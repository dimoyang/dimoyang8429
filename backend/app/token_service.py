"""令牌吊销名单：持久化在数据库，重启和多进程下仍然有效。"""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import TokenRevocation, utcnow


def _expires_at(payload: dict) -> datetime:
    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)
    # 正常令牌都有 exp；缺失时按已过期处理，避免永久占用名单。
    return utcnow()


def is_revoked(db: Session, jti: str | None) -> bool:
    if not jti:
        return False
    return (
        db.scalar(select(TokenRevocation.id).where(TokenRevocation.jti == jti))
        is not None
    )


def revoke(db: Session, payload: dict) -> bool:
    """把令牌加入吊销名单；没有 jti 的旧令牌无法吊销，返回 False。"""
    jti = payload.get("jti")
    if not jti:
        return False
    db.add(
        TokenRevocation(
            jti=jti,
            token_type=str(payload.get("type", "access")),
            expires_at=_expires_at(payload),
        )
    )
    return True


def purge_expired(db: Session) -> None:
    db.execute(delete(TokenRevocation).where(TokenRevocation.expires_at < utcnow()))
