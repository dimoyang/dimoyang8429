"""可插拔邮件发送。

开发默认 file 后端：把邮件写入 MEDITOUR_MAIL_OUTBOX 文件，不假装调用真实 SMTP。
生产设置 MEDITOUR_MAIL_BACKEND=smtp 并提供 SMTP 配置；缺配置时抛错而不是静默成功。
"""

import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("app.mail")


def send_password_reset(to: str, token: str) -> None:
    reset_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/reset-password?token={token}"
    if settings.MAIL_BACKEND == "smtp":
        _send_smtp(to, reset_url)
        return
    if settings.MAIL_BACKEND == "file":
        _write_outbox(to, reset_url, token)
        return
    raise RuntimeError(
        f"未知的 MEDITOUR_MAIL_BACKEND: {settings.MAIL_BACKEND!r}，"
        "可选值为 file 或 smtp"
    )


def _write_outbox(to: str, reset_url: str, token: str) -> None:
    settings.MAIL_OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with settings.MAIL_OUTBOX.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{timestamp}\tto={to}\tsubject=Reset your MediTour password\t"
            f"token={token}\treset_url={reset_url}\n"
        )
    # 只记录“已写入文件”，不把收件人和令牌写进常规日志。
    logger.info("password_reset_email_written", extra={"path": str(settings.MAIL_OUTBOX)})


def _send_smtp(to: str, reset_url: str) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError(
            "MEDITOUR_MAIL_BACKEND=smtp 但缺少 MEDITOUR_SMTP_HOST，拒绝发送"
        )

    message = EmailMessage()
    message["Subject"] = "Reset your MediTour password"
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message.set_content(
        "Use the link below to reset your MediTour password. "
        "The link expires soon and can only be used once.\n\n"
        f"{reset_url}\n"
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_STARTTLS:
            smtp.starttls()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)
