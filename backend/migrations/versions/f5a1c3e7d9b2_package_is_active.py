"""package is_active flag for content operations

Revision ID: f5a1c3e7d9b2
Revises: e3f5a7c9b1d2
Create Date: 2026-11-08 15:10:00.000000

新增套餐上下架开关。默认 true，保证既有套餐继续公开展示；
已有订单的价格是下单时快照，不受上下架或改价影响。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f5a1c3e7d9b2"
down_revision: str | None = "e3f5a7c9b1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("medical_packages") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="1",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("medical_packages") as batch_op:
        batch_op.drop_column("is_active")
