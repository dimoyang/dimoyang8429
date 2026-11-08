"""预约列表字段与请求校验测试。"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone


def future_iso(days: int = 60) -> str:
    value = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
    return value.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()


def booking_payload(**overrides) -> dict:
    payload = {
        "package_id": 1,
        "appointment_date": future_iso(),
        "contact_name": "Booking Test",
        "contact_phone": "+86 138-0000-0000",
        "contact_email": "pytest-booking@meditour.com",
        "notes": "display fields",
        "need_translator": False,
        "need_accommodation": False,
        "need_pickup": False,
    }
    payload.update(overrides)
    return payload


def test_booking_list_returns_display_fields(client, auth_headers) -> None:
    packages = client.get("/api/v1/medical/packages?page=1&page_size=100").json()
    package = packages["items"][0]
    appointment = future_iso(61)

    payload = booking_payload(
        package_id=package["id"],
        appointment_date=appointment,
    )
    created = client.post("/api/v1/bookings/", json=payload, headers=auth_headers)
    assert created.status_code == 201
    body = created.json()

    assert body["package_id"] == package["id"]
    assert body["package_name"] == package["name"]
    assert body["package_name_en"] == package["name_en"]
    assert body["appointment_date"] == datetime.fromisoformat(appointment).isoformat(
        timespec="seconds"
    )
    assert datetime.fromisoformat(body["created_at"].replace("Z", "+00:00")).tzinfo


def test_booking_rejects_past_appointment_date(client, auth_headers) -> None:
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = client.post(
        "/api/v1/bookings/",
        json=booking_payload(appointment_date=past),
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert any(
        "appointment_date" in str(item.get("loc", ""))
        for item in response.json()["detail"]
    )


def test_booking_rejects_overlong_notes(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/bookings/",
        json=booking_payload(notes="x" * 2001),
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_booking_rejects_invalid_contact_details(client, auth_headers) -> None:
    for field, value in (
        ("contact_phone", "not-a-phone"),
        ("contact_phone", "123"),
        ("contact_email", "not-an-email"),
        ("contact_name", "   "),
    ):
        response = client.post(
            "/api/v1/bookings/",
            json=booking_payload(**{field: value}),
            headers=auth_headers,
        )
        assert response.status_code == 422, f"{field}={value!r}"


def test_booking_normalizes_contact_phone(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/bookings/",
        json=booking_payload(
            appointment_date=future_iso(62),
            contact_phone="+86 (138) 0000-0000",
        ),
        headers=auth_headers,
    )
    assert response.status_code == 201


def test_duplicate_pending_booking_is_rejected(client, auth_headers) -> None:
    appointment = future_iso(63)
    first = client.post(
        "/api/v1/bookings/",
        json=booking_payload(appointment_date=appointment),
        headers=auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/bookings/",
        json=booking_payload(appointment_date=appointment),
        headers=auth_headers,
    )
    assert second.status_code == 409
    assert isinstance(second.json()["detail"], str)

    # 同一套餐换一个日期应当允许。
    other_date = client.post(
        "/api/v1/bookings/",
        json=booking_payload(appointment_date=future_iso(64)),
        headers=auth_headers,
    )
    assert other_date.status_code == 201


def test_concurrent_duplicate_booking_is_settled_by_unique_index(
    client, auth_headers
) -> None:
    """并发下单只能有一个 201；其余由部分唯一索引兜底并转为 409。

    串行重复提交走的是应用层预检查，覆盖不到“查重与插入之间被其他请求插入”
    的竞态，所以这里用多线程同时发起请求。
    """
    appointment = future_iso(70)
    attempts = 8
    barrier = threading.Barrier(attempts)

    def attempt() -> int:
        barrier.wait(timeout=10)
        response = client.post(
            "/api/v1/bookings/",
            json=booking_payload(appointment_date=appointment),
            headers=auth_headers,
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=attempts) as pool:
        statuses = list(pool.map(lambda _: attempt(), range(attempts)))

    assert statuses.count(201) == 1, statuses
    assert statuses.count(409) == attempts - 1, statuses
    assert set(statuses) <= {201, 409}

    expected = datetime.fromisoformat(appointment).isoformat(timespec="seconds")
    pending = [
        item
        for item in client.get("/api/v1/bookings/", headers=auth_headers).json()
        if item["appointment_date"] == expected and item["status"] == "pending"
    ]
    assert len(pending) == 1

    # 部分唯一索引只约束 pending：取消后同一时段可以重新预约。
    booking_id = pending[0]["id"]
    assert (
        client.post(
            f"/api/v1/bookings/{booking_id}/cancel", headers=auth_headers
        ).status_code
        == 200
    )
    rebooked = client.post(
        "/api/v1/bookings/",
        json=booking_payload(appointment_date=appointment),
        headers=auth_headers,
    )
    assert rebooked.status_code == 201
    assert rebooked.json()["status"] == "pending"


def test_cancel_pending_booking_and_reject_second_cancel(
    client, auth_headers
) -> None:
    created = client.post(
        "/api/v1/bookings/",
        json=booking_payload(appointment_date=future_iso(65)),
        headers=auth_headers,
    )
    booking_id = created.json()["id"]

    cancelled = client.post(
        f"/api/v1/bookings/{booking_id}/cancel", headers=auth_headers
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    # 响应字段保持向后兼容。
    for field in ("id", "order_no", "package_id", "total_price", "currency"):
        assert field in cancelled.json()

    again = client.post(
        f"/api/v1/bookings/{booking_id}/cancel", headers=auth_headers
    )
    assert again.status_code == 409
    assert isinstance(again.json()["detail"], str)


def test_cannot_cancel_another_users_booking(client, auth_headers) -> None:
    created = client.post(
        "/api/v1/bookings/",
        json=booking_payload(appointment_date=future_iso(66)),
        headers=auth_headers,
    )
    booking_id = created.json()["id"]

    email = "cancel-other@meditour.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Other123456"},
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Other123456"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.post(
        f"/api/v1/bookings/{booking_id}/cancel", headers=other_headers
    )
    assert response.status_code == 404

    assert (
        client.post(f"/api/v1/bookings/{booking_id}/cancel").status_code == 401
    )
