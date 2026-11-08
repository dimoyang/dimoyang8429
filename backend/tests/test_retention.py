"""数据保留与清理测试：dry-run 不写入、真实执行只删过期数据。"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app import retention
from app.database import SessionLocal
from app.models import (
    AuditLog,
    AuthSession,
    Booking,
    EmailVerificationToken,
    Itinerary,
    ItineraryDay,
    PasswordResetToken,
    TokenRevocation,
    User,
)


def _naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def test_expired_tokens_dry_run_then_delete(client) -> None:
    # 依赖 client 触发应用 lifespan（测试库建表与种子数据）。
    now = datetime.now(timezone.utc)
    old = _naive(now - timedelta(days=45))
    recent = _naive(now - timedelta(days=1))
    future = _naive(now + timedelta(days=10))

    with SessionLocal() as db:
        user = User(email="retention-tokens@meditour.com", password_hash="x")
        db.add(user)
        db.flush()
        db.add_all(
            [
                # 过期且超过保留期：应删除。
                PasswordResetToken(
                    user_id=user.id, token_hash="old-reset", expires_at=old
                ),
                # 已使用超过保留期（即使未过期）：应删除。
                PasswordResetToken(
                    user_id=user.id,
                    token_hash="used-reset",
                    expires_at=future,
                    used_at=old,
                ),
                # 仍在保留期内：保留。
                PasswordResetToken(
                    user_id=user.id,
                    token_hash="new-reset",
                    expires_at=future,
                    used_at=recent,
                ),
                EmailVerificationToken(
                    user_id=user.id, token_hash="old-verify", expires_at=old
                ),
                EmailVerificationToken(
                    user_id=user.id, token_hash="new-verify", expires_at=future
                ),
                TokenRevocation(
                    jti="old-jti", token_type="access", expires_at=old
                ),
                TokenRevocation(
                    jti="new-jti", token_type="access", expires_at=future
                ),
                AuthSession(
                    user_id=user.id,
                    sid="old-sid",
                    refresh_jti="old-refresh",
                    expires_at=old,
                ),
                AuthSession(
                    user_id=user.id,
                    sid="new-sid",
                    refresh_jti="new-refresh",
                    expires_at=future,
                ),
            ]
        )
        db.commit()

    with SessionLocal() as db:
        preview = retention.cleanup_expired_tokens(db, now, 30, dry_run=True)
        counts = {item.label: item.count for item in preview}
        assert counts["password_reset_tokens"] >= 2
        assert counts["email_verification_tokens"] >= 1
        assert counts["token_revocations"] >= 1
        assert counts["auth_sessions"] >= 1

    # dry-run 不得删除任何行。
    with SessionLocal() as db:
        assert db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == "old-reset"
            )
        ) is not None
        assert db.scalar(
            select(AuthSession).where(AuthSession.sid == "old-sid")
        ) is not None

    with SessionLocal() as db:
        retention.cleanup_expired_tokens(db, now, 30, dry_run=False)

    with SessionLocal() as db:
        for token_hash in ("old-reset", "used-reset"):
            assert db.scalar(
                select(PasswordResetToken).where(
                    PasswordResetToken.token_hash == token_hash
                )
            ) is None, token_hash
        assert db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == "new-reset"
            )
        ) is not None
        assert db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == "old-verify"
            )
        ) is None
        assert db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == "new-verify"
            )
        ) is not None
        assert db.scalar(
            select(TokenRevocation).where(TokenRevocation.jti == "old-jti")
        ) is None
        assert db.scalar(
            select(TokenRevocation).where(TokenRevocation.jti == "new-jti")
        ) is not None
        assert db.scalar(
            select(AuthSession).where(AuthSession.sid == "old-sid")
        ) is None
        assert db.scalar(
            select(AuthSession).where(AuthSession.sid == "new-sid")
        ) is not None


def test_audit_logs_keep_recent_rows(client) -> None:
    # 依赖 client 触发应用 lifespan（测试库建表）。
    now = datetime.now(timezone.utc)
    old = _naive(now - timedelta(days=400))
    recent = _naive(now - timedelta(days=10))
    actor_email = "retention-audit@meditour.com"

    with SessionLocal() as db:
        user = User(email=actor_email, password_hash="x")
        db.add(user)
        db.flush()
        db.add_all(
            [
                AuditLog(
                    actor_user_id=user.id,
                    actor_email=actor_email,
                    action="view",
                    entity_type="retention_test",
                    entity_id="1",
                    created_at=old,
                ),
                AuditLog(
                    actor_user_id=user.id,
                    actor_email=actor_email,
                    action="view",
                    entity_type="retention_test",
                    entity_id="2",
                    created_at=recent,
                ),
            ]
        )
        db.commit()

    def _rows(db) -> list[int]:
        return list(
            db.scalars(
                select(AuditLog.entity_id).where(
                    AuditLog.actor_email == actor_email
                )
            )
        )

    with SessionLocal() as db:
        preview = retention.cleanup_audit_logs(
            db, now, 365, dry_run=True
        )
        assert preview.count >= 1
        assert sorted(_rows(db)) == ["1", "2"]

    with SessionLocal() as db:
        retention.cleanup_audit_logs(db, now, 365, dry_run=False)

    with SessionLocal() as db:
        assert _rows(db) == ["2"]


def test_soft_deleted_account_keeps_user_row_and_booking(client) -> None:
    """到期软删除账号只清关联数据；用户行与订单必须保留（外键与审计）。"""
    email = "retention-deleted@meditour.com"
    password = "Retention123"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Retention Deleted",
            "preferred_language": "en",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    packages = client.get("/api/v1/medical/packages?page_size=1").json()["items"]
    assert packages, "种子数据应至少有一个在售套餐"
    booking = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": packages[0]["id"],
            "appointment_date": _naive(
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat(),
            "contact_name": "Retention Deleted",
            "contact_phone": "+4912345678",
            "contact_email": email,
        },
        headers=headers,
    )
    assert booking.status_code == 201

    itinerary = client.post(
        "/api/v1/itineraries",
        json={
            "title": "Retention trip",
            "start_date": "2026-12-01",
            "end_date": "2026-12-03",
            "destination_ids": ["beijing"],
            "days": [{"day_number": 1, "destination_ids": ["beijing"], "notes": ""}],
        },
        headers=headers,
    )
    assert itinerary.status_code == 201

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.deleted_at = _naive(now - timedelta(days=60))
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash="soft-deleted-reset",
                expires_at=_naive(now + timedelta(days=10)),
            )
        )
        db.commit()
        user_id = user.id

    with SessionLocal() as db:
        item = retention.cleanup_soft_deleted_accounts(
            db, now, 30, dry_run=False
        )
    assert item.count >= 1
    assert "保留用户行" in item.detail

    with SessionLocal() as db:
        # 用户行与订单保留。
        assert db.get(User, user_id) is not None
        assert db.scalar(
            select(Booking).where(Booking.user_id == user_id)
        ) is not None
        # 可再生的关联数据被清理。
        assert db.scalars(
            select(Itinerary).where(Itinerary.user_id == user_id)
        ).all() == []
        assert db.scalars(
            select(ItineraryDay).join(
                Itinerary, ItineraryDay.itinerary_id == Itinerary.id
            ).where(Itinerary.user_id == user_id)
        ).all() == []
        assert db.scalars(
            select(AuthSession).where(AuthSession.user_id == user_id)
        ).all() == []
        assert db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == "soft-deleted-reset"
            )
        ) is None


def test_mail_files_and_outbox_lines_cleanup(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    preview_dir = tmp_path / "preview"
    preview_dir.mkdir()
    old_file = preview_dir / "old.eml"
    new_file = preview_dir / "new.eml"
    old_file.write_bytes(b"old mail")
    new_file.write_bytes(b"new mail")
    old_ts = (now - timedelta(days=30)).timestamp()
    os.utime(old_file, (old_ts, old_ts))

    outbox = tmp_path / "outbox.log"
    old_line = (
        f"{(now - timedelta(days=30)).isoformat(timespec='seconds')}"
        "\tto=a@example.com\tsubject=s\ttoken=old\tpreview=old.eml\n"
    )
    new_line = (
        f"{(now - timedelta(days=1)).isoformat(timespec='seconds')}"
        "\tto=b@example.com\tsubject=s\ttoken=new\tpreview=new.eml\n"
    )
    outbox.write_text(old_line + new_line + "无法解析但需保留的一行\n", encoding="utf-8")

    preview = retention.cleanup_mail_files(
        now, preview_dir, outbox, 14, dry_run=True
    )
    counts = {item.label: item.count for item in preview}
    assert counts["mail_preview_files"] == 1
    assert counts["mail_outbox_lines"] == 1
    assert old_file.exists() and new_file.exists()
    assert "token=old" in outbox.read_text(encoding="utf-8")

    retention.cleanup_mail_files(now, preview_dir, outbox, 14, dry_run=False)
    assert not old_file.exists()
    assert new_file.exists()
    remaining = outbox.read_text(encoding="utf-8")
    assert "token=old" not in remaining
    assert "token=new" in remaining
    assert "无法解析但需保留的一行" in remaining


def test_upload_cleanup_only_touches_temp_suffixes(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    old_tmp = upload_dir / "chunk.tmp"
    old_image = upload_dir / "photo.jpg"
    new_tmp = upload_dir / "fresh.part"
    for path in (old_tmp, old_image, new_tmp):
        path.write_bytes(b"x")
    old_ts = (now - timedelta(days=5)).timestamp()
    os.utime(old_tmp, (old_ts, old_ts))
    os.utime(old_image, (old_ts, old_ts))

    preview = retention.cleanup_upload_temp_files(now, upload_dir, 1, True)
    assert preview.count == 1
    assert preview.samples == ["chunk.tmp"]
    assert old_tmp.exists()

    retention.cleanup_upload_temp_files(now, upload_dir, 1, False)
    assert not old_tmp.exists()
    # 最终图片与新临时文件都不应被清理。
    assert old_image.exists()
    assert new_tmp.exists()
