"""content translations for medical packages and hospitals

Revision ID: c4f8a1d2e6b3
Revises: 9b3c5d7e1f20
Create Date: 2026-11-08 10:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c4f8a1d2e6b3"
down_revision: str | None = "9b3c5d7e1f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "content_translations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=False),
        sa.Column("field", sa.String(length=60), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "lang",
            "field",
            name="uq_content_translation_entity_lang_field",
        ),
    )
    op.create_index(
        "ix_content_translations_lookup",
        "content_translations",
        ["entity_type", "entity_id", "lang"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_content_translations_lookup",
        table_name="content_translations",
    )
    op.drop_table("content_translations")
