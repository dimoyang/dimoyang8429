"""登录限流测试（进程内实现）。"""

import threading
from concurrent.futures import ThreadPoolExecutor

from app import rate_limit


def test_login_is_rate_limited_after_repeated_failures(client) -> None:
    rate_limit.reset_all()
    email = "rate-limit@meditour.com"
    try:
        for _ in range(rate_limit.MAX_FAILURES):
            response = client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": "WrongPassword123"},
            )
            assert response.status_code == 401

        blocked = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "WrongPassword123"},
        )
        assert blocked.status_code == 429
        assert isinstance(blocked.json()["detail"], str)
        assert int(blocked.headers["retry-after"]) > 0
    finally:
        rate_limit.reset_all()


def test_concurrent_failures_only_admit_threshold(client) -> None:
    """并发失败时也最多放行 MAX_FAILURES 次密码校验，其余直接 429。"""
    rate_limit.reset_all()
    email = "rate-limit-concurrent@meditour.com"
    attempts = rate_limit.MAX_FAILURES + 3
    barrier = threading.Barrier(attempts)

    def attempt() -> int:
        barrier.wait(timeout=10)
        return client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "WrongPassword123"},
        ).status_code

    try:
        with ThreadPoolExecutor(max_workers=attempts) as pool:
            statuses = list(pool.map(lambda _: attempt(), range(attempts)))
    finally:
        rate_limit.reset_all()

    assert statuses.count(401) == rate_limit.MAX_FAILURES, statuses
    assert statuses.count(429) == attempts - rate_limit.MAX_FAILURES, statuses
    assert set(statuses) <= {401, 429}


def test_successful_login_clears_failure_counter(client, auth_headers) -> None:
    rate_limit.reset_all()
    email = "pytest-user@meditour.com"
    password = "Pytest123456"
    try:
        assert (
            client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": "WrongPassword123"},
            ).status_code
            == 401
        )
        ok = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
        assert ok.status_code == 200
        assert rate_limit.retry_after("testclient", email) is None
    finally:
        rate_limit.reset_all()
