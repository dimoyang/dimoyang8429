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
    if user is None:
        raise _unauthorized("Invalid or expired token")
    return user
