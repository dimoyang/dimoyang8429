#!/usr/bin/env python3
"""轻量并发探测：只看状态码分布与错误率，不做性能基准。

仅用标准库（urllib + threading），对关键路径各打一轮并发：

1. 登录限流：同一邮箱连续错误密码，观察 401 → 429 的切换；
2. 预约创建：同一用户、同一套餐、同一预约时间并发下单，正常情况下
   应只有一个 201，其余 409（由部分唯一索引 uq_bookings_pending_slot 兜底）；
3. 取消订单：并发取消同一个 pending 订单，应只有一个 200，其余 409；
4. 订单列表：并发读取，观察连接/锁竞争下的 5xx；
5. 刷新令牌：同一个 refresh token 并发刷新，应只有一个 200，其余 401；
6. 图片上传（需要员工账号）：并发上传同一张图片，观察是否出现 5xx；
7. 员工改价（需要员工账号）：并发修改同一套餐价格，观察最终值是否可预期。

用法（先启动 API）：
    python scripts/concurrency_probe.py --threads 12
    python scripts/concurrency_probe.py --threads 12 --staff-email staff@example.com \
        --staff-password Staff123456

脚本会注册一个临时用户并在结束时注销；失败也会尽量清理。
员工账号不会被脚本修改或删除，改价场景结束后会把价格恢复原值。
"""

import argparse
import base64
import json
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"
# 必须大于服务端连接池等待时间（默认 10s），否则客户端先超时会掩盖真实的 500。
DEFAULT_TIMEOUT = 45.0
# 由 --timeout 覆盖；http_call 的默认参数在运行时读取它。
HTTP_TIMEOUT = DEFAULT_TIMEOUT


# 1x1 透明 PNG；上传接口只校验文件头，但用真实图片更接近实际请求。
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8"
    "BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def http_call(
    method: str,
    url: str,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    form: dict[str, str] | None = None,
    raw: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, bytes, float]:
    """返回 (status, body, 毫秒)。网络异常用 status=0 表示。"""
    timeout = HTTP_TIMEOUT if timeout is None else timeout
    body = None
    final_headers = dict(headers or {})
    if raw is not None:
        body = raw
        if content_type:
            final_headers["Content-Type"] = content_type
    elif form is not None:
        body = urllib.parse.urlencode(form).encode()
        final_headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif payload is not None:
        body = json.dumps(payload).encode()
        final_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url, data=body, headers=final_headers, method=method
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
            return response.status, data, (time.perf_counter() - started) * 1000
    except urllib.error.HTTPError as exc:
        data = exc.read()
        return exc.code, data, (time.perf_counter() - started) * 1000
    except Exception as exc:  # 连接被拒、超时等
        return 0, str(exc).encode(), (time.perf_counter() - started) * 1000


