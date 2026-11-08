"""轻量指标：纯文本输出、开关与不泄露敏感信息。"""

import re

from app.config import settings
from app.metrics import registry


def _metric_value(body: str, name: str) -> float:
    match = re.search(rf"^{name} (\S+)$", body, re.MULTILINE)
    assert match, f"缺少指标 {name}"
    return float(match.group(1))


def test_metrics_endpoint_reports_counts_and_histogram(client) -> None:
    registry.reset()
    assert client.get("/api/v1/health").status_code == 200

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text

    assert _metric_value(body, "meditour_requests_total") >= 1
    assert "meditour_requests_by_method{method=\"GET\"}" in body
    assert "meditour_responses_total{status=\"200\"}" in body
    assert "meditour_request_duration_ms_bucket{le=\"+Inf\"}" in body
    assert "meditour_request_duration_ms_count" in body
    assert "meditour_db_pool_" in body

    # /metrics 自身不计入请求数：连续抓取两次，总数不变。
    first_total = _metric_value(body, "meditour_requests_total")
    second = client.get("/metrics").text
    assert _metric_value(second, "meditour_requests_total") == first_total

    # 不输出令牌、鉴权头或请求内容。
    lowered = body.lower()
    assert "authorization" not in lowered
    assert "bearer" not in lowered
    assert "token=" not in lowered


def test_metrics_endpoint_can_be_disabled(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "METRICS_ENABLED", False)
    response = client.get("/metrics")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
