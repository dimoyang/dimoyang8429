"""token revocation list

Revision ID: 7c1f2a9b4d10
Revises: 1793f8ff58c8
Create Date: 2026-11-08 09:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "7c1f2a9b4d10"
down_revision: str | None = "1793f8ff58c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "token_revocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_token_revocations_jti",
        "token_revocations",
        ["jti"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_token_revocations_jti", table_name="token_revocations")
    op.drop_table("token_revocations")
