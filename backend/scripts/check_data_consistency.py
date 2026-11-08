#!/usr/bin/env python3
"""只读数据一致性巡检。

输出分两类：

- **确定异常**：违反当前数据模型的不变量，通常意味着某条写入路径漏了校验，
  或有人直接改了数据库，需要立即处理。
- **需人工判断**：可能是正常业务结果（例如订单金额是下单时的快照、迁移前的
  历史行没有状态时间戳），需要运营确认，不一定是 bug。

脚本只执行 SELECT，不修改任何数据。

用法（需要 MEDITOUR_SECRET_KEY，与其它脚本一致）：

    python scripts/check_data_consistency.py
    python scripts/check_data_consistency.py --max-examples 10
    python scripts/check_data_consistency.py --database-url sqlite:///./meditour.db

退出码：存在确定异常时返回 1（便于接入定时任务），否则返回 0。
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuthSession,
    Booking,
    Destination,
    Itinerary,
    ItineraryDay,
    MedicalPackage,
    User,
    utcnow,
)

DEFINITE = "确定异常"
REVIEW = "需人工判断"


def _count_and_examples(session: Session, stmt, render, limit: int):
    """返回 (总数, 示例行)。stmt 必须是 SELECT 语句。"""
    count = session.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0
    rows = session.execute(stmt.limit(limit)).all()
    return count, [render(row) for row in rows]


def check_booking_missing_package(session: Session, limit: int):
    stmt = (
        select(Booking.id, Booking.package_id, Booking.order_no)
        .outerjoin(
            MedicalPackage, Booking.package_id == MedicalPackage.id
        )
        .where(MedicalPackage.id.is_(None))
        .order_by(Booking.id)
    )
    return _count_and_examples(
        session,
        stmt,
        lambda row: f"order {row.order_no} (#{row.id}) -> package #{row.package_id} 不存在",
        limit,
    )


def _missing_destinations(session: Session, model, id_column, label: str, limit: int):
    existing = set(session.scalars(select(Destination.id)).all())
    rows = session.execute(select(model.id, id_column)).all()
    missing = []
    for row_id, destination_ids in rows:
        unknown = [
            destination_id
            for destination_id in (destination_ids or [])
            if destination_id not in existing
        ]
        if unknown:
            missing.append(
                f"{label} #{row_id} -> 不存在的目的地 {', '.join(unknown)}"
            )
    return len(missing), missing[:limit]


def check_itinerary_missing_destination(session: Session, limit: int):
    return _missing_destinations(
        session, Itinerary, Itinerary.destination_ids, "itinerary", limit
    )


def check_itinerary_day_missing_destination(session: Session, limit: int):
    return _missing_destinations(
        session,
        ItineraryDay,
        ItineraryDay.destination_ids,
        "itinerary_day",
        limit,
    )


def check_duplicate_pending(session: Session, limit: int):
    stmt = (
        select(
            Booking.user_id,
            Booking.package_id,
            Booking.appointment_date,
            func.count().label("total"),
        )
        .where(Booking.status == "pending")
        .group_by(
            Booking.user_id, Booking.package_id, Booking.appointment_date
        )
        .having(func.count() > 1)
        .order_by(Booking.user_id, Booking.package_id)
    )
    return _count_and_examples(
        session,
        stmt,
        lambda row: (
            f"user #{row.user_id} + package #{row.package_id} + "
            f"{row.appointment_date} 有 {row.total} 条 pending"
        ),
        limit,
    )


def check_soft_deleted_with_active_session(session: Session, limit: int):
    now = utcnow()
    stmt = (
        select(AuthSession.id, AuthSession.user_id, AuthSession.expires_at)
        .join(User, User.id == AuthSession.user_id)
        .where(
            User.deleted_at.is_not(None),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.id)
    )
    return _count_and_examples(
        session,
        stmt,
        lambda row: (
            f"session #{row.id} 属于已软删除用户 #{row.user_id}，"
            f"但未吊销且 {row.expires_at} 才过期"
        ),
        limit,
    )


def check_status_timestamp_conflicts(session: Session, limit: int):
    """状态与时间戳互斥字段同时存在：任何版本都不可能出现。"""
    conditions = {
        "pending": (
            Booking.confirmed_at.is_not(None)
            | Booking.cancelled_at.is_not(None)
            | Booking.completed_at.is_not(None)
        ),
        "confirmed": (
            Booking.cancelled_at.is_not(None)
            | Booking.completed_at.is_not(None)
        ),
        "completed": Booking.cancelled_at.is_not(None),
        "cancelled": Booking.completed_at.is_not(None),
    }
    examples: list[str] = []
    total = 0
    for status_value, condition in conditions.items():
        stmt = select(Booking.id, Booking.order_no).where(
            Booking.status == status_value, condition
        )
        count, rows = _count_and_examples(
            session,
            stmt,
            lambda row: (
                f"order {row.order_no} (#{row.id}) 状态 {status_value} "
                "却带有其它状态的时间戳"
            ),
            limit,
        )
        total += count
        examples.extend(rows)
    return total, examples[:limit]


def check_status_timestamp_missing(session: Session, limit: int):
    """已进入某状态的订单缺少对应时间戳。

    迁移前的历史订单无法回溯真实时刻，因此归入“需人工判断”。
    """
    pairs = (
        ("confirmed", Booking.confirmed_at, "confirmed_at"),
        ("completed", Booking.completed_at, "completed_at"),
        ("cancelled", Booking.cancelled_at, "cancelled_at"),
    )
    examples: list[str] = []
    total = 0
    for status_value, column, field in pairs:
        stmt = select(Booking.id, Booking.order_no, Booking.created_at).where(
            Booking.status == status_value, column.is_(None)
        )
        count, rows = _count_and_examples(
            session,
            stmt,
            lambda row: (
                f"order {row.order_no} (#{row.id}) 状态 {status_value} "
                f"但 {field} 为空（创建于 {row.created_at}）"
            ),
            limit,
        )
        total += count
        examples.extend(rows)
    return total, examples[:limit]


def check_price_snapshot_diff(session: Session, limit: int):
    """订单金额与套餐当前价格不一致。价格快照是设计，通常不是异常。"""
    stmt = (
        select(
            Booking.id,
            Booking.order_no,
            Booking.total_price,
            MedicalPackage.price,
            MedicalPackage.name,
        )
        .join(MedicalPackage, Booking.package_id == MedicalPackage.id)
        .where(func.abs(Booking.total_price - MedicalPackage.price) > 0.001)
        .order_by(Booking.id)
    )
    return _count_and_examples(
        session,
        stmt,
        lambda row: (
            f"order {row.order_no} (#{row.id}) 快照 {row.total_price} "
            f"vs 套餐当前 {row.price}（{row.name}）"
        ),
        limit,
    )


def check_overdue_pending(session: Session, limit: int):
    stmt = (
        select(Booking.id, Booking.order_no, Booking.appointment_date)
        .where(
            Booking.status == "pending",
            Booking.appointment_date < utcnow(),
        )
        .order_by(Booking.appointment_date)
    )
    return _count_and_examples(
        session,
        stmt,
        lambda row: (
            f"order {row.order_no} (#{row.id}) 预约时间 "
            f"{row.appointment_date} 已过但仍为 pending"
        ),
        limit,
    )


def check_pending_on_inactive_package(session: Session, limit: int):
    stmt = (
        select(
            Booking.id, Booking.order_no, MedicalPackage.name
        )
        .join(MedicalPackage, Booking.package_id == MedicalPackage.id)
        .where(
            Booking.status == "pending",
            MedicalPackage.is_active.is_(False),
        )
        .order_by(Booking.id)
    )
    return _count_and_examples(
        session,
        stmt,
        lambda row: (
            f"order {row.order_no} (#{row.id}) 为 pending，"
            f"但套餐 {row.name} 已下架"
        ),
        limit,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="只读数据一致性巡检")
    parser.add_argument(
        "--database-url",
        default=None,
        help="覆盖 DATABASE_URL（默认读取后端配置）",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=5,
        help="每类最多打印的示例条数（默认 5）",
    )
    args = parser.parse_args()

    limit = max(1, args.max_examples)
    if args.database_url:
        session = Session(create_engine(args.database_url))
        database_url = args.database_url
    else:
        session = SessionLocal()
        database_url = settings.DATABASE_URL

    print("== 数据一致性巡检（只读） ==")
    print(f"数据库: {database_url}")
    print(f"时间(UTC): {utcnow().isoformat(timespec='seconds')}")
    print()

    definite_checks = [
        ("订单引用不存在的套餐", check_booking_missing_package),
        ("行程引用不存在的目的地", check_itinerary_missing_destination),
        ("行程每日安排引用不存在的目的地", check_itinerary_day_missing_destination),
        ("同一时段存在多条 pending 订单", check_duplicate_pending),
        ("软删除账号仍有有效会话", check_soft_deleted_with_active_session),
        ("订单状态与时间戳互相矛盾", check_status_timestamp_conflicts),
    ]
    review_checks = [
        ("订单状态缺少对应时间戳（迁移前历史数据无法回溯）", check_status_timestamp_missing),
        ("订单金额与套餐当前价格不一致（价格快照属正常）", check_price_snapshot_diff),
        ("预约时间已过但仍是 pending", check_overdue_pending),
        ("套餐已下架但仍有 pending 订单", check_pending_on_inactive_package),
    ]

    try:
        definite_total = 0
        for label, check in definite_checks:
            count, examples = check(session, limit)
            definite_total += count
            print(f"[{DEFINITE}] {label}: {count} 条")
            for example in examples:
                print(f"    - {example}")

        review_total = 0
        for label, check in review_checks:
            count, examples = check(session, limit)
            review_total += count
            print(f"[{REVIEW}] {label}: {count} 条")
            for example in examples:
                print(f"    - {example}")
    finally:
        session.close()

    print()
    print(f"汇总: 确定异常 {definite_total} 条，需人工判断 {review_total} 条")
    if definite_total:
        print("结论: 存在确定异常，请优先处理。")
        return 1
    print("结论: 未发现确定异常。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
