"""安全与健壮性中间件：请求体大小上限、安全响应头、500 兜底。

错误体形状必须保持 `{"detail": ...}`：前端按这个结构解析，
中间件产生的 413/500 也不能例外。
"""

import logging

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("app.error")

TOO_LARGE_DETAIL = "Request body too large"
INTERNAL_ERROR_DETAIL = "Internal server error"

# API 响应不含页面资源，默认全部禁用；文档页面单独放行（Swagger UI 需要 CDN）。
STRICT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
# 文档页不做严格 CSP：Swagger UI / ReDoc 需要加载外部脚本与样式。
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class RequestBodyTooLarge(Exception):
    """内部信号：流式读取时发现请求体超过上限。"""


class ErrorFallbackMiddleware:
    """把未处理异常统一成 500 + `{"detail": "Internal server error"}`。

    堆栈只写服务端日志（经脱敏），绝不出现在响应体里。
    只有响应尚未开始时才能改写；已开始发送的响应无法回滚。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception(
                "unhandled_exception",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                },
            )
            if response_started:
                raise
            response = JSONResponse(
                status_code=500, content={"detail": INTERNAL_ERROR_DETAIL}
            )
            await response(scope, receive, send)


class RequestSizeLimitMiddleware:
    """拒绝过大的请求体，避免超大 JSON 占用内存。

    优先看 `Content-Length` 直接拒绝；没有该头（chunked）时边读边计数，
    超限即中止请求并返回 413。上传接口自身还有更小的文件上限。
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _header_value(scope, b"content-length")
        if declared is not None:
            try:
                declared_size = int(declared)
            except ValueError:
                declared_size = 0
            if declared_size > self.max_bytes:
                await _too_large(send)
                return

        received = 0
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        async def receive_wrapper() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        except RequestBodyTooLarge:
            if response_started:
                raise
            await _too_large(send)


class SecurityHeadersMiddleware:
    """给所有响应加基础安全头。

    HSTS 只在 HTTPS 时下发（直连 TLS 或反代设置 `X-Forwarded-Proto`），
    本地 HTTP 开发不会把浏览器锁到 https。
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        is_https = _is_https(scope)
        is_docs = (scope.get("path") or "").startswith(DOCS_PATHS)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                if not is_docs:
                    headers.append(
                        (b"content-security-policy", STRICT_CSP.encode())
                    )
                if is_https:
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


def _header_value(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1").strip()
    return None


def _is_https(scope: Scope) -> bool:
    if scope.get("scheme") == "https":
        return True
    forwarded = _header_value(scope, b"x-forwarded-proto")
    return bool(forwarded) and forwarded.split(",")[0].strip().lower() == "https"


async def _too_large(send: Send) -> None:
    body = ('{"detail": "' + TOO_LARGE_DETAIL + '"}').encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
