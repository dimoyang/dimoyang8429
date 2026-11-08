#!/usr/bin/env python3
"""对列表/过滤/统计查询跑 SQLite `EXPLAIN QUERY PLAN`。

目的不是跑接口，而是确认 SQL 形状能命中索引：不出现全表 `SCAN`，
列表排序不出现 `USE TEMP B-TREE FOR ORDER BY`。

用法（在 backend 目录下执行）：
    .\\.venv\\Scripts\\python.exe scripts\\check_query_plans.py
    .\\.venv\\Scripts\\python.exe scripts\\check_query_plans.py --verbose
    .\\.venv\\Scripts\\python.exe scripts\\check_query_plans.py --strict   # 有疑点时退出码 1

脚本只读：用 sqlite3 打开数据库执行 EXPLAIN，不写入任何数据。
查询语句由 SQLAlchemy 模型编译而来，与路由里的真实查询保持一致；
`--verbose` 会同时打印编译后的 SQL。
"""

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
from sqlalchemy import func, select
from sqlalchemy.dialects import sqlite
from sqlalchemy.sql import Select

from app.models import (
    AuditLog,
    Booking,
    ContentTranslation,
    Itinerary,
    MedicalPackage,
)

load_dotenv(BACKEND_DIR / ".env")

DIALECT = sqlite.dialect()


@dataclass(frozen=True)
class Scenario:
    name: str
    note: str
    statement: Select
    # 端点目前不存在的查询形状：只做参考，不参与失败计数。
    informational: bool = False


