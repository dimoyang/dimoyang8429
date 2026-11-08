"""会话管理：列表元信息、单设备吊销、退出所有设备。"""

SESSIONS = "/api/v1/auth/sessions"


def register_and_login(
    client, email: str, agent: str = "device-a"
) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SessionPass123"},
    )
    return login(client, email, agent)


def login(client, email: str, agent: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "SessionPass123"},
        headers={"User-Agent": agent},
    )
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def list_sessions(client, token: str) -> list[dict]:
    response = client.get(SESSIONS, headers=bearer(token))
    assert response.status_code == 200, response.text
    return response.json()


def test_lists_sessions_without_returning_tokens(client) -> None:
    first = register_and_login(client, "session-list@meditour.com", "device-a")
    second = login(client, "session-list@meditour.com", "device-b")

    sessions = list_sessions(client, second["access_token"])
    assert len(sessions) == 2
    for item in sessions:
        assert set(item) == {
            "id",
            "created_at",
            "last_used_at",
            "user_agent",
            "ip",
            "current",
        }
    assert {item["user_agent"] for item in sessions} == {
        "device-a",
        "device-b",
    }
    assert sum(1 for item in sessions if item["current"]) == 1
    # 不返回任何令牌或令牌摘要。
    joined = str(sessions)
    assert first["access_token"] not in joined
    assert first["refresh_token"] not in joined
    assert "jti" not in joined


def test_revoke_single_session_invalidates_only_that_device(client) -> None:
    email = "session-revoke-one@meditour.com"
    first = register_and_login(client, email, "device-a")
    second = login(client, email, "device-b")

    target = next(
        item
        for item in list_sessions(client, second["access_token"])
        if item["user_agent"] == "device-a"
    )
    revoked = client.delete(
        f"{SESSIONS}/{target['id']}", headers=bearer(second["access_token"])
    )
    assert revoked.status_code == 200, revoked.text

    # 被吊销设备的 access / refresh 立即失效，另一台设备不受影响。
    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(first["access_token"])
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first["refresh_token"]},
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(second["access_token"])
        ).status_code
        == 200
    )
    assert len(list_sessions(client, second["access_token"])) == 1

    # 重复吊销同一会话：已不再有效，返回 404。
    again = client.delete(
        f"{SESSIONS}/{target['id']}", headers=bearer(second["access_token"])
    )
    assert again.status_code == 404


def test_cannot_revoke_another_users_session(client) -> None:
    attacker = register_and_login(
        client, "session-attacker@meditour.com", "attacker"
    )
    victim = register_and_login(client, "session-victim@meditour.com", "victim")
    victim_sessions = list_sessions(client, victim["access_token"])
    assert len(victim_sessions) == 1

    response = client.delete(
        f"{SESSIONS}/{victim_sessions[0]['id']}",
        headers=bearer(attacker["access_token"]),
    )
    assert response.status_code == 404
    # 受害者的会话仍然可用。
    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(victim["access_token"])
        ).status_code
        == 200
    )


def test_refresh_keeps_same_session(client) -> None:
    tokens = register_and_login(client, "session-refresh@meditour.com")
    before = list_sessions(client, tokens["access_token"])
    assert len(before) == 1

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    after = list_sessions(client, refreshed.json()["access_token"])
    assert len(after) == 1
    assert after[0]["id"] == before[0]["id"]


def test_logout_revokes_only_current_session(client) -> None:
    email = "session-logout@meditour.com"
    first = register_and_login(client, email, "device-a")
    second = login(client, email, "device-b")

    logged_out = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": second["refresh_token"]},
        headers=bearer(second["access_token"]),
    )
    assert logged_out.status_code == 200

    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(second["access_token"])
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/auth/me", headers=bearer(first["access_token"])
        ).status_code
        == 200
    )


def test_revoke_all_invalidates_every_token(client) -> None:
    email = "session-revoke-all@meditour.com"
    first = register_and_login(client, email, "device-a")
    second = login(client, email, "device-b")

    response = client.post(
        f"{SESSIONS}/revoke-all", headers=bearer(first["access_token"])
    )
    assert response.status_code == 200, response.text
    assert response.json()["revoked"] == 2

    for tokens in (first, second):
        assert (
            client.get(
                "/api/v1/auth/me", headers=bearer(tokens["access_token"])
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": tokens["refresh_token"]},
            ).status_code
            == 401
        )
