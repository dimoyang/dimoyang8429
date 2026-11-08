"""可插拔邮件发送。

开发默认 file 后端：把完整邮件（HTML+纯文本）写成 .eml 落到
`MEDITOUR_MAIL_PREVIEW_DIR`，同时在 outbox 写一行索引供测试/脚本读取令牌；
不假装调用真实 SMTP。生产设置 MEDITOUR_MAIL_BACKEND=smtp 并提供 SMTP 配置，
缺配置时抛错而不是静默成功。

日志只记录预览文件路径，绝不写收件人、令牌或完整重置链接。
"""

import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from app.config import settings
from app.mail_templates import (
    RenderedEmail,
    render_email_verification,
    render_password_reset,
)

logger = logging.getLogger("app.mail")


def send_password_reset(
    to: str, token: str, language: str | None = None
) -> Path | None:
    """发送重置密码邮件；file 后端返回生成的 .eml 路径，smtp 返回 None。"""
    reset_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/reset-password?token={token}"
    rendered = render_password_reset(
        language, reset_url, settings.RESET_TOKEN_EXPIRE_MINUTES
    )
    message = _build_message(to, rendered)

    if settings.MAIL_BACKEND == "smtp":
        _send_smtp(message)
        return None
    if settings.MAIL_BACKEND == "file":
        return _write_outbox(to, rendered, message, token)
    raise RuntimeError(
        f"未知的 MEDITOUR_MAIL_BACKEND: {settings.MAIL_BACKEND!r}，"
        "可选值为 file 或 smtp"
    )


def send_email_verification(
    to: str, token: str, language: str | None = None
) -> Path | None:
    """发送邮箱验证邮件；file 后端返回生成的 .eml 路径，smtp 返回 None。"""
    verify_url = (
        f"{settings.PUBLIC_BASE_URL.rstrip('/')}/verify-email?token={token}"
    )
    rendered = render_email_verification(
        language,
        verify_url,
        settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
    )
    message = _build_message(to, rendered)

    if settings.MAIL_BACKEND == "smtp":
        _send_smtp(message)
        return None
    if settings.MAIL_BACKEND == "file":
        return _write_outbox(
            to, rendered, message, token, kind="email_verification"
        )
    raise RuntimeError(
        f"未知的 MEDITOUR_MAIL_BACKEND: {settings.MAIL_BACKEND!r}，"
        "可选值为 file 或 smtp"
    )


def _build_message(to: str, rendered: RenderedEmail) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = rendered.subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    # 纯文本为主，HTML 作为 alternative；客户端不支持 HTML 时仍可读。
    message.set_content(rendered.text)
    message.add_alternative(rendered.html, subtype="html")
    return message


def _write_outbox(
    to: str,
    rendered: RenderedEmail,
    message: EmailMessage,
    token: str,
    kind: str | None = None,
) -> Path:
    preview = _write_preview(message)
    settings.MAIL_OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    suffix = f"\tkind={kind}" if kind else ""
    # 索引行不写完整链接：链接是敏感信息，只保留 token 供开发脚本使用。
    with settings.MAIL_OUTBOX.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{timestamp}\tto={to}\tsubject={rendered.subject}\t"
            f"token={token}\tpreview={preview.name}{suffix}\n"
        )
    event = (
        "email_verification_email_written"
        if kind == "email_verification"
        else "password_reset_email_written"
    )
    logger.info(event, extra={"path": str(preview)})
    return preview


def _write_preview(message: EmailMessage) -> Path:
    settings.MAIL_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = settings.MAIL_PREVIEW_DIR / f"{stamp}-{uuid.uuid4().hex[:8]}.eml"
    path.write_bytes(message.as_bytes())
    return path


def _send_smtp(message: EmailMessage) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError(
            "MEDITOUR_MAIL_BACKEND=smtp 但缺少 MEDITOUR_SMTP_HOST，拒绝发送"
        )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)
