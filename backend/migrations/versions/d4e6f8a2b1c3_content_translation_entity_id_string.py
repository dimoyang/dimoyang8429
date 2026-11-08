"""content_translations.entity_id: Integer -> String(64)

Revision ID: d4e6f8a2b1c3
Revises: c2d4e6f8a1b3
Create Date: 2026-11-08 23:20:00.000000

目的地主键是 slug 字符串（如 `beijing`），原来的整数 `entity_id` 无法表达，
导致目的地译文无处可存。改为字符串后：

- 套餐/医院继续存整数主键的文本形式（`"1"`、`"2"`）；
- 目的地直接存 slug；
- 唯一约束 (entity_type, entity_id, lang, field) 保持不变。

SQLite 通过批量重建表完成类型转换，已有整数值会按文本保留。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "d4e6f8a2b1c3"
down_revision: str | None = "c2d4e6f8a1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("content_translations") as batch_op:
        batch_op.alter_column(
            "entity_id",
            existing_type=sa.Integer(),
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    # 回退前先清掉无法转回整数的目的地译文，避免整表迁移失败。
    op.execute(
        "DELETE FROM content_translations "
        "WHERE entity_type = 'destination'"
    )
    with op.batch_alter_table("content_translations") as batch_op:
        batch_op.alter_column(
            "entity_id",
            existing_type=sa.String(length=64),
            type_=sa.Integer(),
            existing_nullable=False,
        )
