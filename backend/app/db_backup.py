"""SQLite 备份、恢复与一致性校验。

当前部署只有 SQLite；生产环境若换成 PostgreSQL，应使用 pg_dump /
pg_restore，而不是复制 .db 文件。非 SQLite 连接串会被显式拒绝，
避免出现「以为备份成功」的假象。

两个安全约束：

- 备份使用 sqlite3 在线备份 API，而不是直接复制文件，避免写入过程中
  拿到半截数据；备份先写临时文件再原子替换。
- 恢复默认拒绝覆盖非空数据库（必须显式 ``force=True`` / ``--force``），
  并在覆盖前自动保留一份 ``*.pre-restore-*.bak`` 副本。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# 只接受本地文件型 SQLite 连接串；内存库没有可备份的文件。
SQLITE_URL_PREFIXES = (
    "sqlite+pysqlite:///",
    "sqlite:///",
)


class BackupError(RuntimeError):
    """备份/恢复无法继续；调用方应失败退出，而不是继续写数据。"""


def sqlite_path_from_url(database_url: str) -> Path:
    """把 sqlite:/// 连接串解析成本地文件路径。"""
    for prefix in SQLITE_URL_PREFIXES:
        if database_url.startswith(prefix):
            raw = database_url[len(prefix) :]
            break
    else:
        raise BackupError(
            "Only SQLite databases are supported by this tool; "
            "use pg_dump/pg_restore for PostgreSQL."
        )

    if not raw or raw == ":memory:" or raw.startswith("file::memory:"):
        raise BackupError(
            "In-memory SQLite databases cannot be backed up to a file."
        )
    return Path(raw).expanduser().resolve()


