"""认证接口限流：注册按 IP、找回密码按邮箱 + IP、验证邮件重发冷却。

测试把阈值调小，验证“该拦的拦住、不该误伤的放过”；生产默认值见 README
「认证接口限流」与 `app/config.py`。conftest 已把运行默认值调高，
因此这里用 monkeypatch 只影响单个用例。
"""

import pytest

from app import rate_limit
from app.config import settings

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
RESET = "/api/v1/auth/password-reset/request"
VERIFY_REQUEST = "/api/v1/auth/email-verification/request"
PASSWORD = "RateLimit123456"


@pytest.fixture(autouse=True)
def clean_limiter():
    rate_limit.reset_all()
    yield
    rate_limit.reset_all()


def _register(client, email: str):
    return client.post(
        REGISTER,
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Rate Limit",
            "preferred_language": "en",
        },
    )


def _login(client, email: str) -> dict[str, str]:
    response = client.post(
        LOGIN, data={"username": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _mail_lines(mail_outbox, kind: str) -> list[str]:
    return [
        line
        for line in mail_outbox.read_text(encoding="utf-8").splitlines()
        if f"kind={kind}" in line
    ]


def _reset_mail_count(mail_outbox) -> int:
    """找回密码的 outbox 行没有 kind 字段，用主题识别。"""
    return len(
        [
            line
            for line in mail_outbox.read_text(encoding="utf-8").splitlines()
            if "subject=Reset your MediTour password" in line
        ]
    )


def test_register_is_limited_per_ip(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "REGISTER_LIMIT_PER_IP", 2)
    monkeypatch.setattr(settings, "REGISTER_LIMIT_WINDOW_SECONDS", 3600)

    assert _register(client, "rl-register-a@meditour.com").status_code == 201
    assert _register(client, "rl-register-b@meditour.com").status_code == 201

    blocked = _register(client, "rl-register-c@meditour.com")
    assert blocked.status_code == 429
    assert isinstance(blocked.json()["detail"], str)
    assert int(blocked.headers["retry-after"]) > 0

    # 限流在写库之前：被拒的邮箱没有创建账号。
    login = client.post(
        LOGIN,
        data={"username": "rl-register-c@meditour.com", "password": PASSWORD},
    )
    assert login.status_code == 401


def test_default_register_quota_does_not_block_a_small_team(client) -> None:
    """默认 30 次/小时，同一出口 IP 的 5 个同事可以各自注册。"""
    for index in range(5):
        response = _register(client, f"rl-team-{index}@meditour.com")
        assert response.status_code == 201, response.text


def test_reset_email_limit_only_affects_that_mailbox(
    client, mail_outbox, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "RESET_LIMIT_PER_EMAIL", 1)
    monkeypatch.setattr(settings, "RESET_LIMIT_PER_IP", 100)
    monkeypatch.setattr(settings, "RESET_LIMIT_WINDOW_SECONDS", 3600)

    first = "rl-reset-a@meditour.com"
    second = "rl-reset-b@meditour.com"
    assert _register(client, first).status_code == 201
    assert _register(client, second).status_code == 201

    before = _reset_mail_count(mail_outbox)
    assert client.post(RESET, json={"email": first}).status_code == 200
    assert _reset_mail_count(mail_outbox) == before + 1

    # 同一邮箱再次请求：响应仍是同样的 200，但不发信、不换令牌。
    limited = client.post(RESET, json={"email": first})
    assert limited.status_code == 200
    assert _reset_mail_count(mail_outbox) == before + 1

    # 另一个邮箱不受影响：粒度是“邮箱”，不是“IP”。
    assert client.post(RESET, json={"email": second}).status_code == 200
    assert _reset_mail_count(mail_outbox) == before + 2

    # 未注册邮箱不占用额度，也不发信。
    unknown = "rl-reset-unknown@meditour.com"
    for _ in range(3):
        assert client.post(RESET, json={"email": unknown}).status_code == 200
    assert _reset_mail_count(mail_outbox) == before + 2


def test_reset_ip_limit_blocks_all_emails(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "RESET_LIMIT_PER_EMAIL", 100)
    monkeypatch.setattr(settings, "RESET_LIMIT_PER_IP", 1)
    monkeypatch.setattr(settings, "RESET_LIMIT_WINDOW_SECONDS", 3600)

    assert (
        client.post(
            RESET, json={"email": "rl-reset-ip-a@meditour.com"}
        ).status_code
        == 200
    )
    blocked = client.post(
        RESET, json={"email": "rl-reset-ip-b@meditour.com"}
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_verification_resend_has_cooldown(
    client, mail_outbox, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "VERIFICATION_RESEND_COOLDOWN_SECONDS", 60)
    email = "rl-verify-cooldown@meditour.com"
    assert _register(client, email).status_code == 201
    headers = _login(client, email)

    before = len(_mail_lines(mail_outbox, "email_verification"))
    first = client.post(VERIFY_REQUEST, headers=headers)
    assert first.status_code == 200
    assert len(_mail_lines(mail_outbox, "email_verification")) == before + 1

    second = client.post(VERIFY_REQUEST, headers=headers)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(_mail_lines(mail_outbox, "email_verification")) == before + 1

    # 冷却关闭后可以再次发信（用于验证“冷却”而不是“永久禁发”）。
    monkeypatch.setattr(settings, "VERIFICATION_RESEND_COOLDOWN_SECONDS", 0)
    third = client.post(VERIFY_REQUEST, headers=headers)
    assert third.status_code == 200
    assert len(_mail_lines(mail_outbox, "email_verification")) == before + 2
