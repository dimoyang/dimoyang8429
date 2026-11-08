#!/usr/bin/env python3
"""MediTour 后端接口验证脚本（仅使用 Python 标准库）。

逐条验证前端依赖的 /api/v1 契约：注册、登录、鉴权、套餐、医院、预约、
CORS 预检以及错误体形状。

前置：先启动后端（在 i:\\meditour_app\\backend 下）
    $env:MEDITOUR_SECRET_KEY="<本地密钥>"
    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

运行示例（系统 Python 即可，无需安装任何依赖）：
    python backend/scripts/verify_api.py
    python backend/scripts/verify_api.py --base-url http://10.0.2.2:8000/api/v1
    python backend/scripts/verify_api.py --base-url http://192.168.1.10:8000/api/v1
    python backend/scripts/verify_api.py --cleanup

每次运行都会注册一个带时间戳和随机后缀的独立账号，不会改动演示账号。
--cleanup 仅作用于本机默认的 backend/meditour.db；远程目标请手动清理。
"""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "meditour.db"


class ConnectionFailure(RuntimeError):
    """无法连接后端（端口未监听、DNS 失败、超时等）。"""


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: object


def _decode_body(raw: bytes) -> object:
    if not raw:
        return None
    text = raw.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def request(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> Response:
    req = urllib.request.Request(
        url, data=data, headers=headers or {}, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, dict(resp.headers), _decode_body(resp.read()))
    except urllib.error.HTTPError as exc:
        return Response(exc.code, dict(exc.headers), _decode_body(exc.read()))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ConnectionFailure(str(reason)) from exc


def header(headers: dict[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def is_int(value: object) -> bool:
    # 显式排除 bool：Python 中 bool 是 int 的子类。
    return type(value) is int


def is_number(value: object) -> bool:
    return type(value) in (int, float)


def is_str(value: object) -> bool:
    return type(value) is str


def is_iso_datetime(value: object) -> bool:
    if not is_str(value) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def fmt(value: object, limit: int = 260) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text if len(text) <= limit else text[:limit] + "..."


class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, condition: bool, label: str, detail: str = "") -> bool:
        if condition:
            self.passed += 1
            print(f"  PASS  {label}" + (f" | {detail}" if detail else ""))
        else:
            self.failed += 1
            print(f"  FAIL  {label}" + (f" | {detail}" if detail else ""))
        return condition

    def note(self, text: str) -> None:
        print(f"  NOTE  {text}")

    def section(self, index: int, title: str) -> None:
        print(f"\n[{index}/9] {title}")


class ApiClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get(self, path: str, token: str | None = None, **kwargs) -> Response:
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return request(
            "GET", self.url(path), headers=headers, timeout=self.timeout, **kwargs
        )

    def post_json(
        self, path: str, payload: object, token: str | None = None
    ) -> Response:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return request(
            "POST",
            self.url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            timeout=self.timeout,
        )

    def post_form(self, path: str, fields: dict[str, str]) -> Response:
        return request(
            "POST",
            self.url(path),
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )


def cleanup_local(email: str, db_path: Path) -> None:
    if not db_path.exists():
        print(f"  清理跳过：未找到本地数据库 {db_path}")
        return
    conn = sqlite3.connect(db_path)
    try:
        bookings = conn.execute(
            "DELETE FROM bookings WHERE user_id IN "
            "(SELECT id FROM users WHERE email = ?)",
            (email,),
        ).rowcount
        users = conn.execute(
            "DELETE FROM users WHERE email = ?", (email,)
        ).rowcount
        conn.commit()
    finally:
        conn.close()
    print(f"  清理完成：users={users}, bookings={bookings}（{db_path}）")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="逐条验证 MediTour 后端 /api/v1 接口契约（仅标准库）。"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"后端 API 基址，默认 {DEFAULT_BASE_URL}；Android 模拟器可用 "
        "http://10.0.2.2:8000/api/v1",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="单次请求超时秒数，默认 10"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="验证后从本机默认 SQLite（backend/meditour.db）删除本次测试账号与订单",
    )
    args = parser.parse_args()

    api = ApiClient(args.base_url, args.timeout)
    checker = Checker()
    suffix = f"{datetime.now():%Y%m%d%H%M%S}-{secrets.token_hex(3)}"
    email = f"verify-{suffix}@meditour.com"
    password = "VerifyPass123"

    print(f"目标: {args.base_url}")
    print(f"测试账号: {email}")

    try:
        request(
            "GET", api.url("/medical/hospitals"), timeout=args.timeout
        )
    except ConnectionFailure as exc:
        print(f"\n无法连接后端: {args.base_url}")
        print(f"原因: {exc}")
        print("请先启动后端（在 i:\\meditour_app\\backend 下）：")
        print('  $env:MEDITOUR_SECRET_KEY="<本地密钥>"')
        print(
            "  .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app "
            "--host 0.0.0.0 --port 8000"
        )
        print("若后端在其它主机/端口，请用 --base-url 指定。")
        print("\n汇总: 通过 0 / 失败 1（连接失败）")
        return 2

    # 1. 注册
    checker.section(1, "注册")
    register_payload = {
        "email": email,
        "password": password,
        "full_name": "API Verifier",
        "preferred_language": "zh",
    }
    reg = api.post_json("/auth/register", register_payload)
    checker.check(
        reg.status == 201,
        "POST /auth/register 返回 201",
        f"实际 {reg.status} {fmt(reg.body)}",
    )
    if isinstance(reg.body, dict):
        checker.check(
            is_int(reg.body.get("id")),
            "注册响应 id 为 int",
            f"实际 {fmt(reg.body.get('id'))}",
        )

    dup = api.post_json("/auth/register", register_payload)
    checker.check(
        dup.status != 201
        and isinstance(dup.body, dict)
        and "detail" in dup.body,
        "重复邮箱未创建第二个账号",
        f"实际 {dup.status} {fmt(dup.body)}",
    )
    if dup.status == 409:
        checker.note("当前后端对重复邮箱返回 409，错误体为 {\"detail\": ...}。")
    else:
        checker.note(f"重复邮箱实际返回 {dup.status}：{fmt(dup.body)}")

    # 2. 登录
    checker.section(2, "登录（form-urlencoded）")
    login = api.post_form(
        "/auth/login", {"username": email, "password": password}
    )
    token = login.body.get("access_token") if isinstance(login.body, dict) else None
    checker.check(
        login.status == 200, "正确账号返回 200", f"实际 {login.status}"
    )
    checker.check(
        is_str(token) and bool(token),
        "access_token 为非空字符串",
        f"长度 {len(token) if isinstance(token, str) else 'N/A'}",
    )

    bad_login = api.post_form(
        "/auth/login", {"username": email, "password": "WrongPassword123"}
    )
    checker.check(
        bad_login.status == 401,
        "错误密码返回 401",
        f"实际 {bad_login.status} {fmt(bad_login.body)}",
    )

    # 3. /auth/me
    checker.section(3, "/auth/me 鉴权")
    me = api.get("/auth/me", token=token)
    me_body = me.body if isinstance(me.body, dict) else {}
    checker.check(me.status == 200, "带 token 返回 200", f"实际 {me.status}")
    checker.check(is_int(me_body.get("id")), "id 为 int")
    checker.check(is_str(me_body.get("email")), "email 为 str")
    checker.check(
        "preferred_language" in me_body
        and is_str(me_body.get("preferred_language")),
        "preferred_language 存在且为 str",
        f"实际 {fmt(me_body.get('preferred_language'))}",
    )

    no_token = api.get("/auth/me")
    checker.check(
        no_token.status == 401,
        "无 token 返回 401",
        f"实际 {no_token.status} {fmt(no_token.body)}",
    )

    forged = api.get(
        "/auth/me",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.invalid.signature"},
    )
    checker.check(
        forged.status == 401,
        "伪造/损坏 token 返回 401",
        f"实际 {forged.status} {fmt(forged.body)}",
    )

    # 4. /medical/packages
    checker.section(4, "/medical/packages 分页与字段")
    packages = api.get("/medical/packages?page=1&page_size=100")
    pkg_body = packages.body if isinstance(packages.body, dict) else {}
    checker.check(
        packages.status == 200,
        "返回 200",
        f"实际 {packages.status}",
    )
    for field in ("items", "total", "page", "page_size", "pages"):
        checker.check(field in pkg_body, f"外层包含 {field}")
    items = pkg_body.get("items") if isinstance(pkg_body.get("items"), list) else []
    checker.check(isinstance(items, list), "items 为数组", f"条数 {len(items)}")

    item_rules = {
        "id": (is_int, "int"),
        "name": (is_str, "str"),
        "name_en": (is_str, "str"),
        "price": (is_number, "number"),
        "currency": (is_str, "str"),
        "duration_days": (is_int, "int"),
        "image_url": (is_str, "str"),
        "description": (is_str, "str"),
        "description_en": (is_str, "str"),
        "category": (is_str, "str"),
        "hospital_id": (is_int, "int"),
    }
    problems: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"items[{index}] 不是对象")
            continue
        for field, (predicate, expected) in item_rules.items():
            if field not in item:
                problems.append(f"items[{index}].{field} 缺失")
            elif not predicate(item[field]):
                problems.append(
                    f"items[{index}].{field} 应为 {expected}，"
                    f"实际 {type(item[field]).__name__}"
                )
    checker.check(
        bool(items) and not problems,
        "items 每个元素字段与类型严格匹配",
        "全部通过" if not problems else "; ".join(problems[:8]),
    )

    page_one = api.get("/medical/packages?page=1&page_size=1")
    page_two = api.get("/medical/packages?page=2&page_size=1")
    one_body = page_one.body if isinstance(page_one.body, dict) else {}
    two_body = page_two.body if isinstance(page_two.body, dict) else {}
    one_items = one_body.get("items") if isinstance(one_body.get("items"), list) else []
    two_items = two_body.get("items") if isinstance(two_body.get("items"), list) else []
    total = pkg_body.get("total")
    pagination_ok = (
        page_one.status == 200
        and page_two.status == 200
        and len(one_items) == 1
        and len(two_items) == 1
        and one_body.get("page") == 1
        and two_body.get("page") == 2
        and one_body.get("page_size") == 1
        and two_body.get("page_size") == 1
        and is_int(total)
        and total >= 2
        and one_items[0].get("id") != two_items[0].get("id")
    )
    checker.check(
        pagination_ok,
        "page/page_size 参数生效",
        f"page=1 首条 id={one_items[0].get('id') if one_items else None}，"
        f"page=2 首条 id={two_items[0].get('id') if two_items else None}，"
        f"total={total}",
    )

    # 5. /medical/hospitals
    checker.section(5, "/medical/hospitals 必须为裸数组")
    hospitals = api.get("/medical/hospitals")
    is_bare_list = isinstance(hospitals.body, list)
    checker.check(
        hospitals.status == 200 and is_bare_list,
        "返回裸数组（非 {items: ...}）",
        f"实际 {hospitals.status}，类型 {type(hospitals.body).__name__}",
    )
    if not is_bare_list:
        checker.note(
            "前端 _requestList 会把对象响应静默解析成空数组，后端必须返回数组。"
        )
    else:
        hospital_problems = []
        for index, item in enumerate(hospitals.body):
            if not isinstance(item, dict):
                hospital_problems.append(f"[{index}] 不是对象")
                continue
            if not is_int(item.get("id")):
                hospital_problems.append(f"[{index}].id 非 int")
            for field in ("name", "name_en", "level"):
                if not is_str(item.get(field)):
                    hospital_problems.append(f"[{index}].{field} 非 str")
        checker.check(
            bool(hospitals.body) and not hospital_problems,
            "医院元素字段类型正确",
            "全部通过" if not hospital_problems else "; ".join(hospital_problems[:8]),
        )

    # 6. /bookings/ 创建
    checker.section(6, "/bookings/ 创建订单")
    package_id = items[0].get("id") if items and isinstance(items[0], dict) else None
    booking_payload = {
        "package_id": package_id,
        "appointment_date": "2026-01-02T09:00:00.000",
        "contact_name": "API Verifier",
        "contact_phone": "+8613800000000",
        "contact_email": email,
        "notes": "automated verification",
        "need_translator": True,
        "need_accommodation": False,
        "need_pickup": True,
    }

    no_token_booking = api.post_json("/bookings/", booking_payload)
    checker.check(
        no_token_booking.status == 401,
        "无 token 返回 401",
        f"实际 {no_token_booking.status}",
    )

    created = api.post_json("/bookings/", booking_payload, token=token)
    created_body = created.body if isinstance(created.body, dict) else {}
    checker.check(
        created.status == 201,
        "带 token 创建返回 201",
        f"实际 {created.status} {fmt(created.body)}",
    )
    checker.check(
        is_int(created_body.get("id")), "订单 id 为 int"
    )
    checker.check(
        is_str(created_body.get("order_no"))
        and bool(created_body.get("order_no")),
        "order_no 为非空 str",
    )
    checker.check(
        is_number(created_body.get("total_price")), "total_price 为数字"
    )
    checker.check(is_str(created_body.get("currency")), "currency 为 str")
    checker.check(is_str(created_body.get("status")), "status 为 str")
    checker.check(
        is_int(created_body.get("package_id"))
        and created_body.get("package_id") == package_id,
        "package_id 与请求一致",
        f"实际 {fmt(created_body.get('package_id'))}",
    )
    checker.check(
        is_str(created_body.get("package_name"))
        and bool(created_body.get("package_name")),
        "package_name 为非空 str",
    )
    checker.check(
        is_str(created_body.get("package_name_en")),
        "package_name_en 为 str",
    )
    checker.check(
        is_iso_datetime(created_body.get("appointment_date")),
        "appointment_date 为 ISO 8601",
        fmt(created_body.get("appointment_date")),
    )
    checker.check(
        is_iso_datetime(created_body.get("created_at")),
        "created_at 为 ISO 8601",
        fmt(created_body.get("created_at")),
    )
    checker.note(
        "appointment_date 使用前端真实格式 2026-01-02T09:00:00.000，"
        f"服务端接受情况：{created.status}"
    )

    package_ids = [
        item.get("id")
        for item in items
        if isinstance(item, dict) and is_int(item.get("id"))
    ]
    unknown_payload = {
        **booking_payload,
        "package_id": (max(package_ids) + 100000) if package_ids else 999999999,
    }
    unknown = api.post_json("/bookings/", unknown_payload, token=token)
    checker.check(
        unknown.status == 404,
        "未知 package_id 返回 404",
        f"实际 {unknown.status} {fmt(unknown.body)}",
    )

    missing_payload = dict(booking_payload)
    missing_payload.pop("contact_name")
    missing = api.post_json("/bookings/", missing_payload, token=token)
    missing_detail = (
        missing.body.get("detail") if isinstance(missing.body, dict) else None
    )
    checker.check(
        missing.status == 422,
        "缺少必填字段返回 422",
        f"实际 {missing.status}",
    )
    checker.check(
        isinstance(missing_detail, list) and bool(missing_detail),
        "422 detail 为 FastAPI 默认错误数组",
        fmt(missing_detail),
    )

    # 7. /bookings/ 列表
    checker.section(7, "/bookings/ 列表")
    bookings = api.get("/bookings/", token=token)
    booking_list = bookings.body if isinstance(bookings.body, list) else []
    checker.check(
        bookings.status == 200 and isinstance(bookings.body, list),
        "返回裸数组",
        f"实际 {bookings.status}，类型 {type(bookings.body).__name__}",
    )
    created_item = next(
        (
            item
            for item in booking_list
            if isinstance(item, dict) and item.get("id") == created_body.get("id")
        ),
        None,
    )
    checker.check(
        created_item is not None,
        "列表中能看到刚创建的订单",
        f"订单 id={created_body.get('id')}",
    )
    if created_item is not None:
        checker.check(
            is_int(created_item.get("package_id"))
            and created_item.get("package_id") == package_id,
            "列表 package_id 与创建时一致",
            f"实际 {fmt(created_item.get('package_id'))}",
        )
        checker.check(
            is_str(created_item.get("package_name"))
            and bool(created_item.get("package_name")),
            "列表 package_name 为非空 str",
        )
        checker.check(
            is_str(created_item.get("package_name_en")),
            "列表 package_name_en 为 str",
        )
        checker.check(
            is_iso_datetime(created_item.get("appointment_date")),
            "列表 appointment_date 为 ISO 8601",
            fmt(created_item.get("appointment_date")),
        )
        checker.check(
            is_iso_datetime(created_item.get("created_at")),
            "列表 created_at 为 ISO 8601",
            fmt(created_item.get("created_at")),
        )

    # 8. CORS 预检
    checker.section(8, "CORS 预检")
    origin = "http://localhost:8123"
    preflight = request(
        "OPTIONS",
        api.url("/medical/packages"),
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
        timeout=args.timeout,
    )
    allow_origin = header(preflight.headers, "access-control-allow-origin") or ""
    allow_headers = (
        header(preflight.headers, "access-control-allow-headers") or ""
    ).lower()
    checker.check(
        preflight.status in (200, 204),
        "OPTIONS 预检返回 2xx",
        f"实际 {preflight.status}",
    )
    checker.check(
        allow_origin == origin or allow_origin == "*",
        f"允许来源 {origin}",
        f"access-control-allow-origin={allow_origin or '缺失'}",
    )
    checker.check(
        "authorization" in allow_headers and "content-type" in allow_headers,
        "允许 Authorization 与 Content-Type 头",
        f"access-control-allow-headers={allow_headers or '缺失'}",
    )

    # 9. 错误体形状
    checker.section(9, "错误体形状")
    for name, response in (
        ("401", no_token),
        ("404", unknown),
        ("422", missing),
    ):
        body = response.body
        checker.check(
            isinstance(body, dict) and "detail" in body,
            f"{name} 错误体包含 detail 键",
            fmt(body),
        )
    checker.check(
        isinstance(no_token.body.get("detail"), str),
        "401 detail 为字符串",
    )
    checker.check(
        isinstance(unknown.body.get("detail"), str),
        "404 detail 为字符串",
    )
    checker.check(
        isinstance(missing.body.get("detail"), list),
        "422 detail 为数组",
    )

    # 汇总
    print(f"\n汇总: 通过 {checker.passed} / 失败 {checker.failed}")
    print(f"测试账号: {email}")
    if args.cleanup:
        cleanup_local(email, DEFAULT_DB_PATH)
    else:
        print("未自动清理：本次测试账号与订单保留在数据库中。")
        print("本机可执行以下 SQL 清理（数据库为 backend/meditour.db）：")
        print(
            "  DELETE FROM bookings WHERE user_id IN "
            f"(SELECT id FROM users WHERE email='{email}');"
        )
        print(f"  DELETE FROM users WHERE email='{email}';")

    return 0 if checker.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
