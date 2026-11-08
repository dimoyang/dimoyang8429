"""query plan driven indexes

Revision ID: c2d4e6f8a1b3
Revises: a7c2e9f4b6d1
Create Date: 2026-11-08 22:10:00.000000

依据 `scripts/check_query_plans.py` 的实测结果补齐索引：

- bookings (user_id, id)：用户订单列表按 id 倒序，走索引反向扫描，
  消除 `USE TEMP B-TREE FOR ORDER BY`。
- bookings (status, completed_at, currency, total_price)：员工统计按完成时间
  取成交金额，覆盖索引避免按日汇总时逐行回表；原 (status, completed_at)
  被它替代（前缀相同）。
- medical_packages (is_active, id)：公开/员工在售列表过滤 + 按 id 排序，
  原先为全表扫描 + 临时排序。
- audit_logs (actor_user_id, created_at)：按操作者过滤并倒序，
  替代单列 actor_user_id 索引。

`package.category_active` 目前没有服务端查询（前端本地按分类筛选），
因此不为分类单独建索引，避免无查询使用的写放大。
"""

from collections.abc import Sequence

from alembic import op


revision: str = "c2d4e6f8a1b3"
down_revision: str | None = "a7c2e9f4b6d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_bookings_user_id_id",
        "bookings",
        ["user_id", "id"],
        unique=False,
    )
    op.create_index(
        "ix_bookings_status_completed_stats",
        "bookings",
        ["status", "completed_at", "currency", "total_price"],
        unique=False,
    )
    op.create_index(
        "ix_medical_packages_active_id",
        "medical_packages",
        ["is_active", "id"],
        unique=False,
    )
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.create_index(
        "ix_audit_logs_actor_created_at",
        "audit_logs",
        ["actor_user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_actor_created_at", table_name="audit_logs")
    op.create_index(
        "ix_audit_logs_actor_user_id",
        "audit_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.drop_index(
        "ix_medical_packages_active_id", table_name="medical_packages"
    )
    op.drop_index(
        "ix_bookings_status_completed_stats", table_name="bookings"
    )
    op.drop_index("ix_bookings_user_id_id", table_name="bookings")
