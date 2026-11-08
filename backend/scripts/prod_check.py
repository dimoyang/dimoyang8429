"""上线前配置自检：扫描当前配置的风险项，输出 pass/fail/warn 与修复建议。

用法：

    python scripts/prod_check.py                 # 只报告，不改变退出码
    python scripts/prod_check.py --production    # 按生产断言，有 fail 时退出码 1

检查读取的是当前进程加载的 `app.config.settings`（含 `backend/.env` 与
环境变量），不会连接数据库、不会修改任何状态。部署流水线里应在启动服务前
执行 `--production`，不达标就阻断发布。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

# 常见示例值/占位符；上线前必须换成长随机串。
WEAK_SECRETS = {
    "secret",
    "secret-key",
    "changeme",
    "change-me",
    "change_me",
    "your-secret-key",
    "your_secret_key",
    "test-secret-key-for-pytest-32-bytes-minimum",
    "dev-secret-key-for-local-development-32",
    "meditour",
    "password",
}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    fix: str = ""


def _result(name: str, ok: bool, detail: str, fix: str = "", *, warn_only: bool = False) -> CheckResult:
    if ok:
        return CheckResult(name, PASS, detail)
    return CheckResult(name, WARN if warn_only else FAIL, detail, fix)


def check_secret_key(config, *, production: bool) -> CheckResult:
    secret = (getattr(config, "SECRET_KEY", "") or "").strip()
    name = "JWT 签名密钥"
    if not secret:
        return CheckResult(
            name, FAIL, "SECRET_KEY 为空", "设置 MEDITOUR_SECRET_KEY（至少 32 字节随机值）"
        )
    if secret.lower() in WEAK_SECRETS:
        return CheckResult(
            name, FAIL, "SECRET_KEY 是示例/测试占位值", "生成新的随机密钥并只通过环境注入"
        )
    if len(secret) < 32:
        return CheckResult(
            name,
            FAIL,
            f"SECRET_KEY 仅 {len(secret)} 字节，低于 32",
            "使用 `python -c \"import secrets;print(secrets.token_urlsafe(48))\"` 生成",
        )
    if len(set(secret)) < 8:
        return CheckResult(
            name, FAIL, "SECRET_KEY 字符种类过少，疑似重复串", "换成高熵随机值"
        )
    return CheckResult(name, PASS, f"长度 {len(secret)} 字节，非占位值")


def check_docs(config, *, production: bool) -> CheckResult:
    enabled = bool(getattr(config, "DOCS_ENABLED", False))
    name = "调试/文档端点"
    if not enabled:
        return CheckResult(name, PASS, "/docs、/redoc、/openapi.json 已关闭")
    return _result(
        name,
        False,
        "交互式文档与 OpenAPI 仍对外开放，会暴露完整接口清单",
        "设置 MEDITOUR_DOCS_ENABLED=0（生产默认关闭）",
        warn_only=not production,
    )


def check_cors(config, *, production: bool) -> CheckResult:
    origins = list(getattr(config, "CORS_ORIGINS", []) or [])
    name = "CORS 来源"
    if not origins:
        return _result(
            name,
            False,
            "CORS 来源为空，浏览器前端将无法调用",
            "按实际前端域名配置 MEDITOUR_CORS_ORIGINS",
            warn_only=True,
        )
    problems: list[str] = []
    for origin in origins:
        normalized = origin.strip().lower().rstrip("/")
        if normalized == "*":
            problems.append("通配 *")
            continue
        parsed = urlparse(normalized)
        host = (parsed.hostname or "").lower()
        if host in LOCAL_HOSTS:
            problems.append(f"本地地址 {origin}")
        elif parsed.scheme != "https":
            problems.append(f"非 HTTPS {origin}")
    if problems:
        return _result(
            name,
            False,
            "；".join(problems),
            "只保留真实前端域名，且使用 https://",
            warn_only=not production,
        )
    return CheckResult(name, PASS, f"{len(origins)} 个来源，均为 HTTPS 非本地地址")


def check_metrics(config, *, production: bool) -> CheckResult:
    enabled = bool(getattr(config, "METRICS_ENABLED", False))
    allowed = list(getattr(config, "METRICS_ALLOWED_IPS", []) or [])
    name = "/metrics 暴露面"
    if not enabled:
        return CheckResult(name, PASS, "未开放")
    if allowed:
        return CheckResult(name, PASS, f"已开放，但限制来源 IP：{', '.join(allowed)}")
    return _result(
        name,
        False,
        "已开放且来源 IP 白名单为空，任何能访问服务的人都能读取运行指标",
        "设置 MEDITOUR_METRICS_ALLOWED_IPS，或关闭 MEDITOUR_METRICS_ENABLED",
        warn_only=not production,
    )


def check_demo_flags(config, *, production: bool) -> CheckResult:
    demo_user = bool(getattr(config, "SEED_DEMO_USER", False))
    demo_data = bool(getattr(config, "SEED_DEMO_DATA", False))
    name = "演示账号/演示数据开关"
    if not demo_user and not demo_data:
        return CheckResult(name, PASS, "两个开关均关闭")
    enabled = [
        flag
        for flag, value in (
            ("MEDITOUR_SEED_DEMO_USER", demo_user),
            ("MEDITOUR_SEED_DEMO_DATA", demo_data),
        )
        if value
    ]
    return _result(
        name,
        False,
        f"{', '.join(enabled)} 处于开启状态，启动时会写入演示账号/目录数据",
        "关闭开关；已写入的演示账号需手动删除（关闭开关不会自动清理）",
        warn_only=not production,
    )


def check_email_verification(config, *, production: bool) -> CheckResult:
    required = bool(getattr(config, "REQUIRE_EMAIL_VERIFICATION", False))
    name = "邮箱验证前置"
    if required:
        return CheckResult(name, PASS, "未验证邮箱的账号不能创建预约")
    return _result(
        name,
        False,
        "强制邮箱验证关闭，未验证邮箱也能下单",
        "设置 MEDITOUR_REQUIRE_EMAIL_VERIFICATION=1",
        warn_only=not production,
    )


def check_database(config, *, production: bool) -> CheckResult:
    url = str(getattr(config, "DATABASE_URL", "") or "")
    name = "数据库"
    if not url:
        return CheckResult(name, FAIL, "DATABASE_URL 为空", "配置数据库连接串")
    if url.startswith("sqlite"):
        return _result(
            name,
            False,
            "使用 SQLite：单写者、无网络多实例、备份无法做时间点恢复",
            "生产切换到 PostgreSQL（见 README「PostgreSQL 切换脚手架」）",
            warn_only=not production,
        )
    return CheckResult(name, PASS, url.split("://", 1)[0])


def check_rate_limit_backend(config, *, production: bool) -> CheckResult:
    name = "限流后端"
    detail = "限流计数在进程内存中：多 worker/多实例各自计数，重启清零"
    # 单 worker + 单实例部署时进程内计数可用，因此只警告不阻断；
    # 一旦扩到多进程/多实例，这条必须升级为 FAIL 或先换成共享存储。
    return _result(
        name,
        False,
        detail,
        "多 worker/多实例前接入 Redis 等共享计数存储，并在网关层再做一层限流",
        warn_only=True,
    )


def check_https(config, *, production: bool) -> CheckResult:
    base_url = str(getattr(config, "PUBLIC_BASE_URL", "") or "")
    name = "对外访问协议"
    parsed = urlparse(base_url)
    if parsed.scheme == "https" and parsed.hostname:
        return CheckResult(name, PASS, base_url)
    return _result(
        name,
        False,
        f"PUBLIC_BASE_URL={base_url or '（空）'}，不是可用的 HTTPS 地址",
        "设置 MEDITOUR_PUBLIC_BASE_URL=https://你的域名，并在反代终止 TLS",
        warn_only=not production,
    )


def check_mail_backend(config, *, production: bool) -> CheckResult:
    backend = str(getattr(config, "MAIL_BACKEND", "") or "").lower()
    name = "邮件后端"
    if backend == "smtp":
        return CheckResult(name, PASS, "smtp")
    return _result(
        name,
        False,
        f"MAIL_BACKEND={backend or '（空）'}，生产环境不会真正发出验证/重置邮件",
        "设置 MEDITOUR_MAIL_BACKEND=smtp 并配置 SMTP_*",
        warn_only=not production,
    )


def check_storage_backend(config, *, production: bool) -> CheckResult:
    backend = str(getattr(config, "STORAGE_BACKEND", "") or "").lower()
    name = "上传存储"
    if backend != "local":
        return CheckResult(name, PASS, backend or "未配置")
    return _result(
        name,
        False,
        "local：文件只落在本机磁盘，多实例部署时各节点看不到彼此的上传",
        "多实例上线前切换共享对象存储（当前 s3 后端仍是预留位）",
        warn_only=True,
    )


def check_environment(config, *, production: bool) -> CheckResult:
    environment = str(getattr(config, "ENVIRONMENT", "") or "").lower()
    name = "运行环境标记"
    if not production:
        return CheckResult(name, PASS, f"ENVIRONMENT={environment or '未设置'}（未按生产断言）")
    if environment == "production":
        return CheckResult(name, PASS, "ENVIRONMENT=production")
    return CheckResult(
        name,
        WARN,
        f"ENVIRONMENT={environment or '未设置'}，但正在按生产断言",
        "设置 MEDITOUR_ENV=production，让文档/指标等默认值切到生产形态",
    )


def check_all(config, *, production: bool = False) -> list[CheckResult]:
    checks = (
        check_secret_key,
        check_docs,
        check_cors,
        check_metrics,
        check_demo_flags,
        check_email_verification,
        check_database,
        check_rate_limit_backend,
        check_https,
        check_mail_backend,
        check_storage_backend,
        check_environment,
    )
    return [check(config, production=production) for check in checks]


def _print_results(results: list[CheckResult], *, production: bool) -> None:
    mode = "生产断言" if production else "只报告"
    print(f"MediTour 上线配置自检（{mode}）\n")
    for result in results:
        print(f"[{result.status}] {result.name}: {result.detail}")
        if result.fix and result.status != PASS:
            print(f"       修复：{result.fix}")
    failures = [item for item in results if item.status == FAIL]
    warnings = [item for item in results if item.status == WARN]
    print(
        f"\n结果：{len(results) - len(failures) - len(warnings)} 通过 / "
        f"{len(warnings)} 警告 / {len(failures)} 失败"
    )
    if failures:
        print("结论：不达标" + ("（退出码 1）" if production else "（未按生产断言，退出码 0）"))
        return
    print("结论：达标")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="上线前配置自检")
    parser.add_argument(
        "--production",
        action="store_true",
        help="按生产标准断言：存在 FAIL 时退出码为 1",
    )
    args = parser.parse_args(argv)

    try:
        from app.config import settings
    except Exception as exc:  # 缺密钥等启动期错误也要给出可读结论
        print(f"[FAIL] 配置加载失败: {exc}")
        print("\n修复：先补齐 backend/.env 或环境变量（至少 MEDITOUR_SECRET_KEY）")
        return 1 if args.production else 0

    results = check_all(settings, production=args.production)
    _print_results(results, production=args.production)
    if args.production and any(item.status == FAIL for item in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
