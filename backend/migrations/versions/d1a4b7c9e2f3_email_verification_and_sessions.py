"""email verification tokens and auth sessions

Revision ID: d1a4b7c9e2f3
Revises: b3c9d1e5f7a2
Create Date: 2026-11-08 20:10:00.000000

本迁移只新增结构和可空列，不改动已有行：
- users.email_verified_at：为空表示未验证；不阻断登录，只作为状态返回。
- email_verification_tokens：只存 SHA-256 摘要的一次性令牌。
- auth_sessions：每次登录一条设备会话，用于会话列表与单设备吊销；
  与 token_revocations（已吊销 jti 黑名单）职责不同，不合并。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d1a4b7c9e2f3"
down_revision: str | None = "b3c9d1e5f7a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("email_verified_at", sa.DateTime(), nullable=True)
        )

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_email_verification_tokens_token_hash",
        "email_verification_tokens",
        ["token_hash"],
        unique=True,
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sid", sa.String(length=64), nullable=False),
        sa.Column("refresh_jti", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=200), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_sessions_sid", "auth_sessions", ["sid"], unique=True
    )
    op.create_index(
        "ix_auth_sessions_user_active",
        "auth_sessions",
        ["user_id", "revoked_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_sessions_user_active", table_name="auth_sessions"
    )
    op.drop_index("ix_auth_sessions_sid", table_name="auth_sessions")
    op.drop_table("auth_sessions")

    op.drop_index(
        "ix_email_verification_tokens_token_hash",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "ix_email_verification_tokens_user_id",
        table_name="email_verification_tokens",
    )
    op.drop_table("email_verification_tokens")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("email_verified_at")
