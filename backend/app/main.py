"""MediTour 后端入口。"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.db_migrate import ensure_database_schema
from app.logging_config import RequestLoggingMiddleware, configure_logging
from app.metrics import MetricsMiddleware
from app.middleware import (
    ErrorFallbackMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.routers import (
    auth,
    bookings,
    destinations,
    health,
    itineraries,
    medical,
    staff,
    staff_content,
    uploads,
)
from app.routers import metrics as metrics_router
from app.seed import seed_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("MEDITOUR_TESTING") == "1":
        # 测试使用临时数据库，直接建表，避免依赖迁移脚本的执行顺序。
        Base.metadata.create_all(bind=engine)
    else:
        ensure_database_schema()
    with SessionLocal() as db:
        seed_data(db)
    yield


configure_logging()

TAGS_METADATA = [
    {"name": "health", "description": "进程与数据库健康检查（公开）"},
    {"name": "auth", "description": "注册、登录、令牌刷新/登出、密码与账号生命周期"},
    {"name": "medical", "description": "套餐与医院内容（公开，可选多语言）"},
    {"name": "bookings", "description": "用户侧预约订单（需要 Bearer access token）"},
    {"name": "staff", "description": "员工侧订单运营（需要 staff 角色）"},
    {"name": "destinations", "description": "目的地内容（公开）"},
    {"name": "itineraries", "description": "用户行程 CRUD（需要 Bearer access token）"},
]

API_DESCRIPTION = """
MediTour 后端 API。

- 除健康检查、医疗内容、目的地与注册/登录/找回密码外，端点均需要
  `Authorization: Bearer <access_token>`。
- 错误响应通常为 `{"detail": "..."}`；请求参数校验失败时 `detail`
  为字段错误数组，并返回 422。
- 完整错误码含义与各端点行为见 `backend/README.md` 的「错误码对照表」。
"""

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    # 生产默认关闭交互式文档与 OpenAPI，避免把完整接口清单暴露给外部；
    # 开发环境保持默认开启，便于联调。
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)

# 中间件按「后添加的在最外层」生效。从内到外的顺序是：
# 请求日志 → 请求体限流 → 500 兜底 → 安全头 → CORS → 指标。
# 这样 413/500 也经过安全头与 CORS，异常兜底日志仍能拿到 request_id；
# 指标在最外层，能统计到中间件自身产生的 413/500。
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RequestSizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BYTES
)
app.add_middleware(ErrorFallbackMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)
app.add_middleware(MetricsMiddleware)

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(medical.router, prefix=settings.API_V1_PREFIX)
app.include_router(bookings.router, prefix=settings.API_V1_PREFIX)
app.include_router(staff.router, prefix=settings.API_V1_PREFIX)
app.include_router(staff_content.router, prefix=settings.API_V1_PREFIX)
app.include_router(uploads.router, prefix=settings.API_V1_PREFIX)
app.include_router(destinations.router, prefix=settings.API_V1_PREFIX)
app.include_router(itineraries.router, prefix=settings.API_V1_PREFIX)
# 指标端点固定挂在根路径 /metrics（不放在 /api/v1 下），便于抓取配置。
app.include_router(metrics_router.router)

# 本地上传文件直接由后端静态服务提供。仅单机可用：
# 多实例部署需要对象存储（见 app/storage.py）或把该目录挂到共享卷。
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.MEDIA_URL_PATH,
    StaticFiles(directory=str(settings.UPLOAD_DIR)),
    name="uploads",
)
