"""认证路由：登录、注册、刷新、登出、当前用户。"""

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import rate_limit
from app.database import get_db
from app.deps import get_current_user, get_token_payload
from app.models import User
from app.schemas import (
    LogoutRequest,
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
    verify_password,
)
from app.token_service import is_revoked, purge_expired, revoke

router = APIRouter(prefix="/auth", tags=["auth"])


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
    if user is None or not verify_password(form_data.password, user.password_hash):
        rate_limit.record_failure(client_ip, email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    rate_limit.clear(client_ip, email)
    access_token, refresh_token = create_token_pair(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


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
    if user is None:
        raise _invalid_token("Invalid or expired refresh token")

    revoke(db, payload)
    purge_expired(db)
    try:
        db.commit()
    except IntegrityError:
        # 并发刷新时另一个请求已先吊销同一个 jti。
        db.rollback()
        raise _invalid_token("Refresh token has already been used")

    access_token, refresh_token = create_token_pair(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


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


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
