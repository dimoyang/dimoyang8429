"""重置密码邮件：多语言模板、file 后端 .eml 与日志脱敏。"""

import logging
import re
from email import policy
from email.parser import BytesParser

from app.mail_templates import normalize_mail_language, render_password_reset

RESET_URL = "https://meditour.example/reset-password?token=abc123"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(self.format(record))


def test_templates_render_text_and_html_for_each_language() -> None:
    subjects = set()
    for language in ("en", "zh", "de", "fr"):
        rendered = render_password_reset(language, RESET_URL, 30)
        subjects.add(rendered.subject)
        assert RESET_URL in rendered.text
        assert RESET_URL in rendered.html
        assert "<html" in rendered.html
        assert "<" not in rendered.text
        assert "30" in rendered.text

    assert len(subjects) == 4


def test_language_normalization_and_fallback() -> None:
    assert normalize_mail_language("zh-CN") == "zh"
    assert normalize_mail_language("de_DE") == "de"
    assert normalize_mail_language("FR") == "fr"
    assert normalize_mail_language("es") == "en"
    assert normalize_mail_language(None) == "en"
    assert normalize_mail_language("") == "en"

    german = render_password_reset("de-AT", RESET_URL, 15)
    assert german.subject == "MediTour-Passwort zurücksetzen"
    assert "15 Minuten" in german.text


def test_reset_email_uses_user_language_and_writes_eml(
    client, mail_outbox, mail_preview_dir
) -> None:
    email = "mail-de@meditour.com"
    created = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "MailPass123456",
            "full_name": "Mail User",
            "preferred_language": "de-DE",
        },
    )
    assert created.status_code == 201, created.text

    before = {path.name for path in mail_preview_dir.glob("*.eml")}
    response = client.post(
        "/api/v1/auth/password-reset/request", json={"email": email}
    )
    assert response.status_code == 200

    new_files = [
        path
        for path in mail_preview_dir.glob("*.eml")
        if path.name not in before
    ]
    assert len(new_files) == 1, "file 后端应生成一封 .eml"
    preview = new_files[0]

    message = BytesParser(policy=policy.default).parsebytes(
        preview.read_bytes()
    )
    assert message["To"] == email
    assert message["Subject"] == "MediTour-Passwort zurücksetzen"

    text_part = message.get_body(preferencelist=("plain",))
    html_part = message.get_body(preferencelist=("html",))
    assert text_part is not None and html_part is not None
    text_body = text_part.get_content()
    html_body = html_part.get_content()
    assert "/reset-password?token=" in text_body
    assert "/reset-password?token=" in html_body

    # outbox 只保留索引：可以有 token（开发工具需要），但不能出现完整链接。
    last_line = (
        mail_outbox.read_text(encoding="utf-8").strip().splitlines()[-1]
    )
    assert "reset-password" not in last_line
    assert "reset_url=" not in last_line
    token = re.search(r"\btoken=(\S+)", last_line).group(1)
    assert token in text_body


def test_reset_logs_do_not_contain_token_or_link(
    client, mail_outbox
) -> None:
    email = "mail-logs@meditour.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "MailPass123456",
            "preferred_language": "en",
        },
    )

    capture = _Capture()
    capture.setFormatter(logging.Formatter("%(message)s"))
    app_logger = logging.getLogger("app")
    app_logger.addHandler(capture)
    try:
        response = client.post(
            "/api/v1/auth/password-reset/request", json={"email": email}
        )
    finally:
        app_logger.removeHandler(capture)

    assert response.status_code == 200
    last_line = (
        mail_outbox.read_text(encoding="utf-8").strip().splitlines()[-1]
    )
    token = re.search(r"\btoken=(\S+)", last_line).group(1)

    joined = "\n".join(capture.messages)
    assert "password_reset_email_written" in joined
    assert token not in joined
    assert "reset-password" not in joined
