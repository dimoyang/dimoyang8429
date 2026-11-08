"""健康检查与 CORS 预检测试。"""


def test_health_reports_database_ok(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_cors_preflight_allows_local_frontend(client) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:8123",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8123"
