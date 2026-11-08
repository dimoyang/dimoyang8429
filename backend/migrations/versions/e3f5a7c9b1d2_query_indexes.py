"""query indexes for bookings, itineraries and translations

Revision ID: e3f5a7c9b1d2
Revises: d9e4f1a2b6c8
Create Date: 2026-11-08 12:20:00.000000

索引取舍：
- bookings: 用 (user_id, status) 取代单列 user_id 索引（前缀即可服务单列查询），
  并为员工列表补 (status, created_at) 与 (created_at)。
- itineraries: 用 (user_id, start_date) 取代单列 user_id 索引，覆盖列表过滤与排序。
- content_translations: 删除与唯一约束 (entity_type, entity_id, lang, field)
  前缀重复的 ix_content_translations_lookup。
"""

from collections.abc import Sequence

from alembic import op


revision: str = "e3f5a7c9b1d2"
down_revision: str | None = "d9e4f1a2b6c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.create_index(
        "ix_bookings_user_status",
        "bookings",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_bookings_status_created_at",
        "bookings",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_bookings_created_at",
        "bookings",
        ["created_at"],
        unique=False,
    )

    op.drop_index("ix_itineraries_user_id", table_name="itineraries")
    op.create_index(
        "ix_itineraries_user_start",
        "itineraries",
        ["user_id", "start_date"],
        unique=False,
    )

    op.drop_index(
        "ix_content_translations_lookup", table_name="content_translations"
    )


def downgrade() -> None:
    op.create_index(
        "ix_content_translations_lookup",
        "content_translations",
        ["entity_type", "entity_id", "lang"],
        unique=False,
    )

    op.drop_index("ix_itineraries_user_start", table_name="itineraries")
    op.create_index(
        "ix_itineraries_user_id",
        "itineraries",
        ["user_id"],
        unique=False,
    )

    op.drop_index("ix_bookings_created_at", table_name="bookings")
    op.drop_index("ix_bookings_status_created_at", table_name="bookings")
    op.drop_index("ix_bookings_user_status", table_name="bookings")
    op.create_index(
        "ix_bookings_user_id",
        "bookings",
        ["user_id"],
        unique=False,
    )
