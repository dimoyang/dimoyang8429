"""SQLAlchemy 引擎与会话。

连接池容量默认对齐 uvicorn/anyio 的 40 个同步请求线程（20 + 20），避免
“worker 数大于连接数”造成必然的池排队超时。SQLite 额外开启 WAL 与
busy_timeout，让并发写冲突排队而不是立刻报错；这只改善单机排队行为，
不会把 SQLite 变成高写并发数据库。详见 README「连接池与单机容量」。
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")
# 内存库使用 SingletonThreadPool，不接受 pool_size / max_overflow 参数。
_IS_MEMORY_SQLITE = _IS_SQLITE and (
    ":memory:" in settings.DATABASE_URL
    or settings.DATABASE_URL.rstrip("/") == "sqlite:"
)

connect_args: dict = {}
if _IS_SQLITE:
    # sqlite3 的 timeout 与 PRAGMA busy_timeout 保持同一个值；PRAGMA 在
    # 每个连接建立时再显式设置一次，避免驱动默认值把等待时间截短。
    connect_args = {
        "check_same_thread": False,
        "timeout": settings.DB_SQLITE_BUSY_TIMEOUT_MS / 1000,
    }

_pool_kwargs: dict = {}
if not _IS_MEMORY_SQLITE:
    # 内存 SQLite 不需要连接池参数；其它数据库与文件型 SQLite 统一使用。
    _pool_kwargs = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
    }

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **_pool_kwargs,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

if _IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            if settings.DB_SQLITE_WAL:
                # 幂等：已经是 WAL 时返回当前模式。内存库会保持 memory，无副作用。
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(
                f"PRAGMA busy_timeout={settings.DB_SQLITE_BUSY_TIMEOUT_MS}"
            )
            # WAL 下 NORMAL 已经足够安全（崩溃最多丢失最后一个事务），
            # 比默认 FULL 少一次 fsync。
            cursor.execute("PRAGMA synchronous=NORMAL")
        finally:
            cursor.close()


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
