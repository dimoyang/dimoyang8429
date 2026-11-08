#!/usr/bin/env python3
"""MediTour 后端接口验证脚本（仅使用 Python 标准库）。

逐条验证前端依赖的 /api/v1 契约：注册、登录、鉴权、套餐、医院、预约、
CORS 预检、错误体形状、账号闭环（找回/修改密码、注销）、多语言、数据导出
与员工订单操作。

前置：先启动后端（在 i:\\meditour_app\\backend 下）
    $env:MEDITOUR_SECRET_KEY="<本地密钥>"
    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

运行示例（系统 Python 即可，无需安装任何依赖）：
    python backend/scripts/verify_api.py
    python backend/scripts/verify_api.py --base-url http://10.0.2.2:8000/api/v1
    python backend/scripts/verify_api.py --mail-outbox backend/var/mail_outbox.log
    python backend/scripts/verify_api.py --cleanup
    python backend/scripts/verify_api.py --staff-email staff@example.com --staff-password Staff123456

账号闭环验证需要后端使用开发环境 file 邮件后端（默认），脚本从 outbox
文件读取重置令牌；使用 smtp 后端时该部分会明确失败而不会伪造通过。
员工接口验证需要先用 scripts/manage_staff.py 授予一个真实账号 staff 角色，
并通过 --staff-email/--staff-password 传入；未提供时会跳过并打印提示。
每次运行都会注册带时间戳和随机后缀的独立账号，不会改动演示账号。
--cleanup 仅作用于本机默认的 backend/meditour.db；远程目标请手动清理。
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "meditour.db"
DEFAULT_MAIL_OUTBOX = (
    Path(__file__).resolve().parent.parent / "var" / "mail_outbox.log"
)


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
        print(f"\n[{index}/14] {title}")


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

    def delete_json(
        self, path: str, payload: object, token: str | None = None
    ) -> Response:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return request(
            "DELETE",
            self.url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            timeout=self.timeout,
        )

    def patch_json(
        self, path: str, payload: object, token: str | None = None
    ) -> Response:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return request(
            "PATCH",
            self.url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
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


def outbox_line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def read_new_reset_tokens(path: Path, offset: int) -> list[str]:
    """读取 outbox 中新增行里的重置令牌（开发环境 file 邮件后端）。"""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[offset:]
    tokens: list[str] = []
    for line in lines:
        match = re.search(r"\btoken=(\S+)", line)
        if match:
            tokens.append(match.group(1))
    return tokens


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
    parser.add_argument(
        "--mail-outbox",
        default=str(DEFAULT_MAIL_OUTBOX),
        help="开发环境 file 邮件后端的 outbox 路径，默认 backend/var/mail_outbox.log",
    )
    parser.add_argument(
        "--staff-email",
        help="已由 manage_staff.py 授予 staff 的账号邮箱；提供后验证员工订单接口",
    )
    parser.add_argument(
        "--staff-password",
        help="员工账号密码，需与 --staff-email 同时提供",
    )
    args = parser.parse_args()

    mail_outbox = Path(args.mail_outbox)

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

    limited_email = f"verify-rate-{suffix}@meditour.com"
    statuses = [
        api.post_form(
            "/auth/login",
            {"username": limited_email, "password": "WrongPassword123"},
        ).status
        for _ in range(6)
    ]
    checker.check(
        statuses[:5] == [401] * 5 and statuses[5] == 429,
        "连续失败 5 次后登录被限流",
        f"实际状态序列 {statuses}",
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

    health = api.get("/health")
    health_body = health.body if isinstance(health.body, dict) else {}
    checker.check(
        health.status == 200
        and health_body.get("status") == "ok"
        and health_body.get("database") == "ok",
        "健康检查返回 status/database 均为 ok",
        f"实际 {health.status} {fmt(health.body)}",
    )
    checker.check(
        bool(header(health.headers, "X-Request-ID")),
        "响应包含 X-Request-ID",
        f"值 {header(health.headers, 'X-Request-ID')}",
    )
    traced = api.get(
        "/health", headers={"X-Request-ID": "verify-trace-123"}
    )
    checker.check(
        header(traced.headers, "X-Request-ID") == "verify-trace-123",
        "上游传入的 X-Request-ID 被透传",
        f"值 {header(traced.headers, 'X-Request-ID')}",
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
    checker.check(
        api.get("/medical/packages?page=0").status == 422,
        "page < 1 返回 422",
    )
    checker.check(
        api.get("/medical/packages?page_size=101").status == 422,
        "page_size > 100 返回 422",
    )
    beyond = api.get("/medical/packages?page=99&page_size=100")
    beyond_body = beyond.body if isinstance(beyond.body, dict) else {}
    checker.check(
        beyond.status == 200
        and beyond_body.get("items") == []
        and is_int(beyond_body.get("total"))
        and beyond_body.get("total") >= 1,
        "超出末页 items 为空但 total 保留",
        f"实际 {beyond.status} {fmt(beyond.body, 120)}",
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
    appointment_date = (
        datetime.now() + timedelta(days=60)
    ).replace(hour=9, minute=0, second=0, microsecond=0)
    booking_payload = {
        "package_id": package_id,
        "appointment_date": appointment_date.isoformat(),
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
        "appointment_date 使用运行时计算的未来时间发送，"
        f"服务端接受情况：{created.status}"
    )

    duplicate = api.post_json("/bookings/", booking_payload, token=token)
    checker.check(
        duplicate.status == 409
        and isinstance(duplicate.body, dict)
        and isinstance(duplicate.body.get("detail"), str),
        "同用户同套餐同时间重复提交返回 409",
        f"实际 {duplicate.status} {fmt(duplicate.body)}",
    )

    past_payload = {
        **booking_payload,
        "appointment_date": (
            datetime.now() - timedelta(days=1)
        ).isoformat(),
    }
    checker.check(
        api.post_json("/bookings/", past_payload, token=token).status == 422,
        "过去的 appointment_date 返回 422",
    )

    long_notes = api.post_json(
        "/bookings/", {**booking_payload, "notes": "x" * 2001}, token=token
    )
    checker.check(
        long_notes.status == 422,
        "超长 notes 返回 422",
        f"实际 {long_notes.status}",
    )

    bad_phone = api.post_json(
        "/bookings/",
        {**booking_payload, "contact_phone": "not-a-phone"},
        token=token,
    )
    checker.check(
        bad_phone.status == 422,
        "无效手机号返回 422",
        f"实际 {bad_phone.status}",
    )

    bad_email = api.post_json(
        "/bookings/",
        {**booking_payload, "contact_email": "not-an-email"},
        token=token,
    )
    checker.check(
        bad_email.status == 422,
        "无效联系邮箱返回 422",
        f"实际 {bad_email.status}",
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

    cancel = api.post_json(
        f"/bookings/{created_body.get('id')}/cancel", {}, token=token
    )
    cancel_body = cancel.body if isinstance(cancel.body, dict) else {}
    checker.check(
        cancel.status == 200 and cancel_body.get("status") == "cancelled",
        "取消自己的 pending 订单返回 cancelled",
        f"实际 {cancel.status} status={cancel_body.get('status')}",
    )
    checker.check(
        all(field in cancel_body for field in ("id", "order_no", "package_id", "total_price", "currency")),
        "取消响应保留既有字段",
    )

    cancel_again = api.post_json(
        f"/bookings/{created_body.get('id')}/cancel", {}, token=token
    )
    checker.check(
        cancel_again.status == 409
        and isinstance(cancel_again.body, dict)
        and isinstance(cancel_again.body.get("detail"), str),
        "重复取消返回 409 且 detail 为字符串",
        f"实际 {cancel_again.status} {fmt(cancel_again.body)}",
    )

    # 8. 令牌刷新与登出
    checker.section(8, "令牌刷新与登出")
    login_refresh = (
        login.body.get("refresh_token") if isinstance(login.body, dict) else None
    )
    checker.check(
        is_str(login_refresh) and bool(login_refresh),
        "登录响应包含 refresh_token",
        f"长度 {len(login_refresh) if isinstance(login_refresh, str) else 'N/A'}",
    )

    refreshed = api.post_json(
        "/auth/refresh", {"refresh_token": login_refresh}
    )
    refreshed_body = refreshed.body if isinstance(refreshed.body, dict) else {}
    new_access = refreshed_body.get("access_token")
    new_refresh = refreshed_body.get("refresh_token")
    checker.check(
        refreshed.status == 200
        and is_str(new_access)
        and is_str(new_refresh)
        and new_access != new_refresh,
        "refresh 返回新的 access/refresh 令牌",
        f"实际 {refreshed.status}",
    )

    reuse = api.post_json(
        "/auth/refresh", {"refresh_token": login_refresh}
    )
    checker.check(
        reuse.status == 401
        and isinstance(reuse.body, dict)
        and isinstance(reuse.body.get("detail"), str),
        "旧 refresh token 重复使用返回 401",
        f"实际 {reuse.status} {fmt(reuse.body)}",
    )

    checker.check(
        api.get("/auth/me", token=new_access).status == 200,
        "新 access token 可用",
    )

    logout = api.post_json(
        "/auth/logout",
        {"refresh_token": new_refresh},
        token=new_access,
    )
    checker.check(
        logout.status == 200
        and isinstance(logout.body, dict)
        and isinstance(logout.body.get("detail"), str),
        "登出返回 200 且 detail 为字符串",
        f"实际 {logout.status} {fmt(logout.body)}",
    )
    after_logout = api.get("/auth/me", token=new_access)
    checker.check(
        after_logout.status == 401
        and isinstance(after_logout.body, dict)
        and isinstance(after_logout.body.get("detail"), str),
        "登出后的 access token 被拒绝",
        f"实际 {after_logout.status} {fmt(after_logout.body)}",
    )
    refresh_after_logout = api.post_json(
        "/auth/refresh", {"refresh_token": new_refresh}
    )
    checker.check(
        refresh_after_logout.status == 401,
        "登出后的 refresh token 被拒绝",
        f"实际 {refresh_after_logout.status}",
    )

    # 登出会吊销整个设备会话：同一会话里更早签发的 access token 也一起失效。
    # 后续段落需要有效令牌，这里重新登录拿到一个全新会话。
    relogin = api.post_form(
        "/auth/login", {"username": email, "password": password}
    )
    relogin_body = relogin.body if isinstance(relogin.body, dict) else {}
    token = relogin_body.get("access_token")
    checker.check(
        relogin.status == 200 and is_str(token),
        "登出后可重新登录（后续段落使用新会话）",
        f"实际 {relogin.status}",
    )

    # 9. CORS 预检
    checker.section(9, "CORS 预检")
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

    # 10. 错误体形状
    checker.section(10, "错误体形状")
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

    # 11. 账号闭环
    checker.section(11, "账号闭环（找回/修改密码、注销）")
    reset_email = f"verify-reset-{suffix}@meditour.com"
    reset_password = "ResetStart123"
    reset_new_password = "ResetFinal123"
    api.post_json(
        "/auth/register",
        {
            "email": reset_email,
            "password": reset_password,
            "full_name": "Reset Verifier",
        },
    )

    outbox_offset = outbox_line_count(mail_outbox)
    reset_request = api.post_json(
        "/auth/password-reset/request", {"email": reset_email}
    )
    unknown_reset_request = api.post_json(
        "/auth/password-reset/request",
        {"email": f"verify-nobody-{suffix}@meditour.com"},
    )
    checker.check(
        reset_request.status == 200,
        "已注册邮箱请求重置返回 200",
        f"实际 {reset_request.status} {fmt(reset_request.body)}",
    )
    checker.check(
        unknown_reset_request.status == 200
        and unknown_reset_request.body == reset_request.body,
        "未注册邮箱返回完全相同的响应（防账号枚举）",
        f"实际 {unknown_reset_request.status} {fmt(unknown_reset_request.body)}",
    )

    reset_tokens = read_new_reset_tokens(mail_outbox, outbox_offset)
    checker.check(
        bool(reset_tokens),
        "开发环境 file 邮件后端写入了重置令牌",
        f"outbox={mail_outbox}，新增令牌 {len(reset_tokens)} 个",
    )
    if not reset_tokens:
        checker.note(
            "未读到令牌：确认后端使用 MEDITOUR_MAIL_BACKEND=file，"
            "且 --mail-outbox 指向真实文件；smtp 后端无法自动验证此段。"
        )

    if reset_tokens:
        reset_token = reset_tokens[-1]
        confirmed = api.post_json(
            "/auth/password-reset/confirm",
            {"token": reset_token, "new_password": reset_new_password},
        )
        checker.check(
            confirmed.status == 200,
            "用一次性令牌设置新密码返回 200",
            f"实际 {confirmed.status} {fmt(confirmed.body)}",
        )
        checker.check(
            api.post_form(
                "/auth/login",
                {"username": reset_email, "password": reset_password},
            ).status
            == 401,
            "重置后旧密码无法登录",
        )
        reset_login = api.post_form(
            "/auth/login",
            {"username": reset_email, "password": reset_new_password},
        )
        reset_tokens_body = (
            reset_login.body if isinstance(reset_login.body, dict) else {}
        )
        reset_access = reset_tokens_body.get("access_token")
        reset_refresh = reset_tokens_body.get("refresh_token")
        checker.check(
            reset_login.status == 200 and is_str(reset_access),
            "重置后新密码可以登录",
            f"实际 {reset_login.status}",
        )

        reused_reset = api.post_json(
            "/auth/password-reset/confirm",
            {"token": reset_token, "new_password": "AnotherPass123"},
        )
        checker.check(
            reused_reset.status == 400,
            "重置令牌重复使用返回 400",
            f"实际 {reused_reset.status} {fmt(reused_reset.body)}",
        )

        wrong_current = api.post_json(
            "/auth/change-password",
            {
                "current_password": "WrongCurrent123",
                "new_password": "ChangedAgain123",
            },
            token=reset_access,
        )
        checker.check(
            wrong_current.status == 400,
            "修改密码时当前密码错误返回 400",
            f"实际 {wrong_current.status} {fmt(wrong_current.body)}",
        )

        changed = api.post_json(
            "/auth/change-password",
            {
                "current_password": reset_new_password,
                "new_password": "ChangedAgain123",
            },
            token=reset_access,
        )
        checker.check(
            changed.status == 200,
            "当前密码正确时修改成功",
            f"实际 {changed.status} {fmt(changed.body)}",
        )
        checker.check(
            api.get("/auth/me", token=reset_access).status == 401,
            "改密后旧 access token 立即失效",
        )
        checker.check(
            api.post_json(
                "/auth/refresh", {"refresh_token": reset_refresh}
            ).status
            == 401,
            "改密后旧 refresh token 立即失效",
        )

        final_login = api.post_form(
            "/auth/login",
            {"username": reset_email, "password": "ChangedAgain123"},
        )
        final_body = final_login.body if isinstance(final_login.body, dict) else {}
        final_access = final_body.get("access_token")
        checker.check(
            final_login.status == 200 and is_str(final_access),
            "改密后可用新密码重新登录",
            f"实际 {final_login.status}",
        )

        wrong_delete = api.delete_json(
            "/auth/account",
            {"password": "WrongDelete123"},
            token=final_access,
        )
        checker.check(
            wrong_delete.status == 400,
            "注销账号时密码错误返回 400",
            f"实际 {wrong_delete.status} {fmt(wrong_delete.body)}",
        )

        deleted = api.delete_json(
            "/auth/account",
            {"password": "ChangedAgain123"},
            token=final_access,
        )
        checker.check(
            deleted.status == 200,
            "密码正确时注销账号返回 200",
            f"实际 {deleted.status} {fmt(deleted.body)}",
        )
        checker.check(
            api.get("/auth/me", token=final_access).status == 401,
            "注销后原 access token 失效",
        )
        checker.check(
            api.post_form(
                "/auth/login",
                {"username": reset_email, "password": "ChangedAgain123"},
            ).status
            == 401,
            "注销后无法再登录",
        )

    # 12. 多语言
    checker.section(12, "医疗内容多语言（lang 参数与回退）")
    baseline_packages = api.get("/medical/packages?page=1&page_size=100")
    baseline_body = (
        baseline_packages.body if isinstance(baseline_packages.body, dict) else {}
    )
    baseline_items = (
        baseline_body.get("items")
        if isinstance(baseline_body.get("items"), list)
        else []
    )

    def find_by_name_en(rows: list, name_en: str) -> dict | None:
        for row in rows:
            if isinstance(row, dict) and row.get("name_en") == name_en:
                return row
        return None

    knee_baseline = find_by_name_en(baseline_items, "Knee Replacement Surgery")
    checker.check(
        knee_baseline is not None
        and knee_baseline.get("name") == "膝关节置换手术",
        "不传 lang 时 name 仍为中文（向后兼容）",
        fmt(knee_baseline and knee_baseline.get("name")),
    )

    zh_packages = api.get("/medical/packages?page=1&page_size=100&lang=zh")
    en_packages = api.get("/medical/packages?page=1&page_size=100&lang=en")
    de_packages = api.get("/medical/packages?page=1&page_size=100&lang=de")
    zh_body = zh_packages.body if isinstance(zh_packages.body, dict) else {}
    en_body = en_packages.body if isinstance(en_packages.body, dict) else {}
    de_body = de_packages.body if isinstance(de_packages.body, dict) else {}
    zh_knee = find_by_name_en(zh_body.get("items", []), "Knee Replacement Surgery")
    en_knee = find_by_name_en(en_body.get("items", []), "Knee Replacement Surgery")
    de_knee = find_by_name_en(de_body.get("items", []), "Knee Replacement Surgery")
    de_implants = find_by_name_en(de_body.get("items", []), "Dental Implants")

    checker.check(
        zh_packages.status == 200
        and zh_knee is not None
        and zh_knee.get("name") == "膝关节置换手术",
        "lang=zh 返回中文内容",
        fmt(zh_knee and zh_knee.get("name")),
    )
    checker.check(
        en_packages.status == 200
        and en_knee is not None
        and en_knee.get("name") == "Knee Replacement Surgery",
        "lang=en 使用英文 name",
        fmt(en_knee and en_knee.get("name")),
    )
    checker.check(
        de_packages.status == 200
        and de_knee is not None
        and de_knee.get("name") == "Kniegelenkersatz (Knie-TEP)",
        "lang=de 命中德语译文",
        fmt(de_knee and de_knee.get("name")),
    )
    checker.check(
        de_implants is not None
        and de_implants.get("name") == "Dental Implants",
        "无德语译文的套餐回退到英文（de → en → zh）",
        fmt(de_implants and de_implants.get("name")),
    )

    de_hospitals = api.get("/medical/hospitals?lang=de")
    de_hospital_list = (
        de_hospitals.body if isinstance(de_hospitals.body, list) else []
    )
    de_union = find_by_name_en(
        de_hospital_list, "Peking Union Medical College Hospital"
    )
    checker.check(
        de_hospitals.status == 200
        and de_union is not None
        and de_union.get("name") == "Peking-Union-Krankenhaus",
        "医院列表支持 lang=de",
        fmt(de_union and de_union.get("name")),
    )
    checker.check(
        api.get("/medical/packages?lang=it").status == 422,
        "不支持的语言返回 422",
    )

    # 目的地多语言：不传 lang 与旧响应一致，数组字段类型不变，id 仍是 slug。
    baseline_destinations = api.get("/destinations")
    de_destinations = api.get("/destinations?lang=de")
    baseline_rows = (
        baseline_destinations.body
        if isinstance(baseline_destinations.body, list)
        else []
    )
    de_rows = (
        de_destinations.body if isinstance(de_destinations.body, list) else []
    )
    baseline_ids = [
        row.get("id") for row in baseline_rows if isinstance(row, dict)
    ]
    de_ids = [row.get("id") for row in de_rows if isinstance(row, dict)]
    de_beijing = next(
        (row for row in de_rows if isinstance(row, dict) and row.get("id") == "beijing"),
        None,
    )
    checker.check(
        de_destinations.status == 200 and de_ids == baseline_ids,
        "目的地列表支持 lang 且条目与顺序不变",
        f"{len(baseline_ids)} -> {len(de_ids)}",
    )
    checker.check(
        de_beijing is not None
        and isinstance(de_beijing.get("search_terms"), list)
        and isinstance(de_beijing.get("experiences"), list)
        and isinstance(de_beijing.get("tips"), list),
        "目的地多语言响应保持数组字段类型",
    )
    destination_detail = api.get("/destinations/beijing?lang=fr")
    checker.check(
        destination_detail.status == 200
        and isinstance(destination_detail.body, dict)
        and destination_detail.body.get("id") == "beijing",
        "目的地详情支持 lang 且 id 仍为 slug",
        fmt(destination_detail.body.get("id") if isinstance(destination_detail.body, dict) else None),
    )
    checker.check(
        api.get("/destinations?lang=it").status == 422,
        "目的地不支持的语言返回 422",
    )

    # 13. 数据导出
    checker.section(13, "用户数据导出（仅本人）")
    export = api.get("/auth/export", token=token)
    export_body = export.body if isinstance(export.body, dict) else {}
    checker.check(
        export.status == 200,
        "GET /auth/export 返回 200",
        f"实际 {export.status} {fmt(export.body)}",
    )
    checker.check(
        "attachment" in (header(export.headers, "Content-Disposition") or ""),
        "响应带 attachment 下载头",
        f"Content-Disposition={header(export.headers, 'Content-Disposition')}",
    )
    checker.check(
        isinstance(export_body.get("account"), dict)
        and export_body["account"].get("email") == email,
        "导出账号信息属于当前用户",
        fmt(export_body.get("account")),
    )
    export_bookings = (
        export_body.get("bookings")
        if isinstance(export_body.get("bookings"), list)
        else []
    )
    checker.check(
        any(
            isinstance(item, dict)
            and item.get("order_no") == created_body.get("order_no")
            for item in export_bookings
        ),
        "导出包含本人订单",
        f"订单数 {len(export_bookings)}",
    )
    checker.check(
        isinstance(export_body.get("itineraries"), list)
        and export_body.get("favorites") == [],
        "导出包含 itineraries 与 favorites 字段",
        fmt(
            {
                "itineraries": export_body.get("itineraries"),
                "favorites": export_body.get("favorites"),
            }
        ),
    )

    other_email = f"verify-export-{suffix}@meditour.com"
    api.post_json(
        "/auth/register",
        {"email": other_email, "password": "OtherExport123"},
    )
    other_login = api.post_form(
        "/auth/login", {"username": other_email, "password": "OtherExport123"}
    )
    other_access = (
        other_login.body.get("access_token")
        if isinstance(other_login.body, dict)
        else None
    )
    other_export = api.get("/auth/export", token=other_access)
    other_body = other_export.body if isinstance(other_export.body, dict) else {}
    checker.check(
        other_export.status == 200
        and other_body.get("account", {}).get("email") == other_email,
        "另一个账号只能导出自己的账号信息",
        fmt(other_body.get("account")),
    )
    checker.check(
        other_body.get("bookings") == [] and other_body.get("itineraries") == [],
        "另一个账号导出中不包含他人订单/行程",
        fmt(
            {
                "bookings": other_body.get("bookings"),
                "itineraries": other_body.get("itineraries"),
            }
        ),
    )
    checker.check(
        api.get("/auth/export").status == 401,
        "未登录访问导出接口返回 401",
    )

    # 14. 员工订单操作
    checker.section(14, "员工订单操作与角色边界")
    if not (args.staff_email and args.staff_password):
        checker.note(
            "未提供 --staff-email / --staff-password，跳过员工接口验证。"
        )
        checker.note(
            "创建员工账号：python backend/scripts/manage_staff.py "
            "--email staff@example.com --password Staff123456"
        )
    else:
        staff_login = api.post_form(
            "/auth/login",
            {"username": args.staff_email, "password": args.staff_password},
        )
        staff_login_body = (
            staff_login.body if isinstance(staff_login.body, dict) else {}
        )
        staff_token = staff_login_body.get("access_token")
        checker.check(
            staff_login.status == 200 and staff_login_body.get("role") == "staff",
            "员工账号登录成功且 role=staff",
            f"实际 {staff_login.status} role={staff_login_body.get('role')}",
        )

        checker.check(
            api.get("/staff/bookings", token=token).status == 403,
            "普通用户访问员工订单列表返回 403",
        )

        staff_payload = {
            **booking_payload,
            "appointment_date": (
                datetime.now() + timedelta(days=70)
            )
            .replace(hour=10, minute=0, second=0, microsecond=0)
            .isoformat(),
            "contact_phone": "+8613900001234",
            "notes": "staff verification note",
        }
        staff_created = api.post_json(
            "/bookings/", staff_payload, token=token
        )
        staff_booking = (
            staff_created.body if isinstance(staff_created.body, dict) else {}
        )
        checker.check(
            staff_created.status == 201 and is_int(staff_booking.get("id")),
            "创建员工验证用订单",
            f"实际 {staff_created.status} {fmt(staff_created.body)}",
        )

        staff_list = api.get(
            "/staff/bookings?page=1&page_size=100&status=pending",
            token=staff_token,
        )
        staff_list_body = (
            staff_list.body if isinstance(staff_list.body, dict) else {}
        )
        staff_items = (
            staff_list_body.get("items")
            if isinstance(staff_list_body.get("items"), list)
            else []
        )
        staff_item = next(
            (
                item
                for item in staff_items
                if isinstance(item, dict)
                and item.get("id") == staff_booking.get("id")
            ),
            None,
        )
        checker.check(
            staff_list.status == 200
            and is_int(staff_list_body.get("total"))
            and is_int(staff_list_body.get("page_size")),
            "员工订单列表返回分页结构",
            f"实际 {staff_list.status} {fmt(staff_list.body, 200)}",
        )
        checker.check(
            api.get(
                "/staff/bookings?page_size=101", token=staff_token
            ).status
            == 422,
            "员工列表 page_size 上限为 100",
        )
        checker.check(
            staff_item is not None,
            "员工能看到任意用户的订单",
            f"订单 id={staff_booking.get('id')}",
        )
        if staff_item is not None:
            checker.check(
                "notes" not in staff_item,
                "员工列表不返回备注",
            )
            checker.check(
                staff_item.get("contact_phone") != "+8613900001234"
                and "*" in str(staff_item.get("contact_phone")),
                "员工列表手机号已打码",
                fmt(staff_item.get("contact_phone")),
            )
            checker.check(
                staff_item.get("contact_email") != email
                and str(staff_item.get("contact_email")).endswith(
                    "@meditour.com"
                ),
                "员工列表邮箱已打码",
                fmt(staff_item.get("contact_email")),
            )

        staff_detail = api.get(
            f"/staff/bookings/{staff_booking.get('id')}", token=staff_token
        )
        staff_detail_body = (
            staff_detail.body if isinstance(staff_detail.body, dict) else {}
        )
        checker.check(
            staff_detail.status == 200
            and staff_detail_body.get("contact_phone") == "+8613900001234"
            and staff_detail_body.get("notes") == "staff verification note",
            "员工详情返回完整联系方式与备注",
            f"实际 {staff_detail.status}",
        )

        checker.check(
            api.patch_json(
                f"/staff/bookings/{staff_booking.get('id')}/status",
                {"status": "confirmed"},
                token=token,
            ).status
            == 403,
            "普通用户不能修改订单状态",
        )

        skip_transition = api.patch_json(
            f"/staff/bookings/{staff_booking.get('id')}/status",
            {"status": "completed"},
            token=staff_token,
        )
        checker.check(
            skip_transition.status == 409,
            "跳过 confirmed 直接 completed 返回 409",
            f"实际 {skip_transition.status} {fmt(skip_transition.body)}",
        )

        confirmed = api.patch_json(
            f"/staff/bookings/{staff_booking.get('id')}/status",
            {"status": "confirmed"},
            token=staff_token,
        )
        confirmed_body = (
            confirmed.body if isinstance(confirmed.body, dict) else {}
        )
        checker.check(
            confirmed.status == 200 and confirmed_body.get("status") == "confirmed",
            "员工可将 pending 流转为 confirmed",
            f"实际 {confirmed.status} status={confirmed_body.get('status')}",
        )

        completed = api.patch_json(
            f"/staff/bookings/{staff_booking.get('id')}/status",
            {"status": "completed"},
            token=staff_token,
        )
        completed_body = (
            completed.body if isinstance(completed.body, dict) else {}
        )
        checker.check(
            completed.status == 200
            and completed_body.get("status") == "completed",
            "员工可将 confirmed 流转为 completed",
            f"实际 {completed.status} status={completed_body.get('status')}",
        )

        checker.check(
            api.patch_json(
                f"/staff/bookings/{staff_booking.get('id')}/status",
                {"status": "confirmed"},
                token=staff_token,
            ).status
            == 409,
            "completed 订单不能再次流转",
        )
        checker.check(
            api.patch_json(
                "/staff/bookings/99999999/status",
                {"status": "confirmed"},
                token=staff_token,
            ).status
            == 404,
            "员工操作不存在的订单返回 404",
        )
        checker.check(
            api.patch_json(
                f"/staff/bookings/{staff_booking.get('id')}/status",
                # cancelled 现在是合法目标值；用 pending 验证“不是可写入的目标”。
                {"status": "pending"},
                token=staff_token,
            ).status
            == 422,
            "员工提交非法目标状态返回 422",
        )
        checker.check(
            api.get("/staff/bookings").status == 401,
            "未登录访问员工接口返回 401",
        )

        stats = api.get(
            "/staff/stats/overview?date_from=2026-11-01&date_to=2026-11-08",
            token=staff_token,
        )
        stats_body = stats.body if isinstance(stats.body, dict) else {}
        checker.check(
            stats.status == 200
            and is_int(stats_body.get("total_bookings"))
            and isinstance(stats_body.get("status_counts"), list)
            and isinstance(stats_body.get("revenue"), list)
            and isinstance(stats_body.get("trend"), list),
            "员工概览返回总数、状态分布、成交金额与趋势",
            f"实际 {stats.status} {fmt(stats.body, 200)}",
        )
        checker.check(
            len(stats_body.get("trend", [])) == 8,
            "员工概览趋势覆盖完整日期范围",
            f"实际 {len(stats_body.get('trend', []))} 天",
        )
        checker.check(
            api.get("/staff/stats/overview", token=token).status == 403,
            "普通用户访问员工统计返回 403",
        )
        checker.check(
            api.get("/staff/stats/overview").status == 401,
            "未登录访问员工统计返回 401",
        )
        checker.check(
            api.get(
                "/staff/stats/overview"
                "?date_from=2026-11-08&date_to=2026-11-01",
                token=staff_token,
            ).status
            == 422,
            "员工统计日期范围颠倒返回 422",
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
