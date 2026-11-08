"""列表分页统一规则、裸数组契约与索引存在性。"""

from sqlalchemy import inspect

from app.database import engine


def test_packages_pagination_limits(client) -> None:
    ok = client.get(
        "/api/v1/medical/packages", params={"page": 1, "page_size": 1}
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert body["total"] >= 1
    assert body["pages"] == body["total"]
    assert len(body["items"]) == 1

    # 页码从 1 开始、page_size 上限 100，越界属于请求参数错误。
    assert (
        client.get("/api/v1/medical/packages", params={"page": 0}).status_code
        == 422
    )
    assert (
        client.get(
            "/api/v1/medical/packages", params={"page_size": 101}
        ).status_code
        == 422
    )

    # 超出末页返回空 items，但 total 仍反映真实总数。
    beyond = client.get(
        "/api/v1/medical/packages", params={"page": 99, "page_size": 100}
    )
    assert beyond.status_code == 200
    assert beyond.json()["items"] == []
    assert beyond.json()["total"] >= 1


def test_bare_array_contracts_are_preserved(client, auth_headers) -> None:
    # 前端按裸数组解析，不能改成 {items: ...}。
    hospitals = client.get("/api/v1/medical/hospitals")
    assert hospitals.status_code == 200
    assert isinstance(hospitals.json(), list)

    bookings = client.get("/api/v1/bookings/", headers=auth_headers)
    assert bookings.status_code == 200
    assert isinstance(bookings.json(), list)


def test_query_indexes_match_query_paths() -> None:
    inspector = inspect(engine)

    bookings = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("bookings")
    }
    assert bookings["ix_bookings_user_status"] == ("user_id", "status")
    assert bookings["ix_bookings_status_created_at"] == (
        "status",
        "created_at",
    )
    assert bookings["ix_bookings_created_at"] == ("created_at",)
    # 单列索引已被复合索引前缀取代，避免重复维护。
    assert "ix_bookings_user_id" not in bookings

    itineraries = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("itineraries")
    }
    assert itineraries["ix_itineraries_user_start"] == (
        "user_id",
        "start_date",
    )
    assert "ix_itineraries_user_id" not in itineraries

    translations = {
        index["name"]: tuple(index["column_names"])
        for index in inspector.get_indexes("content_translations")
    }
    # 唯一约束 (entity_type, entity_id, lang, field) 已覆盖同样的查询前缀。
    assert "ix_content_translations_lookup" not in translations