def _connect(path: Path, *, readonly: bool) -> sqlite3.Connection:
    if readonly:
        # mode=ro 防止在路径写错时顺手创建空库。
        return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    return sqlite3.connect(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _user_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


@dataclass(frozen=True)
class DatabaseFingerprint:
    """用于「恢复前后是否一致」的判断依据。

    行数足以发现表丢失或整体覆盖失败；订单状态分布与金额合计用于确认
    关键业务数据不是「行数对但内容错」。
    """

    path: str
    size_bytes: int
    sha256: str
    tables: dict[str, int]
    bookings_by_status: dict[str, int]
    booking_total_price: float

    def business_summary(self) -> dict[str, object]:
        return {
            "bookings_by_status": self.bookings_by_status,
            "booking_total_price": self.booking_total_price,
        }


def fingerprint(path: Path) -> DatabaseFingerprint:
    """统计每张表的行数与订单关键指标，不修改数据库。"""
    path = path.expanduser().resolve()
    if not path.exists():
        raise BackupError(f"Database file not found: {path}")

    try:
        with closing(_connect(path, readonly=True)) as connection:
            names = _user_tables(connection)
            tables = {
                name: connection.execute(
                    f'SELECT COUNT(*) FROM "{name}"'
                ).fetchone()[0]
                for name in names
            }

            by_status: dict[str, int] = {}
            total_price = 0.0
            if "bookings" in tables:
                for status, count, amount in connection.execute(
                    "SELECT status, COUNT(*), COALESCE(SUM(total_price), 0) "
                    "FROM bookings GROUP BY status"
                ):
                    by_status[status] = count
                    total_price += float(amount or 0)
    except sqlite3.Error as exc:
        raise BackupError(
            f"Not a readable SQLite database: {path} ({exc})"
        ) from exc

    return DatabaseFingerprint(
        path=str(path),
        size_bytes=path.stat().st_size,
        sha256=_sha256(path),
        tables=tables,
        bookings_by_status=by_status,
        booking_total_price=round(total_price, 2),
    )


@dataclass(frozen=True)
class BackupResult:
    source: str
    target: str
    fingerprint: DatabaseFingerprint


@dataclass(frozen=True)
class RestoreResult:
    backup: str
    target: str
    fingerprint: DatabaseFingerprint
    replaced_existing: bool
    safety_copy: str | None


def backup_database(
    database_url: str,
    target: Path,
    *,
    overwrite: bool = False,
) -> BackupResult:
    """在线备份到 target；先写临时文件，校验后再原子替换。"""
    source = sqlite_path_from_url(database_url)
    if not source.exists():
        raise BackupError(f"Database file not found: {source}")

    target = target.expanduser().resolve()
    if target == source:
        raise BackupError("Backup target must differ from the database file.")
    if target.exists() and not overwrite:
        raise BackupError(f"Backup target already exists: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.unlink(missing_ok=True)

    source_fingerprint = fingerprint(source)
    try:
        with closing(_connect(source, readonly=True)) as src, closing(
            sqlite3.connect(temporary)
        ) as dst:
            src.backup(dst)
        os.replace(temporary, target)
    except sqlite3.Error as exc:
        temporary.unlink(missing_ok=True)
        raise BackupError(f"Backup failed: {exc}") from exc

    backup_fingerprint = fingerprint(target)
    if (
        source_fingerprint.tables != backup_fingerprint.tables
        or source_fingerprint.business_summary()
        != backup_fingerprint.business_summary()
    ):
        raise BackupError(
            "Backup verification failed: backup content differs from source."
        )

    return BackupResult(
        source=str(source),
        target=str(target),
        fingerprint=backup_fingerprint,
    )


def _existing_tables(path: Path) -> list[str]:
    """目标库已有业务表时返回表名；文件不存在或只有空文件时返回空列表。"""
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        with closing(_connect(path, readonly=True)) as connection:
            return _user_tables(connection)
    except sqlite3.Error as exc:
        raise BackupError(
            f"Target exists but is not a readable SQLite database: {path} ({exc})"
        ) from exc


def restore_database(
    backup_path: Path,
    database_url: str,
    *,
    force: bool = False,
) -> RestoreResult:
    """用备份覆盖目标库；目标非空时必须显式 force。"""
    backup = backup_path.expanduser().resolve()
    if not backup.exists() or not backup.is_file():
        raise BackupError(f"Backup file not found: {backup}")

    target = sqlite_path_from_url(database_url)
    if target == backup:
        raise BackupError("Restore source and target must be different files.")

    backup_fingerprint = fingerprint(backup)
    # 防止把任意 SQLite 文件（如空库）当成备份恢复。
    if "users" not in backup_fingerprint.tables:
        raise BackupError(
            "Backup does not look like a MediTour database "
            "(missing users table)."
        )

    existing_tables = _existing_tables(target)
    if existing_tables and not force:
        raise BackupError(
            "Target database is not empty "
            f"({len(existing_tables)} tables: {', '.join(existing_tables)}). "
            "Stop the backend before restoring, then re-run with --force to "
            "overwrite it."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".restore.tmp")
    temporary.unlink(missing_ok=True)

    safety_copy: Path | None = None
    if existing_tables:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safety_copy = target.with_name(
            f"{target.stem}.pre-restore-{stamp}{target.suffix}.bak"
        )
        shutil.copy2(target, safety_copy)

    try:
        with closing(_connect(backup, readonly=True)) as src, closing(
            sqlite3.connect(temporary)
        ) as dst:
            src.backup(dst)
        os.replace(temporary, target)
    except sqlite3.Error as exc:
        temporary.unlink(missing_ok=True)
        raise BackupError(
            f"Restore failed: {exc}. Stop the backend and try again."
        ) from exc
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise BackupError(
            f"Restore failed while replacing {target}: {exc}. "
            "The backend is probably still running."
        ) from exc

    restored = fingerprint(target)
    if (
        restored.tables != backup_fingerprint.tables
        or restored.business_summary() != backup_fingerprint.business_summary()
    ):
        raise BackupError(
            "Restore verification failed: restored row counts differ from "
            f"backup {backup}."
        )

    return RestoreResult(
        backup=str(backup),
        target=str(target),
        fingerprint=restored,
        replaced_existing=bool(existing_tables),
        safety_copy=str(safety_copy) if safety_copy else None,
    )
