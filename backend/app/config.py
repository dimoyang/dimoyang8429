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
    PUBLIC_BASE_URL: str = os.getenv(
        "MEDITOUR_PUBLIC_BASE_URL", "http://localhost:8123"
    )

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
