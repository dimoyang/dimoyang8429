"""订单状态机与审计覆盖：终态锁死、时间戳、取消规则与查询过滤。"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AuditLog
from app.staff import grant_staff


def _future_iso(days: int = 80) -> str:
    value = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
    return value.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()


def _register(client, email: str, password: str = "Lifecycle123", **extra) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Lifecycle Test",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _login(client, email: str, password: str = "Lifecycle123"):
    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body


def _make_staff(client):
    email = f"lifecycle-staff-{secrets.token_hex(4)}@meditour.com"
    password = "Lifecycle123"
    _register(client, email, password)
    with SessionLocal() as db:
        grant_staff(db, email)
        db.commit()
    headers, body = _login(client, email, password)
    assert body["role"] == "staff"
    return email, headers


def _create_booking(client, headers, days: int = 80) -> dict:
    package_id = client.get(
        "/api/v1/medical/packages?page=1&page_size=100"
    ).json()["items"][0]["id"]
    response = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": package_id,
            "appointment_date": _future_iso(days),
            "contact_name": "Lifecycle Customer",
            "contact_phone": "+8613800005678",
            "contact_email": "lifecycle@meditour.com",
            "notes": "state machine",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _set_status(client, headers, booking_id: int, value: str):
    return client.patch(
        f"/api/v1/staff/bookings/{booking_id}/status",
        json={"status": value},
        headers=headers,
    )


def _audit_rows(action: str, entity_id: str | None = None) -> list[AuditLog]:
    with SessionLocal() as db:
        stmt = select(AuditLog).where(AuditLog.action == action)
        if entity_id is not None:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        return list(db.scalars(stmt.order_by(AuditLog.id)).all())


def test_new_booking_has_no_status_timestamps(client, auth_headers) -> None:
    booking = _create_booking(client, auth_headers, days=90)
    assert booking["status"] == "pending"
    assert booking["confirmed_at"] is None
    assert booking["cancelled_at"] is None
    assert booking["completed_at"] is None


def test_confirmed_booking_cannot_be_cancelled_by_user(
    client, auth_headers
) -> None:
    _, staff_headers = _make_staff(client)
    booking = _create_booking(client, auth_headers, days=91)

    confirmed = _set_status(
        client, staff_headers, booking["id"], "confirmed"
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed_at"] is not None

    # 已确认订单进入员工流程，用户不能自助取消，且提示需要联系员工。
    denied = client.post(
        f"/api/v1/bookings/{booking['id']}/cancel", headers=auth_headers
    )
    assert denied.status_code == 409
    assert "contact staff" in denied.json()["detail"]

    detail = client.get(
        f"/api/v1/staff/bookings/{booking['id']}", headers=staff_headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "confirmed"
    assert detail.json()["cancelled_at"] is None


def test_staff_can_cancel_pending_and_confirmed(client, auth_headers) -> None:
    _, staff_headers = _make_staff(client)

    pending = _create_booking(client, auth_headers, days=92)
    cancelled = _set_status(
        client, staff_headers, pending["id"], "cancelled"
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None

    # 已取消是终态，不能再确认或再次取消。
    for target in ("confirmed", "cancelled"):
        again = _set_status(client, staff_headers, pending["id"], target)
        assert again.status_code == 409

    confirmed_booking = _create_booking(client, auth_headers, days=93)
    assert (
        _set_status(
            client, staff_headers, confirmed_booking["id"], "confirmed"
        ).status_code
        == 200
    )
    staff_cancel = _set_status(
        client, staff_headers, confirmed_booking["id"], "cancelled"
    )
    assert staff_cancel.status_code == 200
    assert staff_cancel.json()["cancelled_at"] is not None


def test_completed_is_terminal_and_cannot_return_to_pending(
    client, auth_headers
) -> None:
    _, staff_headers = _make_staff(client)
    booking = _create_booking(client, auth_headers, days=94)

    assert (
        _set_status(
            client, staff_headers, booking["id"], "confirmed"
        ).status_code
        == 200
    )
    completed = _set_status(
        client, staff_headers, booking["id"], "completed"
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None
    # 确认时间保留，不会被完成覆盖。
    assert completed.json()["confirmed_at"] is not None

    # completed 是终态：不能再完成/取消。
    for target in ("completed", "cancelled"):
        again = _set_status(client, staff_headers, booking["id"], target)
        assert again.status_code == 409
        assert "terminal state" in again.json()["detail"]

    # 退回 pending 不是合法目标值，属于请求格式错误。
    back = _set_status(client, staff_headers, booking["id"], "pending")
    assert back.status_code == 422

    # 用户也不能取消已完成订单。
    user_cancel = client.post(
        f"/api/v1/bookings/{booking['id']}/cancel", headers=auth_headers
    )
    assert user_cancel.status_code == 409


def test_user_cancel_and_export_are_audited(client, auth_headers) -> None:
    booking = _create_booking(client, auth_headers, days=95)
    cancelled = client.post(
        f"/api/v1/bookings/{booking['id']}/cancel", headers=auth_headers
    )
    assert cancelled.status_code == 200

    cancel_rows = _audit_rows("booking.cancel", str(booking["id"]))
    assert len(cancel_rows) == 1
    assert cancel_rows[0].details == {
        "before": {"status": "pending"},
        "after": {"status": "cancelled"},
    }

    before_export = len(_audit_rows("user.export"))
    exported = client.get("/api/v1/auth/export", headers=auth_headers)
    assert exported.status_code == 200

    export_rows = _audit_rows("user.export")
    assert len(export_rows) == before_export + 1
    assert export_rows[-1].entity_type == "user"
    assert export_rows[-1].details["after"]["bookings"] >= 1


def test_staff_status_change_is_audited(client, auth_headers) -> None:
    staff_email, staff_headers = _make_staff(client)
    booking = _create_booking(client, auth_headers, days=96)

    assert (
        _set_status(
            client, staff_headers, booking["id"], "confirmed"
        ).status_code
        == 200
    )

    rows = _audit_rows("booking.status_change", str(booking["id"]))
    assert len(rows) == 1
    assert rows[0].actor_email == staff_email
    assert rows[0].details == {
        "before": {"status": "pending"},
        "after": {"status": "confirmed"},
    }


def test_price_update_and_content_deletes_are_audited(
    client, auth_headers
) -> None:
    staff_email, staff_headers = _make_staff(client)

    hospital = client.post(
        "/api/v1/staff/hospitals",
        json={"name": "Audit Hospital", "name_en": "Audit Hospital"},
        headers=staff_headers,
    )
    assert hospital.status_code == 201, hospital.text
    hospital_id = hospital.json()["id"]

    package = client.post(
        "/api/v1/staff/packages",
        json={
            "name": "Audit Package",
            "name_en": "Audit Package",
            "price": 100.0,
            "currency": "EUR",
            "hospital_id": hospital_id,
        },
        headers=staff_headers,
    )
    assert package.status_code == 201, package.text
    package_id = package.json()["id"]

    updated = client.patch(
        f"/api/v1/staff/packages/{package_id}",
        json={"price": 123.0},
        headers=staff_headers,
    )
    assert updated.status_code == 200

    update_rows = _audit_rows("package.update", str(package_id))
    assert len(update_rows) == 1
    assert update_rows[0].actor_email == staff_email
    assert update_rows[0].details == {
        "before": {"price": 100.0},
        "after": {"price": 123.0},
    }

    assert (
        client.delete(
            f"/api/v1/staff/packages/{package_id}", headers=staff_headers
        ).status_code
        == 204
    )
    delete_rows = _audit_rows("package.delete", str(package_id))
    assert len(delete_rows) == 1
    assert delete_rows[0].details["before"]["price"] == 123.0

    assert (
        client.delete(
            f"/api/v1/staff/hospitals/{hospital_id}", headers=staff_headers
        ).status_code
        == 204
    )
    assert len(_audit_rows("hospital.delete", str(hospital_id))) == 1

    slug = f"audit-dest-{secrets.token_hex(3)}"
    destination = client.post(
        "/api/v1/staff/destinations",
        json={
            "id": slug,
            "name": "审计目的地",
            "name_en": "Audit Destination",
        },
        headers=staff_headers,
    )
    assert destination.status_code == 201, destination.text
    assert (
        client.delete(
            f"/api/v1/staff/destinations/{slug}", headers=staff_headers
        ).status_code
        == 204
    )
    destination_rows = _audit_rows("destination.delete", slug)
    assert len(destination_rows) == 1
    assert destination_rows[0].details["before"]["name"] == "审计目的地"


def test_audit_query_filters_and_requires_staff(client, auth_headers) -> None:
    _, staff_headers = _make_staff(client)
    booking = _create_booking(client, auth_headers, days=97)
    assert (
        _set_status(
            client, staff_headers, booking["id"], "confirmed"
        ).status_code
        == 200
    )

    denied = client.get("/api/v1/staff/audit-logs", headers=auth_headers)
    assert denied.status_code == 403

    by_action = client.get(
        "/api/v1/staff/audit-logs?action=booking.status_change&page=1&page_size=100",
        headers=staff_headers,
    )
    assert by_action.status_code == 200
    body = by_action.json()
    assert body["total"] >= 1
    assert all(
        item["action"] == "booking.status_change" for item in body["items"]
    )
    assert any(
        item["entity_id"] == str(booking["id"]) for item in body["items"]
    )
    assert {"page", "page_size", "pages", "total"} <= body.keys()

    by_entity = client.get(
        "/api/v1/staff/audit-logs"
        f"?entity_type=booking&entity_id={booking['id']}",
        headers=staff_headers,
    )
    assert by_entity.status_code == 200
    assert all(item["entity_type"] == "booking" for item in by_entity.json()["items"])

    now = datetime.now(timezone.utc)
    in_range = client.get(
        "/api/v1/staff/audit-logs",
        params={
            "action": "booking.status_change",
            "created_from": (now - timedelta(hours=1)).isoformat(),
            "created_to": (now + timedelta(hours=1)).isoformat(),
        },
        headers=staff_headers,
    )
    assert in_range.status_code == 200
    assert in_range.json()["total"] >= 1

    future = client.get(
        "/api/v1/staff/audit-logs",
        params={
            "action": "booking.status_change",
            "created_from": (now + timedelta(days=1)).isoformat(),
        },
        headers=staff_headers,
    )
    assert future.status_code == 200
    assert future.json()["total"] == 0

    inverted = client.get(
        "/api/v1/staff/audit-logs",
        params={
            "created_from": (now + timedelta(hours=1)).isoformat(),
            "created_to": (now - timedelta(hours=1)).isoformat(),
        },
        headers=staff_headers,
    )
    assert inverted.status_code == 422
