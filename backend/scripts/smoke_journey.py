"""MediTour 全链路冒烟脚本（仅使用 Python 标准库）。

按真实用户旅程串行执行：

注册 → 从 outbox 读取验证邮件 → 确认邮箱 → 登录 → 浏览套餐/医院 →
创建预约 → 查看订单 → 取消预约 → 导出数据 → 修改密码 → 新密码登录 →
注销账号 → 确认登录被拒。

每一步都校验状态码与关键字段；失败时明确指出断在第几步。适用于上线验收与
CI，退出码 0 表示全部通过、1 表示业务断言失败、2 表示无法连接后端。

前置（在 i:\\meditour_app\\backend 下）：
    $env:MEDITOUR_SECRET_KEY="<本地密钥>"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

运行：
    python backend/scripts/smoke_journey.py
    python backend/scripts/smoke_journey.py --base-url http://127.0.0.1:8000/api/v1
    python backend/scripts/smoke_journey.py --mail-outbox backend/var/mail_outbox.log

脚本需要后端使用 file 邮件后端（开发默认）才能读取验证令牌；smtp 后端会在
“读取验证邮件”一步明确失败，不会伪造通过。账号会在最后一步注销。
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_MAIL_OUTBOX = (
    Path(__file__).resolve().parent.parent / "var" / "mail_outbox.log"
)


class SmokeFailure(RuntimeError):
    """业务断言失败：带上足够的信息定位断点。"""


class ConnectionFailure(RuntimeError):
    """无法连接后端（端口未监听、DNS 失败、超时等）。"""


class Response:
    def __init__(self, status: int, headers: dict[str, str], body: object):
        self.status = status
        self.headers = headers
        self.body = body


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
            return Response(
                resp.status, dict(resp.headers), _decode_body(resp.read())
            )
    except urllib.error.HTTPError as exc:
        return Response(exc.code, dict(exc.headers), _decode_body(exc.read()))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise ConnectionFailure(str(reason)) from exc


class Api:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get(self, path: str, token: str | None = None) -> Response:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return request(
            "GET", self._url(path), headers=headers, timeout=self.timeout
        )

    def post_json(
        self, path: str, payload: dict, token: str | None = None
    ) -> Response:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return request(
            "POST",
            self._url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            timeout=self.timeout,
        )

    def post_form(self, path: str, form: dict) -> Response:
        return request(
            "POST",
            self._url(path),
            data=urllib.parse.urlencode(form).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )

    def delete_json(
        self, path: str, payload: dict, token: str
    ) -> Response:
        return request(
            "DELETE",
            self._url(path),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=self.timeout,
        )


def require(condition: bool, message: str, detail: object = None) -> None:
    if not condition:
        suffix = "" if detail is None else f"（实际：{detail}）"
        raise SmokeFailure(message + suffix)


def _outbox_line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def read_verification_token(
    path: Path, offset: int, email: str
) -> str:
    if not path.exists():
        raise SmokeFailure(
            f"outbox 文件不存在：{path}"
            "（后端需使用 file 邮件后端，或用 --mail-outbox 指定正确路径）"
        )
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[offset:]:
        if f"to={email}" not in line or "kind=email_verification" not in line:
            continue
        match = re.search(r"\btoken=(\S+)", line)
        if match:
            return match.group(1)
    raise SmokeFailure(f"outbox 中没有找到 {email} 的验证邮件（检查邮件后端配置）")


def step_register(ctx: dict) -> None:
    api: Api = ctx["api"]
    response = api.post_json(
        "/auth/register",
        {
            "email": ctx["email"],
            "password": ctx["password"],
            "full_name": "Smoke Journey",
            "preferred_language": "en",
        },
    )
    require(response.status == 201, "注册应返回 201", response.status)
    body = response.body
    require(isinstance(body, dict), "注册响应应为对象", body)
    require(body.get("email") == ctx["email"], "注册响应邮箱不一致", body)
    require(body.get("email_verified") is False, "新账号应为未验证", body)
    require(body.get("role") == "user", "新账号角色应为 user", body)


def step_read_verification_mail(ctx: dict) -> None:
    ctx["verification_token"] = read_verification_token(
        ctx["outbox"], ctx["outbox_offset"], ctx["email"]
    )


def step_confirm_email(ctx: dict) -> None:
    response = ctx["api"].post_json(
        "/auth/email-verification/confirm",
        {"token": ctx["verification_token"]},
    )
    require(response.status == 200, "确认邮箱应返回 200", response.status)


def step_login(ctx: dict) -> None:
    response = ctx["api"].post_form(
        "/auth/login",
        {"username": ctx["email"], "password": ctx["password"]},
    )
    require(response.status == 200, "登录应返回 200", response.status)
    body = response.body
    require(isinstance(body, dict), "登录响应应为对象", body)
    require(
        isinstance(body.get("access_token"), str),
        "登录响应缺少 access_token",
        body,
    )
    require(
        isinstance(body.get("refresh_token"), str),
        "登录响应缺少 refresh_token",
        body,
    )
    require(body.get("email_verified") is True, "确认后应为已验证", body)
    ctx["access_token"] = body["access_token"]


def step_me(ctx: dict) -> None:
    response = ctx["api"].get("/auth/me", token=ctx["access_token"])
    require(response.status == 200, "读取个人资料应返回 200", response.status)
    body = response.body
    require(body.get("email") == ctx["email"], "个人资料邮箱不一致", body)
    require(body.get("email_verified") is True, "个人资料应显示已验证", body)


def step_browse_packages(ctx: dict) -> None:
    response = ctx["api"].get("/medical/packages?page=1&page_size=5")
    require(response.status == 200, "套餐列表应返回 200", response.status)
    body = response.body
    require(isinstance(body, dict), "套餐列表响应应为对象", body)
    items = body.get("items")
    require(isinstance(items, list) and bool(items), "套餐列表不应为空", body)
    require(isinstance(body.get("total"), int), "套餐列表缺少 total", body)
    ctx["package_id"] = items[0]["id"]


def step_browse_hospitals(ctx: dict) -> None:
    response = ctx["api"].get("/medical/hospitals")
    require(response.status == 200, "医院列表应返回 200", response.status)
    body = response.body
    require(
        isinstance(body, list) and bool(body), "医院列表不应为空", body
    )


def step_create_booking(ctx: dict) -> None:
    appointment = (
        datetime.now(timezone.utc) + timedelta(days=30)
    ).replace(microsecond=0).isoformat()
    response = ctx["api"].post_json(
        "/bookings/",
        {
            "package_id": ctx["package_id"],
            "appointment_date": appointment,
            "contact_name": "Smoke Journey",
            "contact_phone": "+8613800000000",
            "contact_email": ctx["email"],
            "notes": "created by smoke_journey.py",
        },
        token=ctx["access_token"],
    )
    require(response.status == 201, "创建预约应返回 201", response.status)
    body = response.body
    require(isinstance(body.get("id"), int), "预约响应缺少 id", body)
    require(body.get("status") == "pending", "新预约状态应为 pending", body)
    require(
        isinstance(body.get("total_price"), (int, float))
        and not isinstance(body.get("total_price"), bool),
        "预约响应缺少服务端金额",
        body,
    )
    ctx["booking_id"] = body["id"]


def step_list_bookings(ctx: dict) -> None:
    response = ctx["api"].get("/bookings/", token=ctx["access_token"])
    require(response.status == 200, "订单列表应返回 200", response.status)
    body = response.body
    require(isinstance(body, list), "订单列表应为裸数组", body)
    target = next(
        (item for item in body if item.get("id") == ctx["booking_id"]), None
    )
    require(target is not None, "订单列表中找不到刚创建的预约", body)
    require(target.get("status") == "pending", "订单状态应为 pending", target)


def step_cancel_booking(ctx: dict) -> None:
    response = ctx["api"].post_json(
        f"/bookings/{ctx['booking_id']}/cancel",
        {},
        token=ctx["access_token"],
    )
    require(response.status == 200, "取消预约应返回 200", response.status)
    require(
        response.body.get("status") == "cancelled",
        "取消后状态应为 cancelled",
        response.body,
    )


def step_export(ctx: dict) -> None:
    response = ctx["api"].get("/auth/export", token=ctx["access_token"])
    require(response.status == 200, "导出数据应返回 200", response.status)
    body = response.body
    require(isinstance(body, dict), "导出响应应为对象", body)
    require(
        body.get("account", {}).get("email") == ctx["email"],
        "导出账号不是当前用户",
        body.get("account"),
    )
    booking_ids = [item.get("id") for item in body.get("bookings", [])]
    require(
        ctx["booking_id"] in booking_ids,
        "导出数据应包含当前预约",
        booking_ids,
    )
    require(
        isinstance(body.get("itineraries"), list),
        "导出数据缺少 itineraries",
        body,
    )


def step_change_password(ctx: dict) -> None:
    response = ctx["api"].post_json(
        "/auth/change-password",
        {
            "current_password": ctx["password"],
            "new_password": ctx["new_password"],
        },
        token=ctx["access_token"],
    )
    require(response.status == 200, "修改密码应返回 200", response.status)


def step_login_with_new_password(ctx: dict) -> None:
    old = ctx["api"].post_form(
        "/auth/login",
        {"username": ctx["email"], "password": ctx["password"]},
    )
    require(old.status == 401, "旧密码登录应被拒绝", old.status)

    response = ctx["api"].post_form(
        "/auth/login",
        {"username": ctx["email"], "password": ctx["new_password"]},
    )
    require(response.status == 200, "新密码登录应返回 200", response.status)
    ctx["access_token"] = response.body["access_token"]


def step_delete_account(ctx: dict) -> None:
    response = ctx["api"].delete_json(
        "/auth/account",
        {"password": ctx["new_password"]},
        token=ctx["access_token"],
    )
    require(response.status == 200, "注销账号应返回 200", response.status)


def step_login_rejected(ctx: dict) -> None:
    response = ctx["api"].post_form(
        "/auth/login",
        {"username": ctx["email"], "password": ctx["new_password"]},
    )
    require(response.status == 401, "注销后登录应返回 401", response.status)


STEPS = [
    ("注册新账号", step_register),
    ("从 outbox 读取验证邮件", step_read_verification_mail),
    ("确认邮箱", step_confirm_email),
    ("登录", step_login),
    ("读取个人资料", step_me),
    ("浏览套餐", step_browse_packages),
    ("浏览医院", step_browse_hospitals),
    ("创建预约", step_create_booking),
    ("查看我的订单", step_list_bookings),
    ("取消预约", step_cancel_booking),
    ("导出数据", step_export),
    ("修改密码", step_change_password),
    ("用新密码登录", step_login_with_new_password),
    ("注销账号", step_delete_account),
    ("确认注销后登录被拒", step_login_rejected),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MediTour 全链路冒烟：注册到注销的完整用户旅程"
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="API 根地址（含 /api/v1）"
    )
    parser.add_argument(
        "--mail-outbox",
        default=str(DEFAULT_MAIL_OUTBOX),
        help="file 邮件后端的 outbox 索引文件",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outbox = Path(args.mail_outbox)
    suffix = secrets.token_hex(3)
    ctx: dict = {
        "api": Api(args.base_url, args.timeout),
        "email": f"smoke-{int(time.time())}-{suffix}@meditour.com",
        "password": "SmokePass123",
        "new_password": "SmokePass456",
        "outbox": outbox,
        "outbox_offset": _outbox_line_count(outbox),
    }

    print(f"目标：{args.base_url}")
    print(f"测试账号：{ctx['email']}")

    passed = 0
    started = time.perf_counter()
    try:
        for index, (name, func) in enumerate(STEPS, start=1):
            step_started = time.perf_counter()
            print(f"[{index:02d}/{len(STEPS)}] {name} ... ", end="", flush=True)
            try:
                func(ctx)
            except SmokeFailure as exc:
                elapsed = time.perf_counter() - step_started
                print(f"FAIL ({elapsed:.2f}s)")
                print(
                    f"\n失败于第 {index} 步「{name}」：{exc}\n"
                    f"账号：{ctx['email']}，后端：{args.base_url}"
                )
                return 1
            elapsed = time.perf_counter() - step_started
            print(f"PASS ({elapsed:.2f}s)")
            passed += 1
    except ConnectionFailure as exc:
        print("\nFAIL")
        print(f"\n无法连接后端 {args.base_url}：{exc}")
        return 2

    total = time.perf_counter() - started
    print(f"\n通过 {passed}/{len(STEPS)}，耗时 {total:.2f}s")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已中断")
        sys.exit(130)
