"""医疗内容多语言接口测试：向后兼容与 de → en → zh 回退。"""


def packages(client, **params) -> dict:
    response = client.get("/api/v1/medical/packages", params=params)
    assert response.status_code == 200
    return response.json()


def by_english_name(payload: dict, name_en: str) -> dict:
    for item in payload["items"]:
        if item["name_en"] == name_en:
            return item
    raise AssertionError(f"未找到套餐 {name_en}")


def test_without_lang_response_is_unchanged(client) -> None:
    baseline = packages(client, page=1, page_size=100)
    assert baseline["items"][0]["name"] == "膝关节置换手术"
    assert baseline["items"][0]["name_en"] == "Knee Replacement Surgery"

    explicit_zh = packages(client, page=1, page_size=100, lang="zh")
    assert explicit_zh == baseline


def test_lang_en_uses_existing_english_columns(client) -> None:
    payload = packages(client, page=1, page_size=100, lang="en")
    knee = by_english_name(payload, "Knee Replacement Surgery")
    assert knee["name"] == "Knee Replacement Surgery"
    # name_en 字段本身保持英文，不因 lang 改变语义。
    assert knee["name_en"] == "Knee Replacement Surgery"


def test_lang_de_uses_translation_and_falls_back_to_english(client) -> None:
    payload = packages(client, page=1, page_size=100, lang="de")
    knee = by_english_name(payload, "Knee Replacement Surgery")
    assert knee["name"] == "Kniegelenkersatz (Knie-TEP)"
    assert knee["description"].startswith("Durchgeführt von einem erfahrenen")

    # 种植牙没有德语译文：回退到英文，而不是中文。
    implants = by_english_name(payload, "Dental Implants")
    assert implants["name"] == "Dental Implants"
    assert implants["description"].startswith("Digitally guided implant surgery")

    hospitals = client.get("/api/v1/medical/hospitals", params={"lang": "de"})
    assert hospitals.status_code == 200
    names = {item["name_en"]: item["name"] for item in hospitals.json()}
    assert names["Peking Union Medical College Hospital"] == "Peking-Union-Krankenhaus"
    # 未翻译的医院回退英文。
    assert (
        names["Peking University School of Stomatology"]
        == "Peking University School of Stomatology"
    )


def test_unsupported_lang_is_rejected(client) -> None:
    response = client.get("/api/v1/medical/packages", params={"lang": "it"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)

    hospitals = client.get("/api/v1/medical/hospitals", params={"lang": "it"})
    assert hospitals.status_code == 422
