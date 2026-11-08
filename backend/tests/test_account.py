"""账号闭环测试：找回密码、修改密码、注销账号。"""

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    AuthSession,
    Booking,
    Itinerary,
    PasswordResetToken,
    User,
)

TOKEN_PATTERN = re.compile(r"\btoken=(\S+)")


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email: str, password: str) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def latest_reset_token(outbox) -> str:
    lines = outbox.read_text(encoding="utf-8").strip().splitlines()
    assert lines, "开发环境邮件应写入 outbox 文件"
    match = TOKEN_PATTERN.search(lines[-1])
    assert match, f"outbox 行缺少 token: {lines[-1]}"
    return match.group(1)


def outbox_line_count(outbox) -> int:
    if not outbox.exists():
        return 0
    return len(outbox.read_text(encoding="utf-8").strip().splitlines())


def future_iso(days: int = 90) -> str:
    value = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
    return value.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()


def test_password_reset_flow_and_single_use(client, mail_outbox) -> None:
    email = "reset-user@meditour.com"
    register_and_login(client, email, "OldPass123456")

    requested = client.post(
        "/api/v1/auth/password-reset/request", json={"email": email}
    )
    assert requested.status_code == 200
    assert requested.json()["detail"]

    token = latest_reset_token(mail_outbox)
    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "NewPass123456"},
    )
    assert confirmed.status_code == 200

    assert (
        client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "OldPass123456"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "NewPass123456"},
        ).status_code
        == 200
    )

    reused = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "AnotherPass123"},
    )
    assert reused.status_code == 400
    assert isinstance(reused.json()["detail"], str)


def test_password_reset_response_does_not_reveal_registration(
    client, mail_outbox
) -> None:
    known = "enumeration-known@meditour.com"
    register_and_login(client, known, "KnownPass123456")

    before = outbox_line_count(mail_outbox)
    known_response = client.post(
        "/api/v1/auth/password-reset/request", json={"email": known}
    )
    unknown_response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "enumeration-unknown@meditour.com"},
    )

    assert known_response.status_code == unknown_response.status_code == 200
    assert known_response.json() == unknown_response.json()
    # 只有已注册邮箱才会真正写出发信记录。
    assert outbox_line_count(mail_outbox) == before + 1


def test_password_reset_rejects_expired_token(client, mail_outbox) -> None:
    email = "reset-expired@meditour.com"
    register_and_login(client, email, "ExpirePass12345")

    client.post("/api/v1/auth/password-reset/request", json={"email": email})
    token = latest_reset_token(mail_outbox)

    with SessionLocal() as db:
        record = db.scalar(
            select(PasswordResetToken).order_by(PasswordResetToken.id.desc())
        )
        assert record is not None
        record.expires_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(minutes=1)
        db.commit()

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "TooLatePass123"},
    )
    assert response.status_code == 400
    assert (
        client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "TooLatePass123"},
        ).status_code
        == 401
    )


def test_change_password_requires_current_password_and_revokes_tokens(
    client,
) -> None:
    email = "change-password@meditour.com"
    tokens = register_and_login(client, email, "CurrentPass123")
    headers = bearer(tokens["access_token"])

    wrong = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongPass123",
            "new_password": "ChangedPass123",
        },
        headers=headers,
    )
    assert wrong.status_code == 400
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    changed = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "CurrentPass123",
            "new_password": "ChangedPass123",
        },
        headers=headers,
    )
    assert changed.status_code == 200

    # 旧的 access / refresh 令牌都应在改密后失效。
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        ).status_code
        == 401
    )

    relogin = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "ChangedPass123"},
    )
    assert relogin.status_code == 200
    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(relogin.json()["access_token"])
        ).status_code
        == 200
    )


def test_delete_account_anonymizes_data_and_blocks_login(client) -> None:
    email = "delete-account@meditour.com"
    password = "DeletePass12345"
    tokens = register_and_login(client, email, password)
    headers = bearer(tokens["access_token"])

    booking = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": 1,
            "appointment_date": future_iso(90),
            "contact_name": "Delete Me",
            "contact_phone": "+86 138-1111-2222",
            "contact_email": email,
            "notes": "private health note",
        },
        headers=headers,
    )
    assert booking.status_code == 201
    booking_id = booking.json()["id"]

    itinerary = client.post(
        "/api/v1/itineraries",
        json={
            "title": "Private trip",
            "start_date": "2027-06-01",
            "end_date": "2027-06-02",
            "destination_ids": ["beijing"],
            "days": [
                {"day_number": 1, "destination_ids": ["beijing"], "notes": "x"}
            ],
            "notes": "private",
        },
        headers=headers,
    )
    assert itinerary.status_code == 201

    wrong = client.request(
        "DELETE", "/api/v1/auth/account", json={"password": "WrongPass123"}
    )
    assert wrong.status_code == 401  # 缺少鉴权头

    wrong = client.request(
        "DELETE", "/api/v1/auth/account", json={"password": "WrongPass123"}, headers=headers
    )
    assert wrong.status_code == 400
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    deleted = client.request(
        "DELETE", "/api/v1/auth/account", json={"password": password}, headers=headers
    )
    assert deleted.status_code == 200

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", data={"username": email, "password": password}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        ).status_code
        == 401
    )

    with SessionLocal() as db:
        # 用订单间接定位被匿名化的用户，避免依赖邮箱随机后缀。
        stored_booking = db.get(Booking, booking_id)
        assert stored_booking is not None
        user = db.get(User, stored_booking.user_id)
        assert user is not None
        assert user.deleted_at is not None
        assert user.email.endswith("@deleted.invalid")
        assert user.email.startswith("deleted-")
        assert user.full_name is None
        assert user.phone is None

        assert stored_booking.status == "cancelled"
        assert stored_booking.contact_name == "Deleted user"
        assert stored_booking.contact_phone == ""
        assert stored_booking.contact_email.endswith("@deleted.invalid")
        assert stored_booking.notes == ""

        remaining = db.scalars(
            select(Itinerary).where(Itinerary.user_id == user.id)
        ).all()
        assert remaining == []

        # 注销后会话全部吊销，避免“软删除账号 + 活跃会话”的脏数据。
        active_sessions = db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
            )
        ).all()
        assert active_sessions == []
