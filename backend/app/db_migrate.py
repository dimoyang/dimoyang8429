"""启动时执行数据库迁移。

新数据库直接 `upgrade head`；已有表但没有 Alembic 版本表的旧库不会被
自动改写，而是给出明确提示，要求先人工确认并执行 `alembic stamp head`。
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option(
        "sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%")
    )
    return config


def ensure_database_schema() -> None:
    engine = create_engine(settings.DATABASE_URL)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    if tables and "alembic_version" not in tables:
        raise RuntimeError(
            "检测到未纳入 Alembic 管理的旧数据库：已有表但缺少 "
            "alembic_version。请先备份数据库，确认表结构与当前模型一致后执行 "
            "`python -m alembic stamp head` 标记基线，再启动服务。"
        )

    command.upgrade(_alembic_config(), "head")
