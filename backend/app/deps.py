"""公共依赖：数据库会话与 Bearer 鉴权。"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import TokenError, decode_token
from app.token_service import is_revoked

# auto_error=False：缺失/格式错误的凭据也由我们统一返回 401（而非 403）。
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except (jwt.PyJWTError, TokenError, ValueError):
        raise _unauthorized("Invalid or expired token")

    if is_revoked(db, payload.get("jti")):
        raise _unauthorized("Invalid or expired token")
    return payload


def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise _unauthorized("Invalid or expired token")

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise _unauthorized("Invalid or expired token")

    # 改密/重置/注销会把 token_version 自增，旧令牌即使未过期也立即失效。
    if int(payload.get("ver", 0) or 0) != user.token_version:
        raise _unauthorized("Invalid or expired token")
    return user


def require_staff(
    current_user: User = Depends(get_current_user),
) -> User:
    """员工专用端点：已登录但不是 staff 一律 403。"""
    if current_user.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff privileges required",
        )
    return current_user
