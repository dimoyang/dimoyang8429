"""员工侧订单操作：角色授予、状态流转、越权与列表字段裁剪。"""

import secrets
from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.database import SessionLocal
from app.staff import grant_staff, revoke_staff


def _future_iso(days: int = 80) -> str:
    value = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
    return value.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()


def _register(client, email: str, password: str = "Staff123456", **extra) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Staff Test",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client, email: str, password: str = "Staff123456"):
    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body


def _make_staff(client):
    email = f"staff-{secrets.token_hex(4)}@meditour.com"
    password = "Staff123456"
    _register(client, email, password)
    with SessionLocal() as db:
        grant_staff(db, email)
        db.commit()
    headers, body = _login(client, email, password)
    assert body["role"] == "staff"
    return email, headers


def _create_booking(client, headers, days: int = 80, **overrides) -> dict:
    package_id = client.get(
        "/api/v1/medical/packages?page=1&page_size=100"
    ).json()["items"][0]["id"]
    payload = {
        "package_id": package_id,
        "appointment_date": _future_iso(days),
        "contact_name": "Order Customer",
        "contact_phone": "+8613800001234",
        "contact_email": "customer@meditour.com",
        "notes": "sensitive health note",
        "need_translator": True,
        "need_accommodation": False,
        "need_pickup": True,
    }
    payload.update(overrides)
    response = client.post("/api/v1/bookings/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_regular_user_cannot_use_staff_endpoints(client, auth_headers) -> None:
    booking = _create_booking(client, auth_headers, days=81)

    list_response = client.get("/api/v1/staff/bookings", headers=auth_headers)
    assert list_response.status_code == 403
    assert isinstance(list_response.json()["detail"], str)

    detail = client.get(
        f"/api/v1/staff/bookings/{booking['id']}", headers=auth_headers
    )
    assert detail.status_code == 403

    patch = client.patch(
        f"/api/v1/staff/bookings/{booking['id']}/status",
        json={"status": "confirmed"},
        headers=auth_headers,
    )
    assert patch.status_code == 403

    # 未登录统一 401，而不是 403。
    assert client.get("/api/v1/staff/bookings").status_code == 401


def test_register_cannot_self_assign_staff_role(client) -> None:
    email = f"self-staff-{secrets.token_hex(4)}@meditour.com"
    created = _register(client, email, role="staff")
    assert created["role"] == "user"

    _, body = _login(client, email)
    assert body["role"] == "user"

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/api/v1/staff/bookings", headers=headers).status_code == 403


def test_staff_flow_masks_list_and_reveals_detail(client, auth_headers) -> None:
    _, staff_headers = _make_staff(client)
    booking = _create_booking(client, auth_headers, days=82)

    listing = client.get(
        "/api/v1/staff/bookings?page=1&page_size=100&status=pending",
        headers=staff_headers,
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["page"] == 1
    assert body["page_size"] == 100
    assert body["total"] >= 1
    assert body["pages"] >= 1

    item = next(item for item in body["items"] if item["id"] == booking["id"])
    assert "notes" not in item
    assert item["contact_phone"] != "+8613800001234"
    assert "*" in item["contact_phone"]
    assert item["contact_email"] != "customer@meditour.com"
    assert item["contact_email"].endswith("@meditour.com")

    detail = client.get(
        f"/api/v1/staff/bookings/{booking['id']}", headers=staff_headers
    )
    assert detail.status_code == 200
    assert detail.json()["contact_phone"] == "+8613800001234"
    assert detail.json()["contact_email"] == "customer@meditour.com"
    assert detail.json()["notes"] == "sensitive health note"

    confirmed = client.patch(
        f"/api/v1/staff/bookings/{booking['id']}/status",
        json={"status": "confirmed"},
        headers=staff_headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    completed = client.patch(
        f"/api/v1/staff/bookings/{booking['id']}/status",
        json={"status": "completed"},
        headers=staff_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    # 已完成订单不能再次流转。
    again = client.patch(
        f"/api/v1/staff/bookings/{booking['id']}/status",
        json={"status": "confirmed"},
        headers=staff_headers,
    )
    assert again.status_code == 409


def test_staff_rejects_illegal_transitions(client, auth_headers) -> None:
    _, staff_headers = _make_staff(client)
    booking = _create_booking(client, auth_headers, days=83)

    # 跳过 confirmed 直接 completed 属于非法流转。
    skip = client.patch(
        f"/api/v1/staff/bookings/{booking['id']}/status",
        json={"status": "completed"},
        headers=staff_headers,
    )
    assert skip.status_code == 409
    assert isinstance(skip.json()["detail"], str)

    # 不存在的订单返回 404。
    missing = client.patch(
        "/api/v1/staff/bookings/99999999/status",
        json={"status": "confirmed"},
        headers=staff_headers,
    )
    assert missing.status_code == 404

    # 目标状态本身不在允许集合内，属于请求格式错误。
    invalid_value = client.patch(
        f"/api/v1/staff/bookings/{booking['id']}/status",
        json={"status": "cancelled"},
        headers=staff_headers,
    )
    assert invalid_value.status_code == 422


def test_cancelled_booking_cannot_be_confirmed(client, auth_headers) -> None:
    _, staff_headers = _make_staff(client)
    booking = _create_booking(client, auth_headers, days=84)

    cancelled = client.post(
        f"/api/v1/bookings/{booking['id']}/cancel", headers=auth_headers
    )
    assert cancelled.status_code == 200

    response = client.patch(
        f"/api/v1/staff/bookings/{booking['id']}/status",
        json={"status": "confirmed"},
        headers=staff_headers,
    )
    assert response.status_code == 409


def test_login_grants_staff_from_allowlist_and_revoke_takes_effect(
    client, monkeypatch
) -> None:
    email = f"allowlist-{secrets.token_hex(4)}@meditour.com"
    _register(client, email)

    monkeypatch.setattr(settings, "STAFF_EMAILS", [email])
    headers, body = _login(client, email)
    assert body["role"] == "staff"

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "staff"

    with SessionLocal() as db:
        revoke_staff(db, email)
        db.commit()

    # 角色每次请求都从数据库读取，撤销后旧令牌立即失去员工权限。
    denied = client.get("/api/v1/staff/bookings", headers=headers)
    assert denied.status_code == 403