def _db_path() -> Path:
    url = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'meditour.db').as_posix()}"
    )
    for prefix in ("sqlite+pysqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            return Path(url[len(prefix) :]).expanduser().resolve()
    raise SystemExit(
        f"该脚本只支持文件型 SQLite，当前 DATABASE_URL={url!r}"
    )


def build_scenarios() -> list[Scenario]:
    now = datetime(2026, 11, 8, 12, 0, 0)
    start = now - timedelta(days=30)
    day_start = (now - timedelta(days=14)).date()

    return [
        Scenario(
            "booking.user_list",
            "用户订单列表：WHERE user_id ORDER BY id DESC（当前路由）",
            select(Booking)
            .where(Booking.user_id == 1)
            .order_by(Booking.id.desc()),
        ),
        Scenario(
            "booking.user_list_status",
            "用户订单按状态过滤：WHERE user_id AND status ORDER BY id DESC",
            select(Booking)
            .where(Booking.user_id == 1, Booking.status == "pending")
            .order_by(Booking.id.desc()),
        ),
        Scenario(
            "booking.staff_list",
            "员工订单列表：无状态过滤，按 created_at 倒序",
            select(Booking)
            .order_by(Booking.created_at.desc(), Booking.id.desc())
            .limit(20),
        ),
        Scenario(
            "booking.staff_list_status",
            "员工订单列表：WHERE status ORDER BY created_at DESC, id DESC",
            select(Booking)
            .where(Booking.status == "confirmed")
            .order_by(Booking.created_at.desc(), Booking.id.desc())
            .limit(20),
        ),
        Scenario(
            "booking.count_status",
            "员工列表总数：COUNT(*) WHERE status",
            select(func.count())
            .select_from(Booking)
            .where(Booking.status == "confirmed"),
        ),
        Scenario(
            "audit.action_time",
            "审计查询：WHERE action AND created_at 范围，按时间倒序",
            select(AuditLog)
            .where(
                AuditLog.action == "booking.view",
                AuditLog.created_at >= start,
                AuditLog.created_at <= now,
            )
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(20),
        ),
        Scenario(
            "audit.action_only",
            "审计查询：只按 action 过滤，按时间倒序",
            select(AuditLog)
            .where(AuditLog.action == "booking.view")
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(20),
        ),
        Scenario(
            "audit.entity",
            "审计查询：WHERE entity_type AND entity_id，按时间倒序",
            select(AuditLog)
            .where(
                AuditLog.entity_type == "booking",
                AuditLog.entity_id == "42",
            )
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(20),
        ),
        Scenario(
            "audit.actor",
            "审计查询：WHERE actor_user_id，按时间倒序",
            select(AuditLog)
            .where(AuditLog.actor_user_id == 7)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(20),
        ),
        Scenario(
            "package.public_list",
            "公开套餐列表：WHERE is_active ORDER BY id LIMIT",
            select(MedicalPackage)
            .where(MedicalPackage.is_active.is_(True))
            .order_by(MedicalPackage.id)
            .limit(20),
        ),
        Scenario(
            "package.count_active",
            "公开套餐总数：COUNT(*) WHERE is_active",
            select(func.count())
            .select_from(MedicalPackage)
            .where(MedicalPackage.is_active.is_(True)),
        ),
        Scenario(
            "package.staff_list_active",
            "员工套餐列表：include_inactive=false",
            select(MedicalPackage)
            .where(MedicalPackage.is_active.is_(True))
            .order_by(MedicalPackage.id)
            .limit(20),
        ),
        Scenario(
            "package.category_active",
            "分类+上下架：WHERE category AND is_active ORDER BY id"
            "（当前端点无服务端分类过滤，前端本地筛选；仅作索引设计参考）",
            select(MedicalPackage)
            .where(
                MedicalPackage.category == "dentistry",
                MedicalPackage.is_active.is_(True),
            )
            .order_by(MedicalPackage.id)
            .limit(20),
            informational=True,
        ),
        Scenario(
            "translation.load",
            "译文批量加载：WHERE entity_type AND entity_id IN AND lang AND field IN",
            select(ContentTranslation).where(
                ContentTranslation.entity_type == "package",
                ContentTranslation.entity_id.in_([1, 2, 3, 4, 5]),
                ContentTranslation.lang == "de",
                ContentTranslation.field.in_(("name", "description")),
            ),
        ),
        Scenario(
            "itinerary.user_list",
            "用户行程列表：WHERE user_id ORDER BY start_date",
            select(Itinerary)
            .where(Itinerary.user_id == 1)
            .order_by(Itinerary.start_date),
        ),
        Scenario(
            "stats.total",
            "统计-订单总数：COUNT(*)",
            select(func.count()).select_from(Booking),
        ),
        Scenario(
            "stats.status_distribution",
            "统计-各状态分布：GROUP BY status（纯计数，覆盖索引）",
            select(Booking.status, func.count()).group_by(Booking.status),
        ),
        Scenario(
            "stats.revenue_range",
            "统计-成交金额：WHERE status AND completed_at 范围，按币种汇总",
            select(
                Booking.currency,
                func.count(),
                func.sum(Booking.total_price),
            )
            .where(
                Booking.status == "completed",
                Booking.completed_at >= start,
                Booking.completed_at < now,
            )
            .group_by(Booking.currency),
        ),
        Scenario(
            "stats.revenue_range_legacy",
            "统计-成交金额（迁移前 completed_at 为空，回退 created_at）",
            select(
                Booking.currency,
                func.count(),
                func.sum(Booking.total_price),
            )
            .where(
                Booking.status == "completed",
                Booking.completed_at.is_(None),
                Booking.created_at >= start,
                Booking.created_at < now,
            )
            .group_by(Booking.currency),
        ),
        Scenario(
            "stats.trend_created",
            "统计-最近趋势：按日 GROUP BY date(created_at)（日期范围已限制）",
            select(
                func.date(Booking.created_at),
                func.count(),
                func.sum(Booking.total_price),
            )
            .where(
                Booking.created_at
                >= datetime.combine(day_start, datetime.min.time())
            )
            .group_by(func.date(Booking.created_at))
            .order_by(func.date(Booking.created_at)),
        ),
    ]


def compile_sql(statement: Select) -> str:
    return str(
        statement.compile(
            dialect=DIALECT, compile_kwargs={"literal_binds": True}
        )
    )


def explain(connection: sqlite3.Connection, sql: str) -> list[str]:
    rows = connection.execute("EXPLAIN QUERY PLAN " + sql).fetchall()
    # 行结构：(id, parent, notused, detail)；detail 已包含层级信息。
    return [row[3] for row in rows]


def judge(plan: list[str]) -> list[str]:
    issues: list[str] = []
    for detail in plan:
        if detail.startswith("SCAN ") and "USING" not in detail:
            issues.append(f"全表扫描: {detail}")
        if "USE TEMP B-TREE FOR ORDER BY" in detail:
            issues.append(f"临时 B 树排序: {detail}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="检查查询计划是否走索引")
    parser.add_argument("--verbose", action="store_true", help="打印 SQL")
    parser.add_argument(
        "--strict", action="store_true", help="存在全表扫描/临时排序时退出码 1"
    )
    args = parser.parse_args()

    db_path = _db_path()
    if not db_path.exists():
        print(f"数据库不存在：{db_path}", file=sys.stderr)
        return 2

    failures = 0
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True) as conn:
        print(f"数据库: {db_path}")
        for scenario in build_scenarios():
            sql = compile_sql(scenario.statement)
            plan = explain(conn, sql)
            issues = judge(plan)
            if issues and not scenario.informational:
                failures += 1
            if scenario.informational:
                status = "INFO"
            else:
                status = "FAIL" if issues else "OK"
            print(f"\n[{status}] {scenario.name} — {scenario.note}")
            if args.verbose:
                print("  SQL: " + " ".join(sql.split()))
            for detail in plan:
                print(f"  - {detail}")
            for issue in issues:
                print(f"  ! {issue}")

    print(f"\n合计: {failures} 条查询存在全表扫描或临时 B 树排序")
    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
