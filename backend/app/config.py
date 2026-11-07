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
    # 前端没有刷新机制，使用 7 天有效期。
    ACCESS_TOKEN_EXPIRE_DAYS = 7

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'meditour.db').as_posix()}"
    )

    # 单一币种来源：种子数据与订单金额均引用此配置。
    DEFAULT_CURRENCY: str = os.getenv("MEDITOUR_CURRENCY", "EUR")

    CORS_ORIGINS: list[str] = [
        "http://localhost:8123",
        "http://127.0.0.1:8123",
    ]


settings = Settings()

if not settings.SECRET_KEY:
    raise RuntimeError(
        "缺少 JWT 密钥：请设置环境变量 MEDITOUR_SECRET_KEY（或 SECRET_KEY），"
        "也可以在 backend/.env 中配置。"
    )
