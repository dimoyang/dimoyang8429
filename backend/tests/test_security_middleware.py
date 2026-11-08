"""安全中间件：体积上限、安全响应头、500 兜底形状。"""

from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.main import app


def _assert_error_shape(response) -> None:
    payload = response.json()
    assert isinstance(payload, dict)
    assert list(payload) == ["detail"]


def test_security_headers_on_plain_http(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    # 纯 HTTP 下不得下发 HSTS，否则会把本地开发锁进 https。
    assert "strict-transport-security" not in response.headers


def test_hsts_only_for_https_requests(client) -> None:
    forwarded = client.get(
        "/api/v1/health", headers={"X-Forwarded-Proto": "https"}
    )
    assert forwarded.headers["strict-transport-security"].startswith(
        "max-age=31536000"
    )

    with TestClient(app, base_url="https://testserver") as https_client:
        direct = https_client.get("/api/v1/health")
    assert "strict-transport-security" in direct.headers


def test_docs_gets_no_strict_csp(client) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" not in response.headers


def test_oversized_body_is_rejected_with_413(client) -> None:
    payload = {"password": "x" * (settings.MAX_REQUEST_BYTES + 1)}
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}
    _assert_error_shape(response)


def test_oversized_chunked_body_is_rejected() -> None:
    """没有 Content-Length 时也要在流式读取阶段中止。

    TestClient 会把生成器内容整体缓冲，无法覆盖分块路径，因此直接驱动
    ASGI 中间件。
    """
    import asyncio
    import json

    from app.middleware import RequestSizeLimitMiddleware

    async def consume_app(scope, receive, send) -> None:
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    incoming = iter(
        [
            {"type": "http.request", "body": b"123456", "more_body": True},
            {"type": "http.request", "body": b"123456", "more_body": False},
        ]
    )
    sent: list[dict] = []

    async def receive():
        return next(incoming)

    async def send(message):
        sent.append(message)

    middleware = RequestSizeLimitMiddleware(consume_app, max_bytes=8)
    asyncio.run(
        middleware(
            {"type": "http", "method": "POST", "path": "/x", "headers": []},
            receive,
            send,
        )
    )

    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"]) == {"detail": "Request body too large"}


def test_unhandled_exception_returns_generic_500(client) -> None:
    def _boom():
        raise RuntimeError("kaboom-internal-detail")

    app.dependency_overrides[get_db] = _boom
    try:
        with TestClient(app, raise_server_exceptions=False) as failing:
            response = failing.get("/api/v1/medical/hospitals")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "kaboom" not in response.text
    assert "Traceback" not in response.text
    # 兜底响应同样经过安全头中间件。
    assert response.headers["x-content-type-options"] == "nosniff"
