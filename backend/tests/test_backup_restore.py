"""备份与恢复：真实 SQLite 演练（备份 → 删库 → 恢复 → 数据一致）。"""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.db_backup import (
    BackupError,
    backup_database,
    fingerprint,
    prune_backups,
    restore_database,
    sqlite_path_from_url,
)
from app.models import (
    Booking,
    ContentTranslation,
    Hospital,
    MedicalPackage,
    User,
)


def _url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _build_database(
    path: Path,
    *,
    email: str = "alice@example.com",
    price: float = 15000.0,
) -> None:
    engine = create_engine(_url(path))
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email=email, password_hash="hash", full_name="Alice")
        db.add(user)
        db.flush()
        hospital = Hospital(name="协和", name_en="PUMCH", level="三级甲等")
        db.add(hospital)
        db.flush()
        package = MedicalPackage(
            name="膝关节置换手术",
            name_en="Knee Replacement Surgery",
            price=price,
            currency="EUR",
            hospital_id=hospital.id,
        )
        db.add(package)
        db.flush()
        db.add(
            Booking(
                order_no=f"MT-{email}",
                user_id=user.id,
                package_id=package.id,
                appointment_date=datetime(2027, 1, 1, 9, 0),
                contact_name="Alice",
                contact_phone="+8613800001111",
                contact_email=email,
                notes="sensitive health note",
                total_price=price,
                currency="EUR",
                status="pending",
            )
        )
        db.add(
            ContentTranslation(
                entity_type="package",
                entity_id=package.id,
                lang="de",
                field="name",
                value="Kniegelenkersatz",
            )
        )
        db.commit()
    engine.dispose()


def test_backup_then_restore_roundtrip(tmp_path: Path) -> None:
    live = tmp_path / "live.db"
    _build_database(live)
    # 演示库实际跑在 WAL 模式；备份必须把 WAL 页合并回主文件，
    # 否则单拷 .db 恢复会丢数据。
    with closing(sqlite3.connect(live)) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    before = fingerprint(live)
    assert before.tables["users"] == 1
    assert before.bookings_by_status == {"pending": 1}
    assert before.booking_total_price == 15000.0

    backup_path = tmp_path / "backups" / "meditour-test.db"
    result = backup_database(_url(live), backup_path)
    assert backup_path.exists()
    assert result.fingerprint.tables == before.tables
    assert result.fingerprint.business_summary() == before.business_summary()
    # 备份文件独立可恢复：不带 -wal/-shm，且已从 WAL 切回 DELETE。
    assert not backup_path.with_name(backup_path.name + "-wal").exists()
    assert not backup_path.with_name(backup_path.name + "-shm").exists()
    with closing(sqlite3.connect(backup_path)) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "delete"

    # 演练删库：删掉原库后再用备份恢复。
    live.unlink()
    restored = restore_database(backup_path, _url(live))
    assert restored.replaced_existing is False
    assert restored.safety_copy is None
    assert restored.fingerprint.tables == before.tables
    assert restored.fingerprint.business_summary() == before.business_summary()
    # 恢复会清掉目标库遗留的 WAL 边车文件。
    assert not live.with_name(live.name + "-wal").exists()
    assert not live.with_name(live.name + "-shm").exists()

    with sqlite3.connect(live) as connection:
        order = connection.execute(
            "SELECT order_no, total_price, notes FROM bookings"
        ).fetchone()
        assert order == ("MT-alice@example.com", 15000.0, "sensitive health note")
        assert connection.execute(
            "SELECT value FROM content_translations"
        ).fetchone()[0] == "Kniegelenkersatz"


def test_restore_refuses_non_empty_target_without_force(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    _build_database(source, email="alice@example.com")
    backup_path = tmp_path / "backup.db"
    backup_database(_url(source), backup_path)

    target = tmp_path / "target.db"
    _build_database(target, email="bob@example.com", price=99.0)

    with pytest.raises(BackupError) as excinfo:
        restore_database(backup_path, _url(target))
    assert "--force" in str(excinfo.value)

    # 拒绝执行时目标库必须原样保留。
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT email FROM users").fetchone()[0] == (
            "bob@example.com"
        )


