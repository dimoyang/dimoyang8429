"""备份与恢复：真实 SQLite 演练（备份 → 删库 → 恢复 → 数据一致）。"""

import sqlite3
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
    before = fingerprint(live)
    assert before.tables["users"] == 1
    assert before.bookings_by_status == {"pending": 1}
    assert before.booking_total_price == 15000.0

    backup_path = tmp_path / "backups" / "meditour-test.db"
    result = backup_database(_url(live), backup_path)
    assert backup_path.exists()
    assert result.fingerprint.tables == before.tables
    assert result.fingerprint.business_summary() == before.business_summary()

    # 演练删库：删掉原库后再用备份恢复。
    live.unlink()
    restored = restore_database(backup_path, _url(live))
    assert restored.replaced_existing is False
    assert restored.safety_copy is None
    assert restored.fingerprint.tables == before.tables
    assert restored.fingerprint.business_summary() == before.business_summary()

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
