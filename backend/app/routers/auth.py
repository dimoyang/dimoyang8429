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
from app.audit import record_audit
from app.config import settings
from app.database import get_db
from app.deps import get_current_user, get_token_payload
from app.mailer import send_email_verification, send_password_reset
from app.models import (
    AuthSession,
    Booking,
    EmailVerificationToken,
    Itinerary,
    ItineraryDay,
    PasswordResetToken,
    User,
    utcnow,
)
from app.schemas import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    EmailVerificationConfirm,
    ItineraryResponse,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.security import (
    TokenError,
    decode_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.session_service import (
    create_session,
    get_by_sid,
    list_active,
    revoke_all,
    revoke_session,
    rotate_session,
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
# 重发验证邮件无论当前是否已验证、发信是否成功，都返回同一响应。
_VERIFICATION_REQUEST_RESPONSE = {
    "detail": "If this address needs verification, a verification email has been sent"
}
_INVALID_VERIFICATION_TOKEN = "Invalid or expired verification token"


def _invalid_token(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _client_ip(request: Request) -> str:
    """限流用的来源 IP。

    只信任直连 IP，不读取 `X-Forwarded-For`：后者可被客户端伪造，
    除非反代已明确覆盖该头。若部署在反代后且需要按真实客户端限流，
    应在反代上覆盖 `X-Forwarded-For` 后再改成信任它。
    """
    return request.client.host if request.client else "unknown"


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="登录并签发 access/refresh 令牌",
    description=(
        "公开接口，使用 form-urlencoded 的 `username`（邮箱）与 `password`。"
        "成功后返回 access token、refresh token 与角色 `role`。"
        "同一 IP + 邮箱连续失败会触发限流。"
    ),
    responses={
        401: {"description": "邮箱或密码错误（含已注销账号）"},
        422: {"description": "表单字段缺失或格式错误"},
        429: {"description": "失败次数过多；按 Retry-After 秒数后重试"},
    },
)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = form_data.username.strip().lower()
    client_ip = _client_ip(request)

    # 检查与计数在同一个锁内完成：并发请求不会都先通过检查再一起记录失败。
    wait = rate_limit.begin_attempt(client_ip, email)
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
        # 失败名额已在 begin_attempt 中预占，这里不再重复计数。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rate_limit.clear(client_ip, email)
    # 命中员工白名单则在登录时授予 staff；角色变更立即对新令牌生效。
    sync_role_on_login(db, user)
    # 每次登录登记一个会话（设备），令牌通过 sid 与之绑定。
    access_token, refresh_token, _session = create_session(
        db,
        user.id,
        user.token_version,
        request.headers.get("user-agent"),
        client_ip,
    )
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        email_verified=user.email_verified,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="用 refresh token 换取新令牌",
    description=(
        "公开接口。refresh token 一次性使用：成功后旧 refresh token 立即吊销，"
        "重复使用、过期或已吊销均返回 401。"
    ),
    responses={
        401: {"description": "refresh token 无效、过期、已使用或账号已失效"},
        422: {"description": "缺少 refresh_token 字段"},
    },
)
def refresh_tokens(
    request: Request,
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

    sid = payload.get("sid")
    session = get_by_sid(db, str(sid)) if sid else None
    if sid and (session is None or session.revoked_at is not None):
        # 会话被“退出该设备/所有设备”或管理员吊销后，refresh 立即失效。
        raise _invalid_token("Session has been revoked")

    if session is not None:
        access_token, refresh_token = rotate_session(
            db, session, user.token_version
        )
    else:
        # 升级前签发、没有 sid 的 refresh token：轮换时补登记会话。
        access_token, refresh_token, _session = create_session(
            db,
            user.id,
            user.token_version,
            request.headers.get("user-agent"),
            request.client.host if request.client else None,
        )

    revoke(db, payload)
    purge_expired(db)
    try:
        db.commit()
    except IntegrityError:
        # 并发刷新时另一个请求已先吊销同一个 jti。
        db.rollback()
        raise _invalid_token("Refresh token has already been used")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        email_verified=user.email_verified,
    )


@router.post(
    "/logout",
    summary="登出并吊销令牌",
    description=(
        "需要 Bearer access token。当前 access token 会被吊销；可选在请求体传入"
        " `refresh_token` 一并吊销，但该 refresh token 必须属于当前用户。"
    ),
    responses={
        401: {"description": "access token 无效，或 refresh token 无效/不属于当前用户"},
        422: {"description": "请求体格式错误"},
    },
)
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

    # 把当前设备会话一并标记吊销：access token 上的 sid 校验会让它立即失效，
    # 而不是等 access token 自然过期。
    sid = payload.get("sid")
    if sid:
        session = get_by_sid(db, str(sid))
        if session is not None:
            revoke_session(db, session)

    revoke(db, payload)
    purge_expired(db)
    try:
        db.commit()
    except IntegrityError:
        # 并发登出时令牌已被另一个请求吊销，结果一致。
        db.rollback()
    return {"detail": "Logged out"}


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册普通用户",
    description=(
        "公开接口。注册成功固定为 `role=user`；请求体中的 `role` 会被忽略，"
        "员工角色只能由服务端白名单或管理脚本授予。"
        "注册后会按 `preferred_language` 发送一封一次性邮箱验证邮件；"
        "未验证不会阻断登录（`email_verified=false`）。"
    ),
    responses={
        409: {"description": "邮箱已注册"},
        422: {"description": "邮箱、密码或语言字段格式不合法"},
        429: {"description": "同一来源 IP 注册过于频繁"},
    },
)
def register(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    # 注册前没有可信的账号标识，只能按来源 IP 限流。阈值取得较宽，
    # 避免同一办公室/NAT 的正常注册被误伤；代价是共享出口 IP 时
    # 额度也共享（见 README「认证接口限流」）。
    wait = rate_limit.hit(
        f"register:ip:{_client_ip(request)}",
        settings.REGISTER_LIMIT_PER_IP,
        settings.REGISTER_LIMIT_WINDOW_SECONDS,
    )
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts",
            headers={"Retry-After": str(wait)},
        )

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

    # 验证邮件发送失败不回滚注册，也不改变响应：用户可以稍后用重发接口再试。
    try:
        raw_token = _issue_verification_token(db, user)
        send_email_verification(
            user.email, raw_token, user.preferred_language
        )
    except Exception:
        db.rollback()
        logger.exception("email_verification_email_failed")
    return user


