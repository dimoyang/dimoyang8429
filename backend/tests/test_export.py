"""用户数据导出测试：只导出本人数据，且不包含凭据。"""

from datetime import datetime, timedelta, timezone


def register_and_login(client, email: str, password: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def future_iso(days: int = 120) -> str:
    value = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
    return value.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()


def test_export_returns_own_account_bookings_and_itineraries(client) -> None:
    email = "export-user@meditour.com"
    headers = register_and_login(client, email, "ExportPass123")

    booking = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": 1,
            "appointment_date": future_iso(120),
            "contact_name": "Export User",
            "contact_phone": "+86 138-2222-3333",
            "contact_email": email,
            "notes": "export note",
        },
        headers=headers,
    )
    assert booking.status_code == 201
    order_no = booking.json()["order_no"]

    itinerary = client.post(
        "/api/v1/itineraries",
        json={
            "title": "Export trip",
            "start_date": "2027-07-01",
            "end_date": "2027-07-02",
            "destination_ids": ["beijing"],
            "days": [
                {"day_number": 1, "destination_ids": ["beijing"], "notes": "day one"}
            ],
            "notes": "trip note",
        },
        headers=headers,
    )
    assert itinerary.status_code == 201

    response = client.get("/api/v1/auth/export", headers=headers)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert ".json" in response.headers["content-disposition"]

    payload = response.json()
    assert payload["format_version"] == 1
    assert payload["account"]["email"] == email
    assert payload["account"]["preferred_language"] == "en"

    assert [item["order_no"] for item in payload["bookings"]] == [order_no]
    assert payload["bookings"][0]["contact_email"] == email
    assert payload["bookings"][0]["notes"] == "export note"

    assert [item["title"] for item in payload["itineraries"]] == ["Export trip"]
    assert payload["itineraries"][0]["days"][0]["notes"] == "day one"

    assert payload["favorites"] == []

    # 导出内容只含用户数据，不包含密码哈希或令牌。
    raw = response.text.lower()
    assert "password" not in raw
    assert "token" not in raw


def test_export_does_not_include_other_users_data(client) -> None:
    first_headers = register_and_login(
        client, "export-first@meditour.com", "FirstPass123"
    )
    first_booking = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": 1,
            "appointment_date": future_iso(121),
            "contact_name": "First User",
            "contact_phone": "+86 138-3333-4444",
            "contact_email": "export-first@meditour.com",
        },
        headers=first_headers,
    )
    assert first_booking.status_code == 201
    first_order_no = first_booking.json()["order_no"]

    client.post(
        "/api/v1/itineraries",
        json={
            "title": "First trip",
            "start_date": "2027-08-01",
            "end_date": "2027-08-01",
            "destination_ids": ["beijing"],
            "days": [],
            "notes": "",
        },
        headers=first_headers,
    )

    second_headers = register_and_login(
        client, "export-second@meditour.com", "SecondPass123"
    )
    response = client.get("/api/v1/auth/export", headers=second_headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["account"]["email"] == "export-second@meditour.com"
    assert payload["bookings"] == []
    assert payload["itineraries"] == []
    assert first_order_no not in response.text


def test_export_requires_authentication(client) -> None:
    assert client.get("/api/v1/auth/export").status_code == 401
