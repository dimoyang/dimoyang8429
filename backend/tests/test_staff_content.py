"""员工内容运营：套餐上下架、改价快照、CRUD 与删除保护。"""

import secrets
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.staff import grant_staff


def _future_iso(days: int = 90) -> str:
    value = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
    return value.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()


def _register(client, email: str, password: str = "Staff123456") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Content Staff"},
    )
    assert response.status_code == 201, response.text


def _login(client, email: str, password: str = "Staff123456") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _make_staff(client) -> dict[str, str]:
    email = f"content-{secrets.token_hex(4)}@meditour.com"
    _register(client, email)
    with SessionLocal() as db:
        grant_staff(db, email)
        db.commit()
    return _login(client, email)


def _first_hospital_id(client, staff_headers) -> int:
    response = client.get("/api/v1/staff/hospitals", headers=staff_headers)
    assert response.status_code == 200, response.text
    return response.json()["items"][0]["id"]


def _create_package(client, staff_headers, price: float = 1000.0, **overrides) -> dict:
    payload = {
        "name": "测试套餐",
        "name_en": "Test Package",
        "price": price,
        "currency": "EUR",
        "duration_days": 3,
        "category": "checkup",
        "hospital_id": _first_hospital_id(client, staff_headers),
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/staff/packages", json=payload, headers=staff_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_booking(client, user_headers, package_id: int, days: int = 90) -> dict:
    response = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": package_id,
            "appointment_date": _future_iso(days),
            "contact_name": "Content Customer",
            "contact_phone": "+8613800001234",
            "contact_email": "content-customer@meditour.com",
            "notes": "history note",
        },
        headers=user_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_regular_user_cannot_manage_content(client, auth_headers) -> None:
    package = _create_package(client, _make_staff(client))

    assert (
        client.get("/api/v1/staff/packages", headers=auth_headers).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/staff/packages",
            json={"name": "x", "price": 1, "hospital_id": package["hospital_id"]},
            headers=auth_headers,
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/staff/packages/{package['id']}",
            json={"is_active": False},
            headers=auth_headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/staff/packages/{package['id']}", headers=auth_headers
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/staff/hospitals",
            json={"name": "x"},
            headers=auth_headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/staff/destinations",
            json={"id": "x", "name": "x", "name_en": "x"},
            headers=auth_headers,
        ).status_code
        == 403
    )

    # 未登录统一 401。
    assert client.get("/api/v1/staff/packages").status_code == 401
    assert client.get("/api/v1/staff/hospitals").status_code == 401
    assert client.get("/api/v1/staff/destinations").status_code == 401


def test_inactive_package_is_hidden_and_not_bookable(client, auth_headers) -> None:
    staff_headers = _make_staff(client)
    package = _create_package(client, staff_headers)

    public_ids = [
        item["id"]
        for item in client.get(
            "/api/v1/medical/packages?page=1&page_size=100"
        ).json()["items"]
    ]
    assert package["id"] in public_ids

    deactivated = client.patch(
        f"/api/v1/staff/packages/{package['id']}",
        json={"is_active": False},
        headers=staff_headers,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    public_after = client.get(
        "/api/v1/medical/packages?page=1&page_size=100"
    ).json()
    assert package["id"] not in [item["id"] for item in public_after["items"]]

    booking = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": package["id"],
            "appointment_date": _future_iso(91),
            "contact_name": "Hidden Package",
            "contact_phone": "+8613800001234",
            "contact_email": "hidden@meditour.com",
        },
        headers=auth_headers,
    )
    assert booking.status_code == 404
    assert "not available" in booking.json()["detail"]

    # 员工侧默认仍能看到下架套餐，便于重新上架。
    staff_all = client.get(
        "/api/v1/staff/packages?page=1&page_size=100", headers=staff_headers
    ).json()["items"]
    assert package["id"] in [item["id"] for item in staff_all]

    staff_active = client.get(
        "/api/v1/staff/packages?page=1&page_size=100&include_inactive=false",
        headers=staff_headers,
    ).json()["items"]
    assert package["id"] not in [item["id"] for item in staff_active]

    # 重新上架后公开列表恢复。
    reactivated = client.patch(
        f"/api/v1/staff/packages/{package['id']}",
        json={"is_active": True},
        headers=staff_headers,
    )
    assert reactivated.status_code == 200
    public_again = client.get(
        "/api/v1/medical/packages?page=1&page_size=100"
    ).json()["items"]
    assert package["id"] in [item["id"] for item in public_again]


