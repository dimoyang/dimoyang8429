"""staff roles for order operations

Revision ID: b7d2e4f6a8c1
Revises: c4f8a1d2e6b3
Create Date: 2026-11-08 11:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b7d2e4f6a8c1"
down_revision: str | None = "c4f8a1d2e6b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=False,
                server_default="user",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")
