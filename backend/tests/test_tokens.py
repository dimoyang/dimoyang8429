"""令牌闭环测试：刷新、轮换、登出吊销与向后兼容。"""

from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def register_and_login(client, email: str = "token-user@meditour.com") -> dict:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TokenPass123"},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "TokenPass123"},
    )
    assert response.status_code == 200
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_access_and_refresh_tokens(client) -> None:
    tokens = register_and_login(client)
    assert isinstance(tokens["access_token"], str) and tokens["access_token"]
    assert isinstance(tokens["refresh_token"], str) and tokens["refresh_token"]
    assert tokens["access_token"] != tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


def test_refresh_rotates_and_rejects_reuse(client) -> None:
    tokens = register_and_login(client, "token-refresh@meditour.com")

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    assert (
        client.get("/api/v1/auth/me", headers=bearer(new_tokens["access_token"])).status_code
        == 200
    )

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reused.status_code == 401
    assert isinstance(reused.json()["detail"], str)


def test_logout_revokes_access_and_refresh(client) -> None:
    tokens = register_and_login(client, "token-logout@meditour.com")
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    logged_out = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh},
        headers=bearer(access),
    )
    assert logged_out.status_code == 200
    assert isinstance(logged_out.json()["detail"], str)

    rejected = client.get("/api/v1/auth/me", headers=bearer(access))
    assert rejected.status_code == 401
    assert isinstance(rejected.json()["detail"], str)

    refresh_after_logout = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh}
    )
    assert refresh_after_logout.status_code == 401


def test_token_types_are_not_interchangeable(client) -> None:
    tokens = register_and_login(client, "token-types@meditour.com")

    as_access = client.get(
        "/api/v1/auth/me", headers=bearer(tokens["refresh_token"])
    )
    assert as_access.status_code == 401

    as_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert as_refresh.status_code == 401


def test_legacy_access_token_without_type_or_jti_still_works(client) -> None:
    tokens = register_and_login(client, "token-legacy@meditour.com")
    user_id = client.get(
        "/api/v1/auth/me", headers=bearer(tokens["access_token"])
    ).json()["id"]

    now = datetime.now(timezone.utc)
    legacy = jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert client.get("/api/v1/auth/me", headers=bearer(legacy)).status_code == 200