def test_price_change_does_not_affect_existing_booking(client, auth_headers) -> None:
    staff_headers = _make_staff(client)
    package = _create_package(client, staff_headers, price=1000.0)
    booking = _create_booking(client, auth_headers, package["id"], days=92)
    assert booking["total_price"] == 1000.0

    updated = client.patch(
        f"/api/v1/staff/packages/{package['id']}",
        json={"price": 4321.0},
        headers=staff_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == 4321.0

    # 用户侧列表：订单金额仍是下单时的快照。
    mine = client.get("/api/v1/bookings/", headers=auth_headers).json()
    stored = next(item for item in mine if item["id"] == booking["id"])
    assert stored["total_price"] == 1000.0
    assert stored["currency"] == "EUR"

    # 员工详情同样是快照值，不受套餐改价影响。
    detail = client.get(
        f"/api/v1/staff/bookings/{booking['id']}", headers=staff_headers
    )
    assert detail.status_code == 200
    assert detail.json()["total_price"] == 1000.0

    # 新订单才使用新价格。
    fresh = _create_booking(client, auth_headers, package["id"], days=93)
    assert fresh["total_price"] == 4321.0


def test_package_delete_is_blocked_by_bookings(client, auth_headers) -> None:
    staff_headers = _make_staff(client)
    package = _create_package(client, staff_headers)
    _create_booking(client, auth_headers, package["id"], days=94)

    blocked = client.delete(
        f"/api/v1/staff/packages/{package['id']}", headers=staff_headers
    )
    assert blocked.status_code == 409
    assert "deactivate" in blocked.json()["detail"]

    unused = _create_package(client, staff_headers, price=250.0)
    deleted = client.delete(
        f"/api/v1/staff/packages/{unused['id']}", headers=staff_headers
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (
        client.get(
            f"/api/v1/staff/packages/{unused['id']}", headers=staff_headers
        ).status_code
        == 404
    )


def test_staff_package_create_and_update_validation(client) -> None:
    staff_headers = _make_staff(client)

    unknown_hospital = client.post(
        "/api/v1/staff/packages",
        json={"name": "x", "price": 10, "hospital_id": 999999},
        headers=staff_headers,
    )
    assert unknown_hospital.status_code == 422
    assert "Unknown hospital_id" in unknown_hospital.json()["detail"]

    package = _create_package(client, staff_headers)
    missing = client.patch(
        f"/api/v1/staff/packages/{package['id']}",
        json={"hospital_id": 999999},
        headers=staff_headers,
    )
    assert missing.status_code == 422

    assert (
        client.get(
            "/api/v1/staff/packages/999999", headers=staff_headers
        ).status_code
        == 404
    )

    # 分页边界与其它列表一致。
    assert (
        client.get(
            "/api/v1/staff/packages", params={"page": 0}, headers=staff_headers
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/staff/packages",
            params={"page_size": 101},
            headers=staff_headers,
        ).status_code
        == 422
    )


def test_hospital_crud_and_delete_protection(client) -> None:
    staff_headers = _make_staff(client)

    created = client.post(
        "/api/v1/staff/hospitals",
        json={"name": "测试医院", "name_en": "Test Hospital", "level": "三级甲等"},
        headers=staff_headers,
    )
    assert created.status_code == 201, created.text
    hospital = created.json()

    listing = client.get("/api/v1/staff/hospitals", headers=staff_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    assert hospital["id"] in [item["id"] for item in listing.json()["items"]]

    updated = client.patch(
        f"/api/v1/staff/hospitals/{hospital['id']}",
        json={"level": "二级甲等"},
        headers=staff_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["level"] == "二级甲等"
    assert updated.json()["name"] == "测试医院"

    package = _create_package(
        client, staff_headers, hospital_id=hospital["id"]
    )
    blocked = client.delete(
        f"/api/v1/staff/hospitals/{hospital['id']}", headers=staff_headers
    )
    assert blocked.status_code == 409
    assert "packages" in blocked.json()["detail"]

    assert (
        client.delete(
            f"/api/v1/staff/packages/{package['id']}", headers=staff_headers
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/staff/hospitals/{hospital['id']}", headers=staff_headers
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"/api/v1/staff/hospitals/{hospital['id']}", headers=staff_headers
        ).status_code
        == 404
    )


def test_destination_crud_and_reference_protection(client, auth_headers) -> None:
    staff_headers = _make_staff(client)
    slug = f"test-{secrets.token_hex(3)}"

    created = client.post(
        "/api/v1/staff/destinations",
        json={
            "id": slug,
            "name": "测试目的地",
            "name_en": "Test Destination",
            "tagline": "tagline",
            "sort_order": 99,
            "experiences": [
                {"icon": "T", "title": "体验", "description": "描述"}
            ],
        },
        headers=staff_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["id"] == slug
    assert created.json()["sort_order"] == 99
    assert created.json()["experiences"][0]["title"] == "体验"

    duplicate = client.post(
        "/api/v1/staff/destinations",
        json={"id": slug, "name": "重复", "name_en": "Duplicate"},
        headers=staff_headers,
    )
    assert duplicate.status_code == 409

    invalid_slug = client.post(
        "/api/v1/staff/destinations",
        json={"id": "Bad Slug!", "name": "坏", "name_en": "Bad"},
        headers=staff_headers,
    )
    assert invalid_slug.status_code == 422

    updated = client.patch(
        f"/api/v1/staff/destinations/{slug}",
        json={"tagline": "更新后的标语", "sort_order": 5},
        headers=staff_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["tagline"] == "更新后的标语"
    assert updated.json()["sort_order"] == 5
    assert updated.json()["name"] == "测试目的地"

    # 员工目的地列表返回 sort_order。
    listing = client.get(
        "/api/v1/staff/destinations?page=1&page_size=100", headers=staff_headers
    )
    assert listing.status_code == 200
    item = next(item for item in listing.json()["items"] if item["id"] == slug)
    assert item["sort_order"] == 5

    itinerary = client.post(
        "/api/v1/itineraries/",
        json={
            "title": "引用目的地的行程",
            "start_date": "2027-05-01",
            "end_date": "2027-05-03",
            "destination_ids": [slug],
            "days": [
                {"day_number": 1, "destination_ids": [slug], "notes": ""}
            ],
        },
        headers=auth_headers,
    )
    assert itinerary.status_code == 201, itinerary.text

    blocked = client.delete(
        f"/api/v1/staff/destinations/{slug}", headers=staff_headers
    )
    assert blocked.status_code == 409
    assert "referenced" in blocked.json()["detail"]

    assert (
        client.delete(
            f"/api/v1/itineraries/{itinerary.json()['id']}", headers=auth_headers
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/staff/destinations/{slug}", headers=staff_headers
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"/api/v1/staff/destinations/{slug}", headers=staff_headers
        ).status_code
        == 404
    )