def _issue_verification_token(db: Session, user: User) -> str:
    """作废旧令牌并签发新的验证令牌；返回明文令牌（只用于发信）。"""
    now = utcnow()
    db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw_token = secrets.token_urlsafe(32)
    db.add(
        EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_token),
            expires_at=now
            + timedelta(
                minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES
            ),
            created_at=now,
        )
    )
    db.commit()
    return raw_token


@router.post(
    "/email-verification/request",
    summary="重新发送邮箱验证邮件",
    description=(
        "需要 Bearer access token。无论当前是否已验证、发信是否成功，都返回"
        "同一个 200 响应，避免通过响应差异判断验证状态。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
    },
)
def request_email_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """重发验证邮件；已通过验证的账号不再发信，但响应保持一致。

    同一用户的两次重发之间有冷却（默认 60 秒），冷却内返回同样的 200
    但不签发新令牌、不发信，避免被当作邮件轰炸入口。
    """
    if current_user.email_verified_at is None and (
        rate_limit.begin_cooldown(
            f"verify:user:{current_user.id}",
            settings.VERIFICATION_RESEND_COOLDOWN_SECONDS,
        )
        is None
    ):
        try:
            raw_token = _issue_verification_token(db, current_user)
            send_email_verification(
                current_user.email,
                raw_token,
                current_user.preferred_language,
            )
        except Exception:
            db.rollback()
            logger.exception("email_verification_email_failed")
    return _VERIFICATION_REQUEST_RESPONSE


@router.post(
    "/email-verification/confirm",
    summary="用一次性令牌验证邮箱",
    description=(
        "公开接口。令牌短时效且只能成功使用一次；"
        "成功后用户 `email_verified` 变为 true，不改变已签发的令牌。"
        "当前未验证不会阻断登录，是否强制验证需产品决策（见 README）。"
    ),
    responses={
        400: {"description": "验证令牌无效、过期或已被使用"},
        422: {"description": "令牌字段缺失或格式不合法"},
    },
)
def confirm_email_verification(
    payload: EmailVerificationConfirm,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """消费一次性验证令牌，写入 `users.email_verified_at`。"""
    now = utcnow()
    record = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash
            == hash_reset_token(payload.token)
        )
    )
    if (
        record is None
        or record.used_at is not None
        or record.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVALID_VERIFICATION_TOKEN,
        )

    # 条件更新保证并发下同一令牌只能成功一次。
    consumed = db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.id == record.id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    if consumed.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVALID_VERIFICATION_TOKEN,
        )

    user = db.get(User, record.user_id)
    if user is None or user.deleted_at is not None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_INVALID_VERIFICATION_TOKEN,
        )
    if user.email_verified_at is None:
        user.email_verified_at = now
    db.commit()
    return {"detail": "Email verified"}


@router.post(
    "/password-reset/request",
    summary="请求密码重置邮件",
    description=(
        "公开接口。无论邮箱是否注册都返回同一个 200 响应，防止账号枚举；"
        "已注册账号会收到短时效、一次性的重置令牌（开发环境写入 outbox 文件）。"
    ),
    responses={
        422: {"description": "邮箱格式不合法"},
        429: {"description": "同一来源 IP 请求过于频繁"},
    },
)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """请求重置令牌。

    无论邮箱是否存在都返回同一响应；令牌只存 SHA-256 摘要，短时效且一次性。
    同一用户再次请求时，之前未使用的令牌立即作废。

    IP 维度超限直接 429（不区分邮箱，不泄露账号是否存在）；邮箱维度超限
    则静默返回同样的 200 且不发信——若返回 429，攻击者就能借“是否被限”
    判断邮箱是否注册。
    """
    ip_wait = rate_limit.hit(
        f"reset:ip:{_client_ip(request)}",
        settings.RESET_LIMIT_PER_IP,
        settings.RESET_LIMIT_WINDOW_SECONDS,
    )
    if ip_wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests",
            headers={"Retry-After": str(ip_wait)},
        )

    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    if user is not None and user.deleted_at is None:
        email_wait = rate_limit.hit(
            f"reset:email:{email}",
            settings.RESET_LIMIT_PER_EMAIL,
            settings.RESET_LIMIT_WINDOW_SECONDS,
        )
        if email_wait is not None:
            return _RESET_REQUEST_RESPONSE

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
            send_password_reset(
                user.email, raw_token, user.preferred_language
            )
        except Exception:
            # 发信失败也不能改变响应，否则会暴露邮箱是否存在。
            logger.exception("password_reset_email_failed")

    return _RESET_REQUEST_RESPONSE


