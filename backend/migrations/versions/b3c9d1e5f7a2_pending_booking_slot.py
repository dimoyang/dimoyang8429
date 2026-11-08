"""partial unique index for pending booking slots

Revision ID: b3c9d1e5f7a2
Revises: f5a1c3e7d9b2
Create Date: 2026-11-08 18:40:00.000000

并发下单时，应用层的“先查 pending 再插入”不是原子操作，多个请求可能同时
通过查重并各自插入一条 pending 订单。这里用部分唯一索引把这条规则落到数据库：

    UNIQUE (user_id, package_id, appointment_date) WHERE status = 'pending'

只约束 pending，因此订单取消后仍可重新预约同一时段；已取消/已完成的订单
不参与唯一性判断。

升级前先处理历史数据：如果库里已经存在同一 (user_id, package_id,
appointment_date) 的多条 pending 行（旧竞态留下的脏数据），保留 id 最小的
一条，其余改为 cancelled。不删除任何订单，也不改动金额等财务字段。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b3c9d1e5f7a2"
down_revision: str | None = "f5a1c3e7d9b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DUPLICATE_GROUPS = sa.text(
    """
    SELECT user_id, package_id, appointment_date, MIN(id) AS keep_id
    FROM bookings
    WHERE status = 'pending'
    GROUP BY user_id, package_id, appointment_date
    HAVING COUNT(*) > 1
    """
)

CANCEL_DUPLICATES = sa.text(
    """
    UPDATE bookings
    SET status = 'cancelled'
    WHERE user_id = :user_id
      AND package_id = :package_id
      AND appointment_date = :appointment_date
      AND status = 'pending'
      AND id != :keep_id
    """
)


def _cancel_duplicate_pending(bind: sa.Connection) -> int:
    """保留每组最早的一条 pending，其余改为 cancelled；返回处理行数。"""
    cancelled = 0
    for row in bind.execute(DUPLICATE_GROUPS).fetchall():
        result = bind.execute(
            CANCEL_DUPLICATES,
            {
                "user_id": row.user_id,
                "package_id": row.package_id,
                "appointment_date": row.appointment_date,
                "keep_id": row.keep_id,
            },
        )
        cancelled += result.rowcount or 0
    return cancelled


def upgrade() -> None:
    bind = op.get_bind()
    cancelled = _cancel_duplicate_pending(bind)
    if cancelled:
        print(
            "[migration] cancelled "
            f"{cancelled} duplicate pending booking(s) before creating "
            "uq_bookings_pending_slot"
        )

    op.create_index(
        "uq_bookings_pending_slot",
        "bookings",
        ["user_id", "package_id", "appointment_date"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_bookings_pending_slot", table_name="bookings")
