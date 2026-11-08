"""轻量运行指标：进程内计数 + 纯文本输出。

选型说明：当前只需要请求总数、状态码分布、耗时直方图和数据库连接池状态这几组
固定指标，引入 `prometheus_client` 会多一个运行时依赖，并带来注册表重复导入、
多进程聚合等额外问题。这里用最少的代码渲染 Prometheus 文本格式的兼容子集，
需要聚合时由 Prometheus 抓取或改用官方客户端，而不是现在提前引入。

限制：计数保存在进程内，多 worker 部署时各进程独立；重启后清零。指标端点与
业务响应一样不包含路径参数、令牌或请求体，避免把敏感信息带进监控系统。
"""

from __future__ import annotations

import threading
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# 毫秒分桶；最后一个 +Inf 桶由渲染阶段补齐。
LATENCY_BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)

METRICS_PATH = "/metrics"


class MetricsRegistry:
    """线程安全的进程内指标；所有读写都在同一把锁内完成。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started_at = time.monotonic()
        self.requests_total = 0
        self.by_method: dict[str, int] = {}
        self.by_status: dict[int, int] = {}
        # 累积计数：bucket[i] 表示耗时 <= LATENCY_BUCKETS_MS[i] 的请求数。
        self._bucket_counts = [0] * len(LATENCY_BUCKETS_MS)
        self.duration_sum_ms = 0.0
        self.duration_count = 0

    def record(self, method: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self.requests_total += 1
            self.by_method[method] = self.by_method.get(method, 0) + 1
            self.by_status[status_code] = self.by_status.get(status_code, 0) + 1
            self.duration_sum_ms += duration_ms
            self.duration_count += 1
            for index, upper in enumerate(LATENCY_BUCKETS_MS):
                if duration_ms <= upper:
                    self._bucket_counts[index] += 1

    def reset(self) -> None:
        """测试辅助：清空计数并重置启动时间。"""
        with self._lock:
            self.started_at = time.monotonic()
            self.requests_total = 0
            self.by_method.clear()
            self.by_status.clear()
            self._bucket_counts = [0] * len(LATENCY_BUCKETS_MS)
            self.duration_sum_ms = 0.0
            self.duration_count = 0

    def render(self) -> str:
        with self._lock:
            uptime = time.monotonic() - self.started_at
            methods = sorted(self.by_method.items())
            statuses = sorted(self.by_status.items())
            buckets = list(self._bucket_counts)
            duration_sum = self.duration_sum_ms
            duration_count = self.duration_count
            requests_total = self.requests_total

        lines = [
            "# HELP meditour_uptime_seconds Process uptime in seconds.",
            "# TYPE meditour_uptime_seconds gauge",
            f"meditour_uptime_seconds {uptime:.3f}",
            "# HELP meditour_requests_total Total HTTP requests handled.",
            "# TYPE meditour_requests_total counter",
            f"meditour_requests_total {requests_total}",
            "# TYPE meditour_requests_by_method counter",
        ]
        lines.extend(
            f'meditour_requests_by_method{{method="{method}"}} {count}'
            for method, count in methods
        )
        lines.append("# TYPE meditour_responses_total counter")
        lines.extend(
            f'meditour_responses_total{{status="{status}"}} {count}'
            for status, count in statuses
        )
        lines.append("# TYPE meditour_request_duration_ms histogram")
        lines.extend(
            (
                "meditour_request_duration_ms_bucket"
                f'{{le="{upper}"}} {buckets[index]}'
            )
            for index, upper in enumerate(LATENCY_BUCKETS_MS)
        )
        lines.append(
            "meditour_request_duration_ms_bucket"
            f'{{le="+Inf"}} {duration_count}'
        )
        lines.append(
            f"meditour_request_duration_ms_sum {duration_sum:.3f}"
        )
        lines.append(f"meditour_request_duration_ms_count {duration_count}")
        lines.extend(_database_pool_lines())
        return "\n".join(lines) + "\n"


def _database_pool_lines() -> list[str]:
    """连接池状态；非池化后端（如 StaticPool）明确标记为不可用。"""
    from app.database import engine

    pool = engine.pool
    try:
        size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
    except (AttributeError, NotImplementedError):
        return [
            "# TYPE meditour_db_pool_available gauge",
            "meditour_db_pool_available 0",
        ]
    return [
        "# TYPE meditour_db_pool_available gauge",
        "meditour_db_pool_available 1",
        "# TYPE meditour_db_pool_size gauge",
        f"meditour_db_pool_size {size}",
        "# TYPE meditour_db_pool_checked_out gauge",
        f"meditour_db_pool_checked_out {checked_out}",
        "# TYPE meditour_db_pool_overflow gauge",
        f"meditour_db_pool_overflow {overflow}",
    ]


registry = MetricsRegistry()


class MetricsMiddleware:
    """记录每个 HTTP 请求的状态码与耗时；跳过 /metrics 自身。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") == METRICS_PATH:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            registry.record(method, 500, (time.perf_counter() - started) * 1000)
            raise
        registry.record(method, status_code, (time.perf_counter() - started) * 1000)
