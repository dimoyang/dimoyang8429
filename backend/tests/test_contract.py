"""前后端契约核对：实际响应字段名、类型、可空性与前端解析需求逐项对照。

期望值来自只读的前端模型：

- `lib/data/models/user_profile.dart`        -> UserProfile
- `lib/data/models/hospital.dart`            -> HospitalInfo
- `lib/data/models/medical_service.dart`     -> MedicalService.fromPackage
- `lib/data/models/destination.dart`         -> Destination
- `lib/data/models/booking.dart`             -> BookingOrder / BookingResult
- `lib/core/network/api_service.dart`        -> AuthTokens（access_token 必须是 String）

只校验前端**确实读取**的字段；后端额外的字段允许存在（前端会忽略）。
可空字段用 `("nullable", spec)` 表示，`None` 也算通过。

运行 `pytest tests/test_contract.py -s` 会打印逐端点核对结果与差异清单。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

USER_SPEC = {
    "id": "int",
    "email": "str",
    "full_name": ("nullable", "str"),
    "phone": ("nullable", "str"),
    "preferred_language": "str",
}

TOKEN_SPEC = {
    "access_token": "str",
    "refresh_token": "str",
    "token_type": "str",
    "role": "str",
    "email_verified": "bool",
}

PACKAGE_SPEC = {
    "id": "int",
    "name": "str",
    "name_en": "str",
    # 前端用 (json['price'] as num).toDouble()，整数价格也能接受。
    "price": "number",
    "currency": "str",
    "duration_days": "int",
    "image_url": "str",
    "description": "str",
    "description_en": "str",
    "category": "str",
    "hospital_id": "int",
}

HOSPITAL_SPEC = {
    "id": "int",
    "name": "str",
    "name_en": "str",
    "level": "str",
}

DESTINATION_SPEC = {
    "id": "str",
    "name": "str",
    "name_en": "str",
    "tagline": "str",
    "image_url": "str",
    "search_terms": ("list_of", "str"),
    "best_season": "str",
    "suggest_days": "str",
    "intro": "str",
    "experiences": ("list_of", {"icon": "str", "title": "str", "description": "str"}),
    "tips": ("list_of", "str"),
}

BOOKING_SPEC = {
    "id": "int",
    "order_no": "str",
    "package_id": "int",
    "appointment_date": "str",
    "total_price": "number",
    "currency": "str",
    "status": "str",
    "created_at": "str",
}

EXPORT_SPEC = {
    "exported_at": "str",
    "format_version": "int",
    "account": {
        "id": "int",
        "email": "str",
        "full_name": ("nullable", "str"),
        "phone": ("nullable", "str"),
        "preferred_language": "str",
        "created_at": "str",
    },
    "bookings": ("list_of", "dict"),
    "itineraries": ("list_of", "dict"),
    "favorites": "list",
}


def _type_name(value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _matches(value, spec: str) -> bool:
    if spec == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if spec == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if spec == "dict":
        return isinstance(value, dict)
    return _type_name(value) == spec


def _check(value, spec, path: str, errors: list[str]) -> int:
    """返回本次校验的字段数；差异写入 errors。"""
    if isinstance(spec, tuple):
        kind, inner = spec
        if kind == "nullable":
            if value is None:
                return 1
            return _check(value, inner, path, errors)
        if kind == "list_of":
            if not isinstance(value, list):
                errors.append(f"{path}: 期望 list，实际 {_type_name(value)}")
                return 1
            checked = 1
            for index, item in enumerate(value):
                checked += _check(item, inner, f"{path}[{index}]", errors)
            return checked
        raise AssertionError(f"未知的契约规则 {kind}")

    if isinstance(spec, dict):
        if not isinstance(value, dict):
            errors.append(f"{path}: 期望 dict，实际 {_type_name(value)}")
            return 1
        checked = 1
        for field, field_spec in spec.items():
            field_path = f"{path}.{field}" if path else field
            if field not in value:
                errors.append(f"{field_path}: 缺失（前端会直接抛异常）")
                checked += 1
                continue
            checked += _check(value[field], field_spec, field_path, errors)
        return checked

    if not _matches(value, spec):
        actual = _type_name(value)
        errors.append(f"{path}: 期望 {spec}，实际 {actual}（{value!r}）")
    return 1


def _report(name: str, payload, spec) -> list[str]:
    errors: list[str] = []
    checked = _check(payload, spec, name, errors)
    status = "OK" if not errors else f"{len(errors)} 处差异"
    print(f"  {name}: {checked} 个字段 -> {status}")
    return errors


def test_frontend_contract_matches_backend(client) -> None:
    email = "contract-check@meditour.com"
    password = "Contract123456"
    details: list[str] = []

    register = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Contract User",
            "preferred_language": "en",
        },
    )
    assert register.status_code == 201, register.text
    details += _report("POST /auth/register", register.json(), USER_SPEC)

    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    details += _report("POST /auth/login", login.json(), TOKEN_SPEC)
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    details += _report("GET /auth/me", me.json(), USER_SPEC)

    packages = client.get("/api/v1/medical/packages?page_size=3")
    assert packages.status_code == 200, packages.text
    details += _report(
        "GET /medical/packages",
        packages.json(),
        {
            "items": ("list_of", PACKAGE_SPEC),
            "total": "int",
            "page": "int",
            "page_size": "int",
            "pages": "int",
        },
    )

    hospitals = client.get("/api/v1/medical/hospitals")
    assert hospitals.status_code == 200, hospitals.text
    details += _report(
        "GET /medical/hospitals", hospitals.json(), ("list_of", HOSPITAL_SPEC)
    )

    destinations = client.get("/api/v1/destinations")
    assert destinations.status_code == 200, destinations.text
    details += _report(
        "GET /destinations", destinations.json(), ("list_of", DESTINATION_SPEC)
    )

    package_id = packages.json()["items"][0]["id"]
    created = client.post(
        "/api/v1/bookings/",
        json={
            "package_id": package_id,
            "appointment_date": (
                datetime.now(timezone.utc).replace(tzinfo=None)
                + timedelta(days=45)
            ).isoformat(timespec="seconds"),
            "contact_name": "Contract User",
            "contact_phone": "+4912345678",
            "contact_email": email,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    details += _report("POST /bookings/", created.json(), BOOKING_SPEC)

    my_bookings = client.get("/api/v1/bookings/", headers=headers)
    assert my_bookings.status_code == 200, my_bookings.text
    details += _report(
        "GET /bookings/", my_bookings.json(), ("list_of", BOOKING_SPEC)
    )

    booking_id = created.json()["id"]
    cancelled = client.post(
        f"/api/v1/bookings/{booking_id}/cancel", headers=headers
    )
    assert cancelled.status_code == 200, cancelled.text
    details += _report(
        "POST /bookings/{id}/cancel", cancelled.json(), BOOKING_SPEC
    )

    exported = client.get("/api/v1/auth/export", headers=headers)
    assert exported.status_code == 200, exported.text
    details += _report("GET /auth/export", exported.json(), EXPORT_SPEC)

    # 客户端没有消费的端点：会话管理、指标、员工侧接口。
    print("  （未核对：/auth/sessions、/metrics、/staff/* —— 前端当前未解析）")

    if details:
        print("\n差异清单：")
        for line in details:
            print(f"  - {line}")
    assert not details, f"前后端契约存在 {len(details)} 处差异"
