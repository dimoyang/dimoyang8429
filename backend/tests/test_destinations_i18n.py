"""目的地多语言接口：向后兼容、请求语言 → en → zh 回退与数组字段类型。

译文直接写 content_translations，避免依赖演示种子数据；每个用例结束后清理，
不污染后续测试（尤其是翻译导入测试要断言导入计数）。
"""

import pytest
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import ContentTranslation

BEIJING = "beijing"
SHANGHAI = "shanghai"

DE_TRANSLATIONS = {
    "name": "Peking (Test)",
    "tagline": "Kaiserstadt",
    "intro": "Deutsche Einleitung",
    "best_season": "April bis Mai",
    "suggest_days": "4-6 Tage",
}

FR_TRANSLATIONS = {
    "name": "Pékin",
    "intro": "Introduction française",
}


def _delete_destination_translations() -> None:
    with SessionLocal() as db:
        db.execute(
            delete(ContentTranslation).where(
                ContentTranslation.entity_type == "destination"
            )
        )
        db.commit()


@pytest.fixture()
def destination_translations():
    _delete_destination_translations()
    with SessionLocal() as db:
        for lang, fields in (("de", DE_TRANSLATIONS), ("fr", FR_TRANSLATIONS)):
            for field, value in fields.items():
                db.add(
                    ContentTranslation(
                        entity_type="destination",
                        entity_id=BEIJING,
                        lang=lang,
                        field=field,
                        value=value,
                    )
                )
        db.commit()
    yield
    _delete_destination_translations()


def _listing(client, **params) -> list[dict]:
    response = client.get("/api/v1/destinations", params=params)
    assert response.status_code == 200
    return response.json()


def _by_id(payload: list[dict], destination_id: str) -> dict:
    for item in payload:
        if item["id"] == destination_id:
            return item
    raise AssertionError(f"未找到目的地 {destination_id}")


def _detail(client, destination_id: str, **params) -> dict:
    response = client.get(f"/api/v1/destinations/{destination_id}", params=params)
    assert response.status_code == 200
    return response.json()


def test_without_lang_response_is_unchanged(client, destination_translations) -> None:
    baseline = _listing(client)
    beijing = _by_id(baseline, BEIJING)
    assert beijing["name"] == "北京"
    assert beijing["name_en"] == "Beijing"
    assert beijing["tagline"] == "千年古都，历史与现代交汇"
    assert beijing["search_terms"] == ["北京", "Beijing", "长城", "Great Wall", "故宫"]

    # 显式 zh 与不传 lang 完全一致。
    assert _listing(client, lang="zh") == baseline
    assert _detail(client, BEIJING, lang="zh") == _detail(client, BEIJING)


def test_lang_de_translates_scalars_and_keeps_arrays(
    client, destination_translations
) -> None:
    baseline = _by_id(_listing(client), BEIJING)
    beijing = _by_id(_listing(client, lang="de"), BEIJING)

    for field, expected in DE_TRANSLATIONS.items():
        assert beijing[field] == expected, field
    # name_en 是主数据列，不随 lang 变化。
    assert beijing["name_en"] == "Beijing"
    # 数组字段不翻译，类型与内容与主数据一致。
    for field in ("search_terms", "experiences", "tips"):
        assert beijing[field] == baseline[field], field
    assert isinstance(beijing["search_terms"], list)
    assert all(isinstance(term, str) for term in beijing["search_terms"])
    assert isinstance(beijing["experiences"], list)
    assert all(isinstance(item, dict) for item in beijing["experiences"])
    assert isinstance(beijing["tips"], list)
    assert all(isinstance(tip, str) for tip in beijing["tips"])


def test_lang_fr_uses_translation_and_falls_back_to_zh(
    client, destination_translations
) -> None:
    beijing = _detail(client, BEIJING, lang="fr")
    assert beijing["name"] == FR_TRANSLATIONS["name"]
    assert beijing["intro"] == FR_TRANSLATIONS["intro"]
    # 没有法语译文、也没有英文列：回退中文主数据，而不是德语译文。
    assert beijing["tagline"] == "千年古都，历史与现代交汇"
    assert beijing["best_season"] == "4-5月 / 9-10月"


def test_lang_de_without_translation_falls_back_to_english(
    client, destination_translations
) -> None:
    shanghai = _by_id(_listing(client, lang="de"), SHANGHAI)
    assert shanghai["name"] == "Shanghai"
    assert shanghai["name_en"] == "Shanghai"
    # 其余标量字段没有英文列，回退中文。
    assert shanghai["tagline"] == "东方巴黎，黄浦江畔的摩登风情"


def test_lang_en_uses_existing_english_columns(
    client, destination_translations
) -> None:
    beijing = _by_id(_listing(client, lang="en"), BEIJING)
    assert beijing["name"] == "Beijing"
    assert beijing["name_en"] == "Beijing"
    # 英文主数据优先于 de/fr 译文。
    assert beijing["tagline"] == "千年古都，历史与现代交汇"


def test_lang_is_case_insensitive(client, destination_translations) -> None:
    assert _listing(client, lang="DE") == _listing(client, lang="de")
    assert _detail(client, BEIJING, lang="Fr") == _detail(client, BEIJING, lang="fr")


def test_unsupported_lang_is_rejected(client) -> None:
    listing = client.get("/api/v1/destinations", params={"lang": "it"})
    assert listing.status_code == 422
    assert isinstance(listing.json()["detail"], str)

    detail = client.get(f"/api/v1/destinations/{BEIJING}", params={"lang": "it"})
    assert detail.status_code == 422


def test_detail_still_404s_for_unknown_slug_with_lang(client) -> None:
    response = client.get(
        "/api/v1/destinations/unknown-city", params={"lang": "de"}
    )
    assert response.status_code == 404


def test_lang_filter_query_still_works(client, destination_translations) -> None:
    payload = _listing(client, query="Shanghai", lang="de")
    assert [item["id"] for item in payload] == [SHANGHAI]


def test_translations_are_loaded_for_all_listed_destinations(
    client, destination_translations
) -> None:
    """一次列表请求不该因目的地数量产生 N+1：只校验结果，查询次数由
    test_query_counts 统一约束。"""
    payload = _listing(client, lang="de")
    assert len(payload) >= 4
    translated = [item for item in payload if item["id"] == BEIJING][0]
    assert translated["name"] == DE_TRANSLATIONS["name"]
    others = [item for item in payload if item["id"] != BEIJING]
    assert all(item["name"] for item in others)


def test_translations_are_stored_in_table(client, destination_translations) -> None:
    with SessionLocal() as db:
        stored = db.scalars(
            select(ContentTranslation.entity_id).where(
                ContentTranslation.entity_type == "destination"
            )
        ).all()
    # 确认测试数据确实写进了表，而不是只存在于本地变量。
    assert set(stored) == {BEIJING}
