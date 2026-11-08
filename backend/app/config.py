"""应用配置：全部来自环境变量，默认值仅用于本地开发。"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 本地开发时允许用 backend/.env 提供值（该文件已被 .gitignore 忽略）。
load_dotenv(BASE_DIR / ".env")


class Settings:
    """集中配置，币种只在这里定义一次。"""

    APP_NAME = "MediTour API"
    API_V1_PREFIX = "/api/v1"

    SECRET_KEY: str = os.getenv("MEDITOUR_SECRET_KEY", os.getenv("SECRET_KEY", ""))
    JWT_ALGORITHM = "HS256"
    # 前端目前只用 access token；refresh token 供后续客户端升级使用。
    ACCESS_TOKEN_EXPIRE_DAYS = int(
        os.getenv("MEDITOUR_ACCESS_TOKEN_EXPIRE_DAYS", "7")
    )
    REFRESH_TOKEN_EXPIRE_DAYS = int(
        os.getenv("MEDITOUR_REFRESH_TOKEN_EXPIRE_DAYS", "30")
    )

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'meditour.db').as_posix()}"
    )

    # 单一币种来源：种子数据与订单金额均引用此配置。
    DEFAULT_CURRENCY: str = os.getenv("MEDITOUR_CURRENCY", "EUR")

    # 允许来源：逗号分隔的环境变量；未配置时保留本地 Flutter Web 默认端口。
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "MEDITOUR_CORS_ORIGINS",
            "http://localhost:8123,http://127.0.0.1:8123",
        ).split(",")
        if origin.strip()
    ]

    # 演示账号默认不创建，只有显式开启时才写入种子数据（生产环境不要开启）。
    SEED_DEMO_USER: bool = os.getenv(
        "MEDITOUR_SEED_DEMO_USER", ""
    ).strip().lower() in {"1", "true", "yes", "on"}

    # 员工角色白名单（逗号分隔邮箱）。登录时命中名单会授予 staff，
    # 但不会自动创建账号；撤销请用 scripts/manage_staff.py --revoke。
    STAFF_EMAILS: list[str] = [
        email.strip().lower()
        for email in os.getenv("MEDITOUR_STAFF_EMAILS", "").split(",")
        if email.strip()
    ]

    # 忘记密码令牌有效期（分钟）。
    RESET_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("MEDITOUR_RESET_TOKEN_EXPIRE_MINUTES", "30")
    )

    # 邮件实现：file（开发默认，写入 outbox 文件）/ smtp（生产配置位）。
    MAIL_BACKEND: str = os.getenv("MEDITOUR_MAIL_BACKEND", "file").strip().lower()
    MAIL_OUTBOX: Path = Path(
        os.getenv(
            "MEDITOUR_MAIL_OUTBOX",
            str(BASE_DIR / "var" / "mail_outbox.log"),
        )
    )
    # file 后端把完整邮件（HTML+纯文本）落成 .eml 便于本地预览；
    # outbox 只保留一行索引（含 token，供开发脚本读取）。
    MAIL_PREVIEW_DIR: Path = Path(
        os.getenv(
            "MEDITOUR_MAIL_PREVIEW_DIR",
            str(BASE_DIR / "var" / "mail_preview"),
        )
    )
    PUBLIC_BASE_URL: str = os.getenv(
        "MEDITOUR_PUBLIC_BASE_URL", "http://localhost:8123"
    )

    # 上传存储：local（默认，落本机磁盘）或 s3（预留位，当前未实现）。
    STORAGE_BACKEND: str = os.getenv(
        "MEDITOUR_STORAGE_BACKEND", "local"
    ).strip().lower()
    UPLOAD_DIR: Path = Path(
        os.getenv("MEDITOUR_UPLOAD_DIR", str(BASE_DIR / "var" / "uploads"))
    )
    UPLOAD_MAX_BYTES: int = int(
        os.getenv("MEDITOUR_UPLOAD_MAX_BYTES", str(5 * 1024 * 1024))
    )
    # 全局请求体上限（字节）。必须大于上传接口的单文件上限，
    # 否则图片还没进入上传校验就会被中间件拒绝。
    MAX_REQUEST_BYTES: int = int(
        os.getenv("MEDITOUR_MAX_REQUEST_BYTES", str(10 * 1024 * 1024))
    )
    # 对外 URL 前缀（挂载点）。修改后需要同步调整 main.py 的 StaticFiles 挂载。
    MEDIA_URL_PATH: str = "/media/uploads"
    # 媒体资源的对外域名/CDN。留空时返回站内相对路径；配置后返回绝对 URL。
    MEDIA_BASE_URL: str = os.getenv("MEDITOUR_MEDIA_BASE_URL", "").rstrip("/")

    SMTP_HOST: str = os.getenv("MEDITOUR_SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("MEDITOUR_SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("MEDITOUR_SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("MEDITOUR_SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("MEDITOUR_SMTP_FROM", "no-reply@meditour.local")
    SMTP_STARTTLS: bool = os.getenv(
        "MEDITOUR_SMTP_STARTTLS", "1"
    ).strip().lower() in {"1", "true", "yes", "on"}


settings = Settings()

if not settings.SECRET_KEY:
    raise RuntimeError(
        "缺少 JWT 密钥：请设置环境变量 MEDITOUR_SECRET_KEY（或 SECRET_KEY），"
        "也可以在 backend/.env 中配置。"
    )
