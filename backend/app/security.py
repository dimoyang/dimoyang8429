"""密码哈希与 JWT 签发。"""

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from app.config import settings


class TokenError(ValueError):
    """令牌类型或内容不符合预期。"""


def _password_bytes(password: str) -> bytes:
    # bcrypt 只处理前 72 字节，统一截断保证哈希/校验一致。
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            _password_bytes(password), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def _create_token(
    user_id: int,
    token_type: str,
    expires_days: int,
    token_version: int = 0,
    sid: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=expires_days),
        "type": token_type,
        "jti": uuid4().hex,
        "ver": token_version,
    }
    # sid 把令牌绑定到某次登录会话；没有 sid 的是本次升级前签发的旧令牌。
    if sid:
        payload["sid"] = sid
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    user_id: int, token_version: int = 0, sid: str | None = None
) -> str:
    return _create_token(
        user_id,
        "access",
        settings.ACCESS_TOKEN_EXPIRE_DAYS,
        token_version,
        sid,
    )


def create_refresh_token(
    user_id: int, token_version: int = 0, sid: str | None = None
) -> str:
    return _create_token(
        user_id,
        "refresh",
        settings.REFRESH_TOKEN_EXPIRE_DAYS,
        token_version,
        sid,
    )


def create_token_pair(
    user_id: int, token_version: int = 0, sid: str | None = None
) -> tuple[str, str]:
    return (
        create_access_token(user_id, token_version, sid),
        create_refresh_token(user_id, token_version, sid),
    )


def decode_token(token: str, expected_type: str = "access") -> dict:
    """解码并校验令牌类型；旧令牌没有 type/ver 字段时分别按 access/0 处理。"""
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    token_type = payload.get("type", "access")
    if token_type != expected_type:
        raise TokenError(f"Expected {expected_type} token")
    return payload


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
