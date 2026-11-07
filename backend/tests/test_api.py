"""后端接口测试：目的地与行程。"""

TRIP = {
    "title": "Spring in China",
    "start_date": "2027-05-01",
    "end_date": "2027-05-03",
    "destination_ids": ["beijing", "shanghai"],
    "days": [
        {
            "day_number": 1,
            "destination_ids": ["beijing"],
            "notes": "Arrive and settle in.",
        },
        {
            "day_number": 2,
            "destination_ids": ["shanghai", "beijing"],
            "notes": "High-speed train.",
        },
        {"day_number": 3, "destination_ids": [], "notes": ""},
    ],
    "notes": "Overall plan.",
}


def test_destinations_are_seeded_and_filterable(client) -> None:
    response = client.get("/api/v1/destinations")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 4
    assert payload[0]["id"] == "beijing"
    assert payload[0]["experiences"][0]["title"]

    filtered = client.get("/api/v1/destinations", params={"query": "Shanghai"})
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == ["shanghai"]


def test_destination_detail_returns_404_for_unknown_id(client) -> None:
    response = client.get("/api/v1/destinations/unknown-city")
    assert response.status_code == 404


def test_itinerary_endpoints_require_authentication(client) -> None:
    assert client.get("/api/v1/itineraries").status_code == 401
    assert client.post("/api/v1/itineraries", json=TRIP).status_code == 401


def test_itinerary_crud_with_day_plans(client, auth_headers) -> None:
    created = client.post("/api/v1/itineraries", json=TRIP, headers=auth_headers)
    assert created.status_code == 201

    itinerary = created.json()
    itinerary_id = itinerary["id"]
    assert itinerary["title"] == TRIP["title"]
    assert itinerary["start_date"] == "2027-05-01"
    assert len(itinerary["days"]) == 3
    assert itinerary["days"][1]["destination_ids"] == ["shanghai", "beijing"]

    listed = client.get("/api/v1/itineraries", headers=auth_headers)
    assert listed.status_code == 200
    assert itinerary_id in [item["id"] for item in listed.json()]

    detail = client.get(f"/api/v1/itineraries/{itinerary_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["days"][0]["notes"] == "Arrive and settle in."

    updated_payload = {
        **TRIP,
        "title": "China spring trip",
        "destination_ids": ["beijing"],
        "days": [{"day_number": 1, "destination_ids": ["beijing"], "notes": "Only one day."}],
    }
    updated = client.put(
        f"/api/v1/itineraries/{itinerary_id}",
        json=updated_payload,
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "China spring trip"
    assert len(updated.json()["days"]) == 1
    assert updated.json()["days"][0]["notes"] == "Only one day."

    deleted = client.delete(
        f"/api/v1/itineraries/{itinerary_id}", headers=auth_headers
    )
    assert deleted.status_code == 204
    assert (
        client.get(f"/api/v1/itineraries/{itinerary_id}", headers=auth_headers).status_code
        == 404
    )


def test_itinerary_validation_rejects_bad_ranges(client, auth_headers) -> None:
    invalid_range = {**TRIP, "end_date": "2027-04-30"}
    assert (
        client.post(
            "/api/v1/itineraries", json=invalid_range, headers=auth_headers
        ).status_code
        == 422
    )

    empty_destinations = {**TRIP, "destination_ids": []}
    assert (
        client.post(
            "/api/v1/itineraries", json=empty_destinations, headers=auth_headers
        ).status_code
        == 422
    )

    day_out_of_range = {
        **TRIP,
        "days": [{"day_number": 10, "destination_ids": [], "notes": ""}],
    }
    assert (
        client.post(
            "/api/v1/itineraries", json=day_out_of_range, headers=auth_headers
        ).status_code
        == 422
    )


def test_itineraries_are_isolated_per_user(client, auth_headers) -> None:
    created = client.post("/api/v1/itineraries", json=TRIP, headers=auth_headers)
    itinerary_id = created.json()["id"]

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "pytest-other@meditour.com",
            "password": "Other123456",
            "preferred_language": "en",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "pytest-other@meditour.com", "password": "Other123456"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert (
        client.get(f"/api/v1/itineraries/{itinerary_id}", headers=other_headers).status_code
        == 404
    )
    assert client.get("/api/v1/itineraries", headers=other_headers).json() == []
