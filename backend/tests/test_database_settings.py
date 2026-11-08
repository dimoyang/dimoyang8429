"""连接池与 SQLite PRAGMA 的基础验证。"""

from sqlalchemy import text

from app.config import settings
from app.database import engine


def test_pool_matches_configured_capacity() -> None:
    assert engine.pool.size() == settings.DB_POOL_SIZE
    assert engine.pool._max_overflow == settings.DB_MAX_OVERFLOW
    # 池容量必须覆盖默认的 40 个同步请求线程，否则并发下必然排队超时。
    assert engine.pool.size() + engine.pool._max_overflow >= 40


def test_sqlite_wal_and_busy_timeout_are_applied() -> None:
    with engine.connect() as connection:
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar()
        busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar()
        synchronous = connection.execute(text("PRAGMA synchronous")).scalar()
    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) == settings.DB_SQLITE_BUSY_TIMEOUT_MS
    # NORMAL == 1
    assert int(synchronous) == 1
