"""预约列表字段测试：前端订单页依赖的展示字段。"""

from datetime import datetime


def test_booking_list_returns_display_fields(client, auth_headers) -> None:
    packages = client.get("/api/v1/medical/packages?page=1&page_size=100").json()
    package = packages["items"][0]

    payload = {
        "package_id": package["id"],
        "appointment_date": "2026-01-02T09:00:00.000",
        "contact_name": "Booking Test",
        "contact_phone": "+8613800000000",
        "contact_email": "pytest-booking@meditour.com",
        "notes": "display fields",
        "need_translator": False,
        "need_accommodation": False,
        "need_pickup": False,
    }
    created = client.post("/api/v1/bookings/", json=payload, headers=auth_headers)
    assert created.status_code == 201
    body = created.json()

    assert body["package_id"] == package["id"]
    assert body["package_name"] == package["name"]
    assert body["package_name_en"] == package["name_en"]
    assert body["appointment_date"] == "2026-01-02T09:00:00"
    assert datetime.fromisoformat(body["created_at"].replace("Z", "+00:00")).tzinfo

    listed = client.get("/api/v1/bookings/", headers=auth_headers)
    assert listed.status_code == 200
    item = next(
        booking for booking in listed.json() if booking["id"] == body["id"]
    )

    assert item["package_id"] == package["id"]
    assert item["package_name"] == package["name"]
    assert item["package_name_en"] == package["name_en"]
    assert datetime.fromisoformat(item["appointment_date"]) == datetime(
        2026, 1, 2, 9, 0
    )
    assert datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")).tzinfo
