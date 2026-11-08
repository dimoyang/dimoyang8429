"""日志脱敏与 request id 测试。"""

import logging

from app.logging_config import JsonFormatter, sanitize


def test_sanitize_redacts_sensitive_values() -> None:
    raw = (
        "email=alice@example.com phone=+86 138-0000-0000 "
        "password=hunter2 token=abc123 notes=diabetes"
    )
    cleaned = sanitize(raw)
    assert "alice@example.com" not in cleaned
    assert "138-0000-0000" not in cleaned
    assert "hunter2" not in cleaned
    assert "abc123" not in cleaned
    assert "diabetes" not in cleaned
    assert cleaned.count("[REDACTED]") >= 5


def test_sanitize_redacts_jwt_and_json_fields() -> None:
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl"
    raw = f'payload {{"email": "bob@example.com", "notes": "asthma", "token": "{token}"}}'
    cleaned = sanitize(raw)
    assert token not in cleaned
    assert "bob@example.com" not in cleaned
    assert "asthma" not in cleaned


def test_sanitize_does_not_redact_dates() -> None:
    assert "2026-11-08" in sanitize("created_at=2026-11-08")


def test_json_formatter_never_emits_plaintext() -> None:
    record = logging.LogRecord(
        "app",
        logging.INFO,
        __file__,
        1,
        "login %s token=%s notes=%s",
        ("carol@example.com", "secret-token", "diabetes"),
        None,
    )
    output = JsonFormatter().format(record)
    assert "carol@example.com" not in output
    assert "secret-token" not in output
    assert "diabetes" not in output
    assert "[REDACTED]" in output


def test_request_id_is_returned_and_echoed(client) -> None:
    generated = client.get("/api/v1/health")
    assert generated.headers["x-request-id"]

    echoed = client.get(
        "/api/v1/health", headers={"X-Request-ID": "trace-abc-123"}
    )
    assert echoed.headers["x-request-id"] == "trace-abc-123"