def multipart_png() -> tuple[bytes, str]:
    """构造一个只含 file 字段的 multipart 请求体。"""
    boundary = f"----meditourProbe{secrets.token_hex(8)}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; '
            b'filename="probe.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            PNG_BYTES,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def run_concurrent(count: int, worker) -> list:
    """所有线程在同一 barrier 后同时发起请求。"""
    results: list = [None] * count
    barrier = threading.Barrier(count)
    errors: list[BaseException] = []

    def runner(index: int) -> None:
        try:
            barrier.wait()
            results[index] = worker(index)
        except BaseException as exc:  # noqa: BLE001 - 线程内异常要带回主线程
            errors.append(exc)

    threads = [
        threading.Thread(target=runner, args=(index,)) for index in range(count)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    if errors:
        raise errors[0]
    return results


def summarize(name: str, results: list[tuple[int, bytes, float]]) -> None:
    statuses = Counter(status for status, _, _ in results)
    latencies = sorted(ms for _, _, ms in results)
    failures = statuses.get(0, 0) + sum(
        count for status, count in statuses.items() if status >= 500
    )
    total = len(results)
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
    distribution = ", ".join(
        f"{status if status else 'network'}: {count}"
        for status, count in sorted(statuses.items())
    )
    print(
        f"[{name}] requests={total} | {distribution} | "
        f"errors(5xx/network)={failures} ({failures / total:.0%}) | "
        f"p50={p50:.0f}ms p95={p95:.0f}ms max={latencies[-1]:.0f}ms"
    )


def _json_body(result: tuple[int, bytes, float]) -> dict:
    if result[0] != 200 and result[0] != 201:
        return {}
    try:
        return json.loads(result[1])
    except json.JSONDecodeError:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="并发探测关键路径")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--threads", type=int, default=12, help="每个场景的并发线程数"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=(
            "单请求超时秒数（默认 45）。必须大于服务端连接池等待时间，"
            "否则客户端先超时会掩盖真实的 500。"
        ),
    )
    parser.add_argument(
        "--password", default="ProbePass123456", help="临时用户密码"
    )
    parser.add_argument(
        "--staff-email", default=None, help="员工账号邮箱（启用上传/改价场景）"
    )
    parser.add_argument("--staff-password", default=None, help="员工账号密码")
    args = parser.parse_args()

    global HTTP_TIMEOUT
    HTTP_TIMEOUT = args.timeout

    base = args.base_url.rstrip("/")
    count = max(2, args.threads)

    status, _, _ = http_call("GET", f"{base}/health")
    if status != 200:
        print(f"服务不可用：{base}/health 返回 {status}", file=sys.stderr)
        return 2

    suffix = secrets.token_hex(4)
    email = f"probe-{suffix}@probe.meditour.com"
    password = args.password

    print(f"base_url={base} threads={count} user={email}")
    print("-" * 78)

    # 场景 1：登录限流（不存在的邮箱 + 错误密码，全部预期 401/429）。
    rate_email = f"rate-limit-{suffix}@probe.meditour.com"
    rate_results = run_concurrent(
        count,
        lambda _index: http_call(
            "POST",
            f"{base}/auth/login",
            form={"username": rate_email, "password": "definitely-wrong"},
        ),
    )
    summarize("login-rate-limit", rate_results)

    # 准备一个真实用户与一个在售套餐。
    register = http_call(
        "POST",
        f"{base}/auth/register",
        {"email": email, "password": password, "full_name": "Probe User"},
    )
    if register[0] != 201:
        print(f"注册探测用户失败：{register[0]} {register[1][:200]!r}", file=sys.stderr)
        return 2

    login = http_call(
        "POST",
        f"{base}/auth/login",
        form={"username": email, "password": password},
    )
    if login[0] != 200:
        print(f"登录探测用户失败：{login[0]} {login[1][:200]!r}", file=sys.stderr)
        return 2
    token = _json_body(login)["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    packages = http_call("GET", f"{base}/medical/packages?page=1&page_size=1")
    if packages[0] != 200 or not _json_body(packages)["items"]:
        print("没有可预约的套餐，无法验证下单并发", file=sys.stderr)
        return 2
    package_id = _json_body(packages)["items"][0]["id"]

    def appointment_iso(days: int) -> str:
        return (
            datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
        ).replace(hour=9, minute=0, second=0, microsecond=0).isoformat(
            timespec="seconds"
        )

    booking_payload = {
        "package_id": package_id,
        "appointment_date": appointment_iso(120),
        "contact_name": "Probe User",
        "contact_phone": "+8613800000000",
        "contact_email": email,
        "notes": "concurrency probe",
    }

    # 场景 2：同一用户/套餐/预约时间并发下单，正常应只有 1 个 201。
    booking_results = run_concurrent(
        count,
        lambda _index: http_call(
            "POST", f"{base}/bookings/", booking_payload, auth
        ),
    )
    summarize("booking-create", booking_results)

    # 场景 3：并发取消同一个 pending 订单，正常应只有 1 个 200。
    cancel_payload = dict(booking_payload, appointment_date=appointment_iso(121))
    created = http_call("POST", f"{base}/bookings/", cancel_payload, auth)
    if created[0] != 201:
        print(
            f"创建待取消订单失败：{created[0]} {created[1][:200]!r}",
            file=sys.stderr,
        )
        return 2
    booking_id = _json_body(created)["id"]
    cancel_results = run_concurrent(
        count,
        lambda _index: http_call(
            "POST", f"{base}/bookings/{booking_id}/cancel", None, auth
        ),
    )
    summarize("booking-cancel", cancel_results)

    # 场景 4：并发读取订单列表。
    list_results = run_concurrent(
        count,
        lambda _index: http_call("GET", f"{base}/bookings/", None, auth),
    )
    summarize("bookings-list", list_results)

    # 场景 5：同一个 refresh token 并发刷新，正常应只有 1 个 200，其余 401。
    relogin = http_call(
        "POST",
        f"{base}/auth/login",
        form={"username": email, "password": password},
    )
    refresh_token = _json_body(relogin)["refresh_token"]
    refresh_results = run_concurrent(
        count,
        lambda _index: http_call(
            "POST", f"{base}/auth/refresh", {"refresh_token": refresh_token}
        ),
    )
    summarize("refresh-token", refresh_results)

    # 场景 6/7：员工侧上传与改价（需要显式提供员工账号）。
    staff_auth = None
    if args.staff_email and args.staff_password:
        staff_login = http_call(
            "POST",
            f"{base}/auth/login",
            form={
                "username": args.staff_email,
                "password": args.staff_password,
            },
        )
        if staff_login[0] == 200:
            staff_auth = {
                "Authorization": f"Bearer {_json_body(staff_login)['access_token']}"
            }
        else:
            print(
                f"[staff] 登录失败：{staff_login[0]} {staff_login[1][:200]!r}",
                file=sys.stderr,
            )

    if staff_auth is None:
        print(
            "[upload] skipped：需要 --staff-email/--staff-password 才能访问员工接口"
        )
        print("[staff-price-update] skipped：同上")
    else:
        def upload_once(_index: int) -> tuple[int, bytes, float]:
            body, content_type = multipart_png()
            return http_call(
                "POST",
                f"{base}/staff/uploads",
                headers=staff_auth,
                raw=body,
                content_type=content_type,
            )

        upload_results = run_concurrent(count, upload_once)
        summarize("upload", upload_results)
        saved = [
            _json_body(result)["path"]
            for result in upload_results
            if result[0] == 201
        ]
        print(
            f"  upload success={len(saved)} unique_paths={len(set(saved))}"
        )

        detail = http_call(
            "GET", f"{base}/staff/packages/{package_id}", None, staff_auth
        )
        if detail[0] != 200:
            print(
                f"[staff-price-update] 读取套餐失败：{detail[0]}",
                file=sys.stderr,
            )
        else:
            original_price = _json_body(detail)["price"]
            prices = [round(original_price + index + 1, 2) for index in range(count)]
            price_results = run_concurrent(
                count,
                lambda index: http_call(
                    "PATCH",
                    f"{base}/staff/packages/{package_id}",
                    {"price": prices[index]},
                    staff_auth,
                ),
            )
            summarize("staff-price-update", price_results)
            final_result = http_call(
                "GET",
                f"{base}/staff/packages/{package_id}",
                None,
                staff_auth,
            )
            final_body = _json_body(final_result)
            if "price" in final_body:
                print(
                    f"  original={original_price} final={final_body['price']} "
                    f"in_submitted={final_body['price'] in prices}"
                )
            else:
                print(
                    "  final GET failed: "
                    f"status={final_result[0]} body={final_result[1][:120]!r}"
                )
            restored = http_call(
                "PATCH",
                f"{base}/staff/packages/{package_id}",
                {"price": original_price},
                staff_auth,
            )
            print(f"  restore original price -> {restored[0]}")

    # 清理：注销临时用户（其 pending 订单会被取消并匿名化）。
    cleanup = http_call(
        "DELETE", f"{base}/auth/account", {"password": password}, auth
    )
    print("-" * 78)
    print(f"cleanup: DELETE /auth/account -> {cleanup[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
