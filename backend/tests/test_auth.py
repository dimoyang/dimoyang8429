"""登录限流测试（进程内实现）。"""

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
