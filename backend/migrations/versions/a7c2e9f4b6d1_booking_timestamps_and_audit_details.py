"""booking status timestamps and audit detail snapshots

Revision ID: a7c2e9f4b6d1
Revises: d1a4b7c9e2f3
Create Date: 2026-11-08 21:30:00.000000

本迁移只做可空新增与类型放宽，可在现有数据上直接升级：
- bookings.confirmed_at / cancelled_at / completed_at：状态时间戳。
  迁移前的历史行保持 NULL（无法回溯真实时刻），巡检脚本会单独列出。
- audit_logs.details：变更前后快照（JSON，可空）。
- audit_logs.entity_id：Integer -> String(64)，以支持目的地 slug。
  已有行的整数值在 SQLite/PostgreSQL 下都会按文本保留。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a7c2e9f4b6d1"
down_revision: str | None = "d1a4b7c9e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("bookings") as batch_op:
        batch_op.add_column(
            sa.Column("confirmed_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("cancelled_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("completed_at", sa.DateTime(), nullable=True)
        )

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("details", sa.JSON(), nullable=True))
        batch_op.alter_column(
            "entity_id",
            existing_type=sa.Integer(),
            type_=sa.String(length=64),
            existing_nullable=False,
        )

    op.create_index(
        "ix_audit_logs_action_created_at",
        "audit_logs",
        ["action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audit_logs_action_created_at", table_name="audit_logs"
    )

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column(
            "entity_id",
            existing_type=sa.String(length=64),
            type_=sa.Integer(),
            existing_nullable=False,
        )
        batch_op.drop_column("details")

    with op.batch_alter_table("bookings") as batch_op:
        batch_op.drop_column("completed_at")
        batch_op.drop_column("cancelled_at")
        batch_op.drop_column("confirmed_at")
