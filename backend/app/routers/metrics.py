"""指标端点：纯文本、无鉴权、可通过配置关闭。

关闭时返回 404 而不是 403，避免向未授权访问者暴露端点存在。
路由不写进 OpenAPI（`include_in_schema=False`），也不返回任何请求内容。
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.metrics import registry

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    include_in_schema=False,
    response_class=PlainTextResponse,
    summary="进程指标（纯文本）",
    description=(
        "请求计数、状态码分布、耗时直方图与数据库连接池状态。"
        "开发环境默认开放，生产默认关闭；由 `MEDITOUR_METRICS_ENABLED` 控制。"
        "关闭时返回 404。"
    ),
)
def metrics() -> PlainTextResponse:
    if not settings.METRICS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
        )
    return PlainTextResponse(
        registry.render(), media_type="text/plain; version=0.0.4"
    )