def test_restore_force_keeps_safety_copy(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    _build_database(source, email="alice@example.com")
    backup_path = tmp_path / "backup.db"
    backup_database(_url(source), backup_path)

    target = tmp_path / "target.db"
    _build_database(target, email="bob@example.com", price=99.0)

    restored = restore_database(backup_path, _url(target), force=True)
    assert restored.replaced_existing is True
    assert restored.safety_copy is not None
    safety = Path(restored.safety_copy)
    assert safety.exists()
    with sqlite3.connect(safety) as connection:
        assert connection.execute("SELECT email FROM users").fetchone()[0] == (
            "bob@example.com"
        )

    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT email FROM users").fetchone()[0] == (
            "alice@example.com"
        )
        assert connection.execute(
            "SELECT total_price FROM bookings"
        ).fetchone()[0] == 15000.0


def test_restore_rejects_file_that_is_not_a_database(tmp_path: Path) -> None:
    bogus = tmp_path / "notes.db"
    bogus.write_text("this is not a sqlite database", encoding="utf-8")

    with pytest.raises(BackupError):
        restore_database(bogus, _url(tmp_path / "target.db"))


def test_backup_refuses_existing_target_without_overwrite(tmp_path: Path) -> None:
    live = tmp_path / "live.db"
    _build_database(live)
    backup_path = tmp_path / "existing.db"
    backup_path.write_bytes(b"occupied")

    with pytest.raises(BackupError) as excinfo:
        backup_database(_url(live), backup_path)
    assert "already exists" in str(excinfo.value)


def test_non_sqlite_url_is_rejected() -> None:
    with pytest.raises(BackupError):
        sqlite_path_from_url("postgresql://user:pass@localhost:5432/meditour")


def _touch_backups(directory: Path, names: list[str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / name).write_bytes(b"backup")


def test_prune_keeps_daily_then_weekly_and_never_newest(
    tmp_path: Path,
) -> None:
    names = [
        "meditour-20261108-010000.db",  # 今天较早的一份：同一天只留最新
        "meditour-20261108-020000.db",  # 最新
        "meditour-20261107-020000.db",
        "meditour-20261106-020000.db",
        "meditour-20261030-020000.db",  # 第 44 周
        "meditour-20261023-020000.db",  # 第 43 周
        "meditour-20261016-020000.db",  # 第 42 周
        "meditour-20261009-020000.db",  # 第 41 周
    ]
    _touch_backups(tmp_path, names)
    (tmp_path / "manual-backup.db").write_bytes(b"keep me")
    (tmp_path / "meditour-20261108-020000.db.tmp").write_bytes(b"partial")

    result = prune_backups(
        tmp_path,
        daily_keep=3,
        weekly_keep=2,
        now=datetime(2026, 11, 8, 12, 0),
    )

    kept = {Path(path).name for path in result.kept}
    deleted = {Path(path).name for path in result.deleted}
    assert kept == {
        "meditour-20261108-020000.db",
        "meditour-20261107-020000.db",
        "meditour-20261106-020000.db",
        "meditour-20261030-020000.db",
        "meditour-20261023-020000.db",
    }
    assert deleted == {
        "meditour-20261108-010000.db",
        "meditour-20261016-020000.db",
        "meditour-20261009-020000.db",
    }
    # 非本脚本命名的文件与临时文件不参与清理。
    assert (tmp_path / "manual-backup.db").exists()
    assert (tmp_path / "meditour-20261108-020000.db.tmp").exists()


def test_prune_with_zero_retention_keeps_only_newest(
    tmp_path: Path,
) -> None:
    _touch_backups(
        tmp_path,
        [
            "meditour-20250101-010000.db",
            "meditour-20250102-010000.db",
            "meditour-20250103-010000.db",
        ],
    )

    result = prune_backups(
        tmp_path,
        daily_keep=0,
        weekly_keep=0,
        now=datetime(2026, 11, 8, 12, 0),
    )

    assert {Path(path).name for path in result.kept} == {
        "meditour-20250103-010000.db"
    }
    assert len(result.deleted) == 2


def test_prune_empty_directory_is_noop(tmp_path: Path) -> None:
    result = prune_backups(
        tmp_path, daily_keep=7, weekly_keep=4, now=datetime(2026, 11, 8)
    )
    assert result.kept == ()
    assert result.deleted == ()
