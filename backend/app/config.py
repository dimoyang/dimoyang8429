"""应用配置：全部来自环境变量，默认值仅用于本地开发。"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 本地开发时允许用 backend/.env 提供值（该文件已被 .gitignore 忽略）。
load_dotenv(BASE_DIR / ".env")

# 只用于区分本机/生产默认值（例如指标端点是否默认开放），不参与业务逻辑。
_ENVIRONMENT = os.getenv("MEDITOUR_ENV", "development").strip().lower()


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

    # 邮箱验证令牌有效期（分钟）。短时效、一次性；当前不阻断未验证用户登录。
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("MEDITOUR_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES", "60")
    )
    # 是否把“邮箱已验证”作为创建预约的前置条件。默认关闭；产品确认要强制
    # 验证时再开启。开启后未验证用户仍可登录，只是不能下单（403）。
    REQUIRE_EMAIL_VERIFICATION: bool = os.getenv(
        "MEDITOUR_REQUIRE_EMAIL_VERIFICATION", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}

    # 运行环境：development / production。仅影响默认开关，不做硬编码限制。
    ENVIRONMENT = _ENVIRONMENT
    # /metrics 是否开放：开发默认开、生产默认关；显式设置时以环境变量为准。
    METRICS_ENABLED: bool = os.getenv(
        "MEDITOUR_METRICS_ENABLED",
        "false" if _ENVIRONMENT == "production" else "true",
    ).strip().lower() in {"1", "true", "yes", "on"}
    # /metrics 来源白名单：精确 IP（逗号分隔），空表示不限来源。
    # 只做字符串相等比较，不支持 CIDR；需要网段时应在网关层限制。
    METRICS_ALLOWED_IPS: list[str] = [
        ip.strip()
        for ip in os.getenv("MEDITOUR_METRICS_ALLOWED_IPS", "").split(",")
        if ip.strip()
    ]

    # 数据保留期（天）。清理脚本 scripts/cleanup_data.py 读取这些值。
    TOKEN_RETENTION_DAYS: int = int(
        os.getenv("MEDITOUR_TOKEN_RETENTION_DAYS", "30")
    )
    AUDIT_LOG_RETENTION_DAYS: int = int(
        os.getenv("MEDITOUR_AUDIT_LOG_RETENTION_DAYS", "365")
    )
    # 软删除账号：到期只清理可再生的关联数据，不删用户行与订单（见 README）。
    SOFT_DELETED_ACCOUNT_RETENTION_DAYS: int = int(
        os.getenv("MEDITOUR_SOFT_DELETED_ACCOUNT_RETENTION_DAYS", "30")
    )
    MAIL_PREVIEW_RETENTION_DAYS: int = int(
        os.getenv("MEDITOUR_MAIL_PREVIEW_RETENTION_DAYS", "14")
    )
    UPLOAD_TEMP_RETENTION_DAYS: int = int(
        os.getenv("MEDITOUR_UPLOAD_TEMP_RETENTION_DAYS", "1")
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
