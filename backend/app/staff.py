"""员工角色：可控的授予路径与登录时同步。

角色不接受客户端自助提升，只有两种服务端入口：
1. 环境变量 MEDITOUR_STAFF_EMAILS 白名单：登录时命中即授予 staff；
2. scripts/manage_staff.py：显式授予或撤销，便于运维审计。

白名单只负责「引导」已有账号，不会自动创建账号；撤销必须显式执行脚本，
避免误删环境变量后让正在值班的员工立即失去权限。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User

STAFF_ROLE = "staff"
USER_ROLE = "user"


def is_staff_email(email: str) -> bool:
    return email.strip().lower() in settings.STAFF_EMAILS


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def sync_role_on_login(db: Session, user: User) -> bool:
    """登录成功后按白名单授予 staff；返回是否发生变更（调用方负责 commit）。"""
    if is_staff_email(user.email) and user.role != STAFF_ROLE:
        user.role = STAFF_ROLE
        return True
    return False


def grant_staff(db: Session, email: str) -> User:
    user = find_user_by_email(db, email)
    if user is None or user.deleted_at is not None:
        raise LookupError(f"Active user {email} not found")
    user.role = STAFF_ROLE
    return user


def revoke_staff(db: Session, email: str) -> User:
    user = find_user_by_email(db, email)
    if user is None or user.deleted_at is not None:
        raise LookupError(f"Active user {email} not found")
    user.role = USER_ROLE
    return user
