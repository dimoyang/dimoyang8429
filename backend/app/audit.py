"""审计日志写入工具：统一实体 id、操作者与前后快照的保存方式。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(
    db: Session,
    *,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: object,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    """把一条审计记录加入当前事务，由调用方 commit。

    `entity_id` 统一转成字符串：订单/套餐是整数主键，目的地是 slug。
    `before` / `after` 只放需要留痕的字段，避免把完整备注等敏感内容
    整段复制进审计表。
    """
    details = None
    if before is not None or after is not None:
        details = {"before": before or {}, "after": after or {}}

    log = AuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
    )
    db.add(log)
    return log
