"""结构化请求日志与脱敏规则。

所有日志统一从这里输出 JSON；路由代码只记业务事件，不直接拼接敏感字段。
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REDACTED = "[REDACTED]"

_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
# 7 位以上连续数字（允许空格、括号、点、短横线），用于兜底手机号。
_PHONE_RE = re.compile(r"(?<![\w-])\+?\d[\d\s().-]{5,}\d(?![\w-])")
_SENSITIVE_KV_RE = re.compile(
    r"(?i)\b(password|passwd|token|access_token|refresh_token|authorization|"
    r"notes|phone|email)\b\s*[:=]\s*[^\s,;&]+"
)
_SENSITIVE_JSON_RE = re.compile(
    r'(?i)"(password|passwd|token|access_token|refresh_token|authorization|'
    r'notes|phone|email)"\s*:\s*"[^"]*"'
)


def _mask_phone(match: re.Match[str]) -> str:
    text = match.group(0)
    digits = re.sub(r"\D", "", text)
    # 不误伤日期（如 2026-11-08）。
    if len(digits) < 7 or re.fullmatch(r"\d{4}-\d{2}-\d{2}", text.strip()):
        return text
    return REDACTED


def sanitize(value: str) -> str:
    """按固定规则脱敏：JWT、邮箱、手机号、敏感键值。"""
    value = _JWT_RE.sub(REDACTED, value)
    value = _EMAIL_RE.sub(REDACTED, value)
    value = _PHONE_RE.sub(_mask_phone, value)
    value = _SENSITIVE_JSON_RE.sub(
        lambda m: f'"{m.group(1)}": "{REDACTED}"', value
    )
    value = _SENSITIVE_KV_RE.sub(lambda m: f"{m.group(1)}={REDACTED}", value)
    return value


class RedactionFilter(logging.Filter):
    """在格式化前清洗消息与参数，避免任何 handler 写出明文。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: sanitize(str(item)) for key, item in record.args.items()
                }
            else:
                record.args = tuple(sanitize(str(item)) for item in record.args)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize(record.getMessage()),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = sanitize(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger("app")
    if any(getattr(handler, "_meditour_json", False) for handler in logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    handler._meditour_json = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False


logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """记录 request_id、耗时、状态码；只记录路径，不记录查询串与请求体。"""

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming[:64] if incoming else uuid.uuid4().hex
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
