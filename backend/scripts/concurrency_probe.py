#!/usr/bin/env python3
"""轻量并发探测：只看状态码分布与错误率，不做性能基准。

仅用标准库（urllib + threading），对三条关键路径各打一轮并发：

1. 登录限流：同一邮箱连续错误密码，观察 401 → 429 的切换；
2. 预约创建：同一用户、同一套餐、同一预约时间并发下单，
   验证是否只产生一个 pending（SQLite 下也可能暴露 database is locked）；
3. 订单列表：并发读取，观察连接/锁竞争下的 5xx。

用法（先启动 API）：
    python scripts/concurrency_probe.py --threads 12

脚本会注册一个临时用户并在结束时注销；失败也会尽量清理。
"""

import argparse
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


def http_call(
    method: str,
    url: str,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    form: dict[str, str] | None = None,
) -> tuple[int, bytes, float]:
    """返回 (status, body, 毫秒)。网络异常用 status=0 表示。"""
    body = None
    final_headers = dict(headers or {})
    if form is not None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="并发探测关键路径")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--threads", type=int, default=12, help="每个场景的并发线程数"
    )
    parser.add_argument(
        "--password", default="ProbePass123456", help="临时用户密码"
    )
    args = parser.parse_args()

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
    token = json.loads(login[1])["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    packages = http_call("GET", f"{base}/medical/packages?page=1&page_size=1")
    if packages[0] != 200 or not json.loads(packages[1])["items"]:
        print("没有可预约的套餐，无法验证下单并发", file=sys.stderr)
        return 2
    package_id = json.loads(packages[1])["items"][0]["id"]

    appointment = (
        datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=120)
    ).replace(hour=9, minute=0, second=0, microsecond=0)
    booking_payload = {
        "package_id": package_id,
        "appointment_date": appointment.isoformat(timespec="seconds"),
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

    # 场景 3：并发读取订单列表。
    list_results = run_concurrent(
        count,
        lambda _index: http_call("GET", f"{base}/bookings/", None, auth),
    )
    summarize("bookings-list", list_results)

    # 清理：注销临时用户（其 pending 订单会被取消并匿名化）。
    cleanup = http_call(
        "DELETE", f"{base}/auth/account", {"password": password}, auth
    )
    print("-" * 78)
    print(f"cleanup: DELETE /auth/account -> {cleanup[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
