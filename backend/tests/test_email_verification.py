"""邮箱验证：注册发信、可重发、一次性令牌与不阻断登录。"""

import re
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser

from app.config import settings

VERIFY_REQUEST = "/api/v1/auth/email-verification/request"
VERIFY_CONFIRM = "/api/v1/auth/email-verification/confirm"


def register(client, email: str, language: str = "en"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "VerifyPass123",
            "preferred_language": language,
        },
    )


def latest_verification_token(mail_outbox) -> str:
    lines = [
        line
        for line in mail_outbox.read_text(encoding="utf-8").splitlines()
        if "kind=email_verification" in line
    ]
    assert lines, "outbox 中应有验证邮件索引行"
    return re.search(r"\btoken=(\S+)", lines[-1]).group(1)


def login(client, email: str, agent: str = "verify-agent"):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "VerifyPass123"},
        headers={"User-Agent": agent},
    )
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_sends_multilingual_verification_email(
    client, mail_outbox, mail_preview_dir
) -> None:
    email = "verify-zh@meditour.com"
    before = {path.name for path in mail_preview_dir.glob("*.eml")}

    response = register(client, email, "zh-CN")
    assert response.status_code == 201, response.text
    assert response.json()["email_verified"] is False

    new_files = [
        path
        for path in mail_preview_dir.glob("*.eml")
        if path.name not in before
    ]
    assert len(new_files) == 1

    message = BytesParser(policy=policy.default).parsebytes(
        new_files[0].read_bytes()
    )
    assert message["Subject"] == "验证你的 MediTour 邮箱"
    text_body = message.get_body(preferencelist=("plain",)).get_content()
    html_body = message.get_body(preferencelist=("html",)).get_content()
    assert "/verify-email?token=" in text_body
    assert "/verify-email?token=" in html_body

    # outbox 只保留 token 索引，不写完整链接或收件人以外的敏感信息。
    last_line = mail_outbox.read_text(encoding="utf-8").splitlines()[-1]
    assert "kind=email_verification" in last_line
    assert "verify-email" not in last_line
    assert latest_verification_token(mail_outbox) in text_body


def test_unverified_user_can_still_login(client) -> None:
    email = "verify-login@meditour.com"
    assert register(client, email).status_code == 201

    tokens = login(client, email)
    assert tokens["email_verified"] is False

    me = client.get("/api/v1/auth/me", headers=bearer(tokens["access_token"]))
    assert me.status_code == 200
    assert me.json()["email_verified"] is False


def test_verification_token_is_single_use(client, mail_outbox) -> None:
    email = "verify-single@meditour.com"
    assert register(client, email).status_code == 201
    token = latest_verification_token(mail_outbox)

    confirmed = client.post(VERIFY_CONFIRM, json={"token": token})
    assert confirmed.status_code == 200, confirmed.text

    me = client.get(
        "/api/v1/auth/me", headers=bearer(login(client, email)["access_token"])
    )
    assert me.json()["email_verified"] is True

    reused = client.post(VERIFY_CONFIRM, json={"token": token})
    assert reused.status_code == 400
    assert isinstance(reused.json()["detail"], str)

    unknown = client.post(VERIFY_CONFIRM, json={"token": "not-a-real-token"})
    assert unknown.status_code == 400


def test_resend_invalidates_previous_token(client, mail_outbox) -> None:
    email = "verify-resend@meditour.com"
    assert register(client, email).status_code == 201
    old_token = latest_verification_token(mail_outbox)
    headers = bearer(login(client, email)["access_token"])

    resent = client.post(VERIFY_REQUEST, headers=headers)
    assert resent.status_code == 200
    new_token = latest_verification_token(mail_outbox)
    assert new_token != old_token

    # 旧令牌被作废，新令牌可用。
    assert client.post(VERIFY_CONFIRM, json={"token": old_token}).status_code == 400
    assert (
        client.post(VERIFY_CONFIRM, json={"token": new_token}).status_code == 200
    )

    # 已验证后重发：响应完全一致，且不再写新邮件。
    lines_before = mail_outbox.read_text(encoding="utf-8").splitlines()
    verified_resend = client.post(VERIFY_REQUEST, headers=headers)
    assert verified_resend.status_code == 200
    assert verified_resend.json() == resent.json()
    assert mail_outbox.read_text(encoding="utf-8").splitlines() == lines_before


def test_booking_requires_verified_email_when_switch_enabled(
    client, mail_outbox, monkeypatch
) -> None:
    email = "verify-booking-gate@meditour.com"
    assert register(client, email).status_code == 201
    tokens = login(client, email)

    package = client.get("/api/v1/medical/packages?page=1&page_size=1").json()
    package_id = package["items"][0]["id"]
    payload = {
        "package_id": package_id,
        "appointment_date": (
            datetime.now(timezone.utc) + timedelta(days=30)
        )
        .replace(microsecond=0)
        .isoformat(),
        "contact_name": "Gate User",
        "contact_phone": "+8613800000000",
        "contact_email": email,
    }

    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)
    denied = client.post(
        "/api/v1/bookings/", json=payload, headers=bearer(tokens["access_token"])
    )
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Email verification required"}

    token = latest_verification_token(mail_outbox)
    assert client.post(VERIFY_CONFIRM, json={"token": token}).status_code == 200

    allowed = client.post(
        "/api/v1/bookings/", json=payload, headers=bearer(tokens["access_token"])
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["status"] == "pending"


def test_expired_verification_token_is_rejected(
    client, mail_outbox, monkeypatch
) -> None:
    email = "verify-expired@meditour.com"
    assert register(client, email).status_code == 201
    headers = bearer(login(client, email)["access_token"])

    monkeypatch.setattr(
        settings, "EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES", -1
    )
    assert client.post(VERIFY_REQUEST, headers=headers).status_code == 200
    expired_token = latest_verification_token(mail_outbox)

    response = client.post(VERIFY_CONFIRM, json={"token": expired_token})
    assert response.status_code == 400
