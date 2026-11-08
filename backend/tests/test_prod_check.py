"""上线配置自检脚本：生产断言能拦住默认/开发配置。"""

from types import SimpleNamespace

from scripts.prod_check import FAIL, PASS, WARN, check_all


def _config(**overrides) -> SimpleNamespace:
    base = dict(
        SECRET_KEY="u9Kx2vQ7mN4pR8sT1wY6zA3bC5dE0fG2hJ7kL9mP",
        DOCS_ENABLED=False,
        CORS_ORIGINS=["https://app.meditour.com"],
        METRICS_ENABLED=True,
        METRICS_ALLOWED_IPS=["10.0.0.5"],
        SEED_DEMO_USER=False,
        SEED_DEMO_DATA=False,
        REQUIRE_EMAIL_VERIFICATION=True,
        DATABASE_URL="postgresql+psycopg://user:pass@db:5432/meditour",
        PUBLIC_BASE_URL="https://api.meditour.com",
        MAIL_BACKEND="smtp",
        STORAGE_BACKEND="s3",
        ENVIRONMENT="production",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _by_name(results) -> dict:
    return {result.name: result for result in results}


def test_production_ready_config_passes() -> None:
    results = check_all(_config(), production=True)
    failed = [item for item in results if item.status == FAIL]
    warned = {item.name for item in results if item.status == WARN}
    assert [item.name for item in failed] == []
    # 进程内限流在单实例下可用，但扩多 worker 前必须换共享存储：只警告。
    assert warned == {"限流后端"}


def test_default_config_is_blocked_in_production() -> None:
    results = _by_name(
        check_all(
            _config(
                SECRET_KEY="changeme",
                DOCS_ENABLED=True,
                CORS_ORIGINS=["*"],
                METRICS_ENABLED=True,
                METRICS_ALLOWED_IPS=[],
                SEED_DEMO_USER=True,
                SEED_DEMO_DATA=True,
                REQUIRE_EMAIL_VERIFICATION=False,
                DATABASE_URL="sqlite:///meditour.db",
                PUBLIC_BASE_URL="http://localhost:8123",
                MAIL_BACKEND="file",
                STORAGE_BACKEND="local",
                ENVIRONMENT="development",
            ),
            production=True,
        )
    )

    failed = {name for name, item in results.items() if item.status == FAIL}
    assert {
        "JWT 签名密钥",
        "调试/文档端点",
        "CORS 来源",
        "/metrics 暴露面",
        "演示账号/演示数据开关",
        "邮箱验证前置",
        "数据库",
        "对外访问协议",
        "邮件后端",
    } <= failed

    # 本地上传存储与进程内限流在单机部署下可用，生产只作为警告，不阻断。
    assert results["上传存储"].status == WARN
    assert results["限流后端"].status == WARN
    assert results["运行环境标记"].status == WARN


def test_short_or_empty_secret_is_always_failed() -> None:
    for secret in ("", "short-secret"):
        item = _by_name(check_all(_config(SECRET_KEY=secret), production=False))[
            "JWT 签名密钥"
        ]
        assert item.status == FAIL
        assert item.fix


def test_dev_config_only_warns_in_report_mode() -> None:
    results = check_all(
        _config(
            DOCS_ENABLED=True,
            CORS_ORIGINS=["http://localhost:8123"],
            METRICS_ENABLED=True,
            METRICS_ALLOWED_IPS=[],
            DATABASE_URL="sqlite:///meditour.db",
            PUBLIC_BASE_URL="http://localhost:8123",
            MAIL_BACKEND="file",
        ),
        production=False,
    )
    statuses = {item.name: item.status for item in results}
    assert statuses["调试/文档端点"] == WARN
    assert statuses["CORS 来源"] == WARN
    assert statuses["数据库"] == WARN
    assert statuses["对外访问协议"] == WARN
    assert statuses["JWT 签名密钥"] == PASS


def test_each_failure_carries_a_fix_hint() -> None:
    results = check_all(
        _config(
            SECRET_KEY="",
            DOCS_ENABLED=True,
            CORS_ORIGINS=["*"],
            METRICS_ALLOWED_IPS=[],
            SEED_DEMO_DATA=True,
            REQUIRE_EMAIL_VERIFICATION=False,
            DATABASE_URL="sqlite:///meditour.db",
            PUBLIC_BASE_URL="http://localhost:8123",
            MAIL_BACKEND="file",
        ),
        production=True,
    )
    for item in results:
        if item.status == FAIL:
            assert item.fix, item.name