@router.post(
    "/password-reset/confirm",
    summary="用一次性令牌重置密码",
    description=(
        "公开接口。令牌短时效且只能成功使用一次；成功后该用户已签发的所有"
        " access/refresh 令牌立即失效。"
    ),
    responses={
        400: {"description": "重置令牌无效、过期或已被使用"},
        422: {"description": "令牌或新密码格式不合法"},
    },
)
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


@router.post(
    "/change-password",
    summary="修改当前账号密码",
    description=(
        "需要 Bearer access token，且必须提供当前密码。成功后 token_version 自增，"
        "该用户所有旧 access/refresh 令牌立即失效。"
    ),
    responses={
        400: {"description": "当前密码错误"},
        401: {"description": "未登录或令牌无效"},
        422: {"description": "密码长度等字段不合法"},
    },
)
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


@router.delete(
    "/account",
    summary="注销账号（软删除 + 匿名化）",
    description=(
        "需要 Bearer access token 与当前密码。用户行保留以维持订单外键，"
        "待处理订单改为 cancelled，联系人信息与备注清空，行程及每日安排删除。"
    ),
    responses={
        400: {"description": "密码错误"},
        401: {"description": "未登录或令牌无效"},
        422: {"description": "缺少密码字段"},
    },
)
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
    # 注销后会话不再可用；显式吊销，避免巡检把“软删除账号 + 活跃会话”判为脏数据。
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )

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


@router.get(
    "/export",
    summary="导出本人数据（JSON 下载）",
    description=(
        "需要 Bearer access token。只按令牌对应的用户导出账号、订单、行程；"
        "不接受任何用户 id 参数。响应带 attachment 下载头，favorites 目前固定为空。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
    },
)
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
    record_audit(
        db,
        actor=current_user,
        action="user.export",
        entity_type="user",
        entity_id=current_user.id,
        after={
            "bookings": len(bookings),
            "itineraries": len(itineraries),
        },
    )
    db.commit()
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": (
                f'attachment; filename="meditour-export-{current_user.id}.json"'
            )
        },
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前登录用户",
    description="需要 Bearer access token。返回账号资料与角色（user/staff）。",
    responses={
        401: {"description": "未登录、令牌无效或账号已失效"},
    },
)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="查看当前有效会话/设备",
    description=(
        "需要 Bearer access token。基于登录时登记的 refresh 会话，返回会话标识、"
        "创建时间、最后使用时间与粗略来源（截断的 User-Agent、打码 IP）。"
        "不返回任何令牌、令牌摘要或完整 IP。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
    },
)
def list_sessions(
    payload: dict = Depends(get_token_payload),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionResponse]:
    current_sid = payload.get("sid")
    return [
        SessionResponse(
            id=session.sid,
            created_at=session.created_at,
            last_used_at=session.last_used_at,
            user_agent=session.user_agent,
            ip=session.ip,
            current=session.sid == current_sid,
        )
        for session in list_active(db, current_user.id)
    ]


@router.delete(
    "/sessions/{session_id}",
    summary="吊销指定设备会话",
    description=(
        "需要 Bearer access token。只能吊销自己的会话；不存在、属于他人或"
        "已经吊销统一返回 404。吊销后该会话对应的 access/refresh 立即失效。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        404: {"description": "会话不存在、不属于当前用户或已吊销"},
    },
)
def revoke_one_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    session = get_by_sid(db, session_id)
    if (
        session is None
        or session.user_id != current_user.id
        or session.revoked_at is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    revoke_session(db, session)
    try:
        db.commit()
    except IntegrityError:
        # 并发吊销同一会话时另一个请求已经写入黑名单，结果一致。
        db.rollback()
    return {"detail": "Session revoked"}


@router.post(
    "/sessions/revoke-all",
    summary="退出所有设备",
    description=(
        "需要 Bearer access token。吊销该用户全部有效会话并自增 token_version，"
        "使已经签发的 access/refresh 令牌立即失效（包括当前请求使用的令牌）。"
        "响应中的 `revoked` 是本次标记吊销的会话数。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
    },
)
def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    revoked = revoke_all(db, current_user.id)
    # 旧 access token 可能没有 sid（升级前签发），用版本号兜底让它们也失效。
    current_user.token_version += 1
    db.commit()
    return {"detail": "All sessions revoked", "revoked": revoked}
