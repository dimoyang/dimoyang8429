"""认证路由：登录、注册、刷新、登出、找回/修改密码、注销账号。"""

import logging
import secrets
from datetime import timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app import rate_limit
from app.config import settings
from app.database import get_db
from app.deps import get_current_user, get_token_payload
from app.mailer import send_password_reset
from app.models import (
    Booking,
    Itinerary,
    ItineraryDay,
    PasswordResetToken,
    User,
    utcnow,
)
from app.schemas import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ItineraryResponse,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.security import (
    TokenError,
    create_token_pair,
    decode_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.staff import sync_role_on_login
from app.token_service import is_revoked, purge_expired, revoke

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("app.auth")

# 无论邮箱是否注册都返回同一响应，避免账号枚举。
_RESET_REQUEST_RESPONSE = {
    "detail": "If the email is registered, a password reset link has been sent"
}
_INVALID_RESET_TOKEN = "Invalid or expired reset token"


def _invalid_token(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = form_data.username.strip().lower()
    client_ip = request.client.host if request.client else None

    wait = rate_limit.retry_after(client_ip, email)
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )

    user = db.scalar(select(User).where(User.email == email))
    if (
        user is None
        or user.deleted_at is not None
        or not verify_password(form_data.password, user.password_hash)
    ):
        rate_limit.record_failure(client_ip, email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rate_limit.clear(client_ip, email)
    # 命中员工白名单则在登录时授予 staff；角色变更立即对新令牌生效。
    if sync_role_on_login(db, user):
        db.commit()
    access_token, refresh_token = create_token_pair(user.id, user.token_version)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    payload_in: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """用 refresh token 换新令牌；旧 refresh token 立即失效（禁止重复使用）。"""
    try:
        payload = decode_token(payload_in.refresh_token, expected_type="refresh")
    except (jwt.PyJWTError, TokenError, ValueError):
        raise _invalid_token("Invalid or expired refresh token")

    jti = payload.get("jti")
    if is_revoked(db, jti):
        raise _invalid_token("Refresh token has already been used")

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise _invalid_token("Invalid or expired refresh token")

    user = db.get(User, user_id)
    if (
        user is None
        or user.deleted_at is not None
        or int(payload.get("ver", 0) or 0) != user.token_version
    ):
        raise _invalid_token("Invalid or expired refresh token")

    revoke(db, payload)
    purge_expired(db)
    try:
        db.commit()
    except IntegrityError:
        # 并发刷新时另一个请求已先吊销同一个 jti。
        db.rollback()
        raise _invalid_token("Refresh token has already been used")

    access_token, refresh_token = create_token_pair(user.id, user.token_version)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
    )


@router.post("/logout")
def logout(
    body: LogoutRequest | None = None,
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """吊销当前 access token；可选同时吊销请求体里的 refresh token。"""
    if body is not None and body.refresh_token:
        try:
            refresh_payload = decode_token(
                body.refresh_token, expected_type="refresh"
            )
        except (jwt.PyJWTError, TokenError, ValueError):
            raise _invalid_token("Invalid or expired refresh token")
        if str(refresh_payload.get("sub", "")) != str(payload.get("sub", "")):
            raise _invalid_token("Refresh token does not belong to this user")
        if not is_revoked(db, refresh_payload.get("jti")):
            revoke(db, refresh_payload)

    revoke(db, payload)
    purge_expired(db)
    try:
        db.commit()
    except IntegrityError:
        # 并发登出时令牌已被另一个请求吊销，结果一致。
        db.rollback()
    return {"detail": "Logged out"}


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    email = payload.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/password-reset/request")
def request_password_reset(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """请求重置令牌。

    无论邮箱是否存在都返回同一响应；令牌只存 SHA-256 摘要，短时效且一次性。
    同一用户再次请求时，之前未使用的令牌立即作废。
    """
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is not None and user.deleted_at is None:
        now = utcnow()
        db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        raw_token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_reset_token(raw_token),
                expires_at=now
                + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES),
            )
        )
        db.commit()
        try:
            send_password_reset(user.email, raw_token)
        except Exception:
            # 发信失败也不能改变响应，否则会暴露邮箱是否存在。
            logger.exception("password_reset_email_failed")

    return _RESET_REQUEST_RESPONSE


