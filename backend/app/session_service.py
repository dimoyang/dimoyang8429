"""会话（设备）登记与吊销。

选型说明：没有复用 `token_revocations` 作为会话列表来源。那张表只记录
“已吊销的 jti”，既没有创建时间/最后使用时间，也无法表达“会话有效但某个
access token 已单独登出”。因此新增 `auth_sessions` 正向登记每次登录，
`token_revocations` 继续只做令牌级黑名单，两者职责不重叠。

列表接口不返回令牌本身：`sid` 是随机标识，不是可用于认证的凭据；
refresh token 的 jti 只留在服务端。
"""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuthSession, TokenRevocation, utcnow
from app.security import create_token_pair, decode_token
from app.token_service import is_revoked


def coarse_user_agent(value: str | None) -> str:
    """只保留截断后的 UA，避免把超长请求头写进数据库。"""
    return (value or "").strip()[:200]


def coarse_ip(value: str | None) -> str:
    """把 IP 打码到网段级别；列表只需要“粗略来源”，不需要精确地址。"""
    ip = (value or "").strip()
    if not ip:
        return ""
    if ":" in ip:
        groups = [part for part in ip.split(":") if part]
        return ":".join(groups[:2]) + "::" if groups else ""
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".x"
    return ip


def create_session(
    db: Session,
    user_id: int,
    token_version: int,
    user_agent: str | None,
    ip: str | None,
) -> tuple[str, str, AuthSession]:
    """登记一次新登录并签发绑定 sid 的令牌；调用方负责 commit。"""
    now = utcnow()
    sid = uuid4().hex
    access_token, refresh_token = create_token_pair(
        user_id, token_version, sid=sid
    )
    refresh_payload = decode_token(refresh_token, expected_type="refresh")
    session = AuthSession(
        user_id=user_id,
        sid=sid,
        refresh_jti=str(refresh_payload.get("jti", "")),
        user_agent=coarse_user_agent(user_agent),
        ip=coarse_ip(ip),
        created_at=now,
        last_used_at=now,
        expires_at=now
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    return access_token, refresh_token, session


def rotate_session(
    db: Session, session: AuthSession, token_version: int
) -> tuple[str, str]:
    """refresh 轮换：沿用同一会话行，更新 jti 与最后使用时间。"""
    now = utcnow()
    access_token, refresh_token = create_token_pair(
        session.user_id, token_version, sid=session.sid
    )
    refresh_payload = decode_token(refresh_token, expected_type="refresh")
    session.refresh_jti = str(refresh_payload.get("jti", ""))
    session.last_used_at = now
    session.expires_at = now + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    return access_token, refresh_token


def get_by_sid(db: Session, sid: str) -> AuthSession | None:
    return db.scalar(select(AuthSession).where(AuthSession.sid == sid))


def is_active_for_user(db: Session, sid: str, user_id: int) -> bool:
    """每次鉴权时确认 sid 对应的会话没有被单独吊销。"""
    return (
        db.scalar(
            select(AuthSession.id).where(
                AuthSession.sid == sid,
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        is not None
    )


def list_active(db: Session, user_id: int) -> list[AuthSession]:
    now = utcnow()
    return list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.last_used_at.desc(), AuthSession.id.desc())
        )
    )


def revoke_session(db: Session, session: AuthSession) -> bool:
    """吊销单个会话：标记会话并拉黑当前 refresh jti（不新增重复黑名单行）。"""
    if session.revoked_at is not None:
        return False
    session.revoked_at = utcnow()
    # 同一事务里可能已经为这个 jti 排过黑名单（例如登出时请求体也带了
    # refresh token）；Session 关闭了 autoflush，必须同时看 db.new。
    already_queued = any(
        isinstance(obj, TokenRevocation) and obj.jti == session.refresh_jti
        for obj in db.new
    )
    if not already_queued and not is_revoked(db, session.refresh_jti):
        db.add(
            TokenRevocation(
                jti=session.refresh_jti,
                token_type="refresh",
                expires_at=session.expires_at,
            )
        )
    return True


def revoke_all(db: Session, user_id: int) -> int:
    """吊销该用户全部会话；调用方同时自增 token_version 让旧 access 立即失效。"""
    sessions = db.scalars(
        select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
    ).all()
    count = 0
    for session in sessions:
        if revoke_session(db, session):
            count += 1
    return count
