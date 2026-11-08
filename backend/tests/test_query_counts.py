"""列表接口查询次数：单次请求的 SELECT 数必须是常数，不随条数增长。

用 SQLAlchemy 的 before_cursor_execute 事件统计 SELECT，覆盖用户侧订单、
行程、套餐、医院、目的地与员工侧订单列表。运行 `pytest -s` 可看到明细。
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import event, select

from app.database import SessionLocal, engine
from app.models import User


@contextmanager
def count_selects():
    counter = {"n": 0}

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        if statement.lstrip().upper().startswith("SELECT"):
            counter["n"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def _count(client, method: str, url: str, headers=None, **kwargs) -> int:
    with count_selects() as counter:
        response = client.request(method, url, headers=headers, **kwargs)
    assert response.status_code == 200, response.text
    return counter["n"]


def _register(client, email: str, password: str = "QueryPass123456") -> dict:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Query User",
            "preferred_language": "en",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_list_endpoint_query_counts_are_constant(client) -> None:
    email = "query-count@meditour.com"
    headers = _register(client, email)

    package = client.get("/api/v1/medical/packages?page_size=1").json()["items"][0]
    package_id = package["id"]

    def create_booking(offset_days: int) -> None:
        response = client.post(
            "/api/v1/bookings/",
            json={
                "package_id": package_id,
                "appointment_date": (
                    datetime.now(timezone.utc).replace(tzinfo=None)
                    + timedelta(days=offset_days)
                ).isoformat(timespec="seconds"),
                "contact_name": "Query User",
                "contact_phone": "+491111111",
                "contact_email": email,
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text

    create_booking(30)
    create_booking(31)
    bookings_few = _count(client, "GET", "/api/v1/bookings/", headers)
    for offset in range(6):
        create_booking(40 + offset)
    bookings_many = _count(client, "GET", "/api/v1/bookings/", headers)

    def create_itinerary(index: int) -> None:
        response = client.post(
            "/api/v1/itineraries",
            json={
                "title": f"Query trip {index}",
                "start_date": "2026-12-01",
                "end_date": "2026-12-03",
                "destination_ids": ["beijing"],
                "days": [
                    {"day_number": 1, "destination_ids": ["beijing"], "notes": ""},
                    {"day_number": 2, "destination_ids": ["shanghai"], "notes": ""},
                ],
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text

    create_itinerary(1)
    create_itinerary(2)
    itineraries_few = _count(client, "GET", "/api/v1/itineraries", headers)
    for index in range(3, 9):
        create_itinerary(index)
    itineraries_many = _count(client, "GET", "/api/v1/itineraries", headers)

    packages_few = _count(client, "GET", "/api/v1/medical/packages?page_size=1")
    packages_many = _count(client, "GET", "/api/v1/medical/packages?page_size=100")
    hospitals_few = _count(client, "GET", "/api/v1/medical/hospitals")
    destinations = _count(client, "GET", "/api/v1/destinations")

    print()
    print(f"GET /bookings/        2 条 -> {bookings_few} 次; 8 条 -> {bookings_many} 次")
    print(
        "GET /itineraries      2 条 -> "
        f"{itineraries_few} 次; 8 条 -> {itineraries_many} 次"
    )
    print(
        "GET /medical/packages page_size=1 -> "
        f"{packages_few} 次; page_size=100 -> {packages_many} 次"
    )
    print(f"GET /medical/hospitals -> {hospitals_few} 次")
    print(f"GET /destinations      -> {destinations} 次")

    assert bookings_few == bookings_many, "订单列表查询次数随条数增长"
    assert itineraries_few == itineraries_many, "行程列表查询次数随条数增长"
    assert packages_few == packages_many, "套餐列表查询次数随分页大小增长"
    assert itineraries_few == 5, (
        "行程列表应为 5 次查询（吊销检查 + 会话检查 + 当前用户 + 行程 + "
        f"每日安排批量加载），实际 {itineraries_few}"
    )

    # 员工侧列表：比较 page_size=2 与 20，查询次数应与分页大小无关。
    staff_email = "query-count-staff@meditour.com"
    staff_headers = _register(client, staff_email)
    with SessionLocal() as db:
        staff = db.scalar(select(User).where(User.email == staff_email))
        assert staff is not None
        staff.role = "staff"
        db.commit()

    staff_few = _count(
        client, "GET", "/api/v1/staff/bookings?page=1&page_size=2", staff_headers
    )
    staff_many = _count(
        client, "GET", "/api/v1/staff/bookings?page=1&page_size=20", staff_headers
    )
    print(
        "GET /staff/bookings    page_size=2 -> "
        f"{staff_few} 次; page_size=20 -> {staff_many} 次"
    )
    assert staff_few == staff_many, "员工订单列表查询次数随分页大小增长"