@router.post("/password-reset/confirm")
def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """用一次性令牌设置新密码；成功后旧令牌版本全部失效。"""
    now = utcnow()
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_reset_token(payload.token)
        )
    )
    if (
        record is None
        or record.used_at is not None
        or record.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_RESET_TOKEN
        )

    user = db.get(User, record.user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_RESET_TOKEN
        )

    # 条件更新保证并发下同一令牌只能成功一次。
    consumed = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == record.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    if consumed.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=_INVALID_RESET_TOKEN
        )

    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    db.commit()
    return {"detail": "Password has been reset"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """校验当前密码后修改密码，并让该用户已签发的所有令牌失效。"""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.token_version += 1
    db.commit()
    return {"detail": "Password changed; please log in again"}


@router.delete("/account")
def delete_account(
    body: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """注销账号：软删除 + 匿名化。

    用户行保留以维持订单外键完整性；订单作为财务凭证保留，只清除联系人信息，
    待处理订单标记为 cancelled；行程与每日安排属于纯个人数据，直接删除。
    """
    if not verify_password(body.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect",
        )

    user = current_user
    now = utcnow()

    anonymized_email = f"deleted-{user.id}-{secrets.token_hex(4)}@deleted.invalid"
    db.execute(
        update(Booking)
        .where(Booking.user_id == user.id)
        .values(
            contact_name="Deleted user",
            contact_phone="",
            contact_email=anonymized_email,
            notes="",
        )
    )
    db.execute(
        update(Booking)
        .where(Booking.user_id == user.id, Booking.status == "pending")
        .values(status="cancelled")
    )

    itinerary_ids = list(
        db.scalars(select(Itinerary.id).where(Itinerary.user_id == user.id))
    )
    if itinerary_ids:
        db.execute(
            delete(ItineraryDay).where(
                ItineraryDay.itinerary_id.in_(itinerary_ids)
            )
        )
        db.execute(delete(Itinerary).where(Itinerary.id.in_(itinerary_ids)))

    user.email = anonymized_email
    user.full_name = None
    user.phone = None
    user.password_hash = hash_password(secrets.token_urlsafe(32))
    user.token_version += 1
    user.deleted_at = now

    db.commit()
    return {"detail": "Account deleted and personal data anonymized"}


def _utc_z(value) -> str:
    """数据库存 naive UTC；导出时补 Z 后缀，避免客户端按本地时间解析。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _booking_export(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "order_no": booking.order_no,
        "package_id": booking.package_id,
        "package_name": booking.package_name,
        "package_name_en": booking.package_name_en,
        "appointment_date": booking.appointment_date.isoformat(timespec="seconds"),
        "total_price": booking.total_price,
        "currency": booking.currency,
        "status": booking.status,
        "created_at": _utc_z(booking.created_at),
        "contact_name": booking.contact_name,
        "contact_phone": booking.contact_phone,
        "contact_email": booking.contact_email,
        "notes": booking.notes,
        "need_translator": booking.need_translator,
        "need_accommodation": booking.need_accommodation,
        "need_pickup": booking.need_pickup,
    }


@router.get("/export")
def export_my_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """导出当前用户本人的账号、订单与行程数据（JSON 下载）。

    只按 token 对应的 user_id 查询，不接受任何用户 id 参数，避免越权导出。
    后端目前没有收藏表，因此 favorites 固定为空数组。
    """
    bookings = db.scalars(
        select(Booking)
        .options(joinedload(Booking.package))
        .where(Booking.user_id == current_user.id)
        .order_by(Booking.id)
    ).all()
    itineraries = db.scalars(
        select(Itinerary)
        .options(selectinload(Itinerary.days))
        .where(Itinerary.user_id == current_user.id)
        .order_by(Itinerary.id)
    ).all()

    payload = {
        "exported_at": _utc_z(utcnow()),
        "format_version": 1,
        "account": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "preferred_language": current_user.preferred_language,
            "created_at": _utc_z(current_user.created_at),
        },
        "bookings": [_booking_export(booking) for booking in bookings],
        "itineraries": [
            ItineraryResponse.model_validate(itinerary).model_dump(mode="json")
            for itinerary in itineraries
        ],
        # 后端没有收藏表；收藏目前只存在客户端本地。
        "favorites": [],
    }
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": (
                f'attachment; filename="meditour-export-{current_user.id}.json"'
            )
        },
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
