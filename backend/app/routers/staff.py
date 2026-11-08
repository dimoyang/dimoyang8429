"""员工侧路由：订单列表/详情/状态流转，以及审计日志查询。

员工可以查看全部订单，而不是只看「与自己无关」的订单：系统当前没有
派单/归属字段，客服需要处理任意客户发起的订单。若后续引入归属，
应在此处增加过滤条件而不是靠前端隐藏。
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.audit import record_audit
from app.database import get_db
from app.deps import require_staff
from app.models import AuditLog, Booking, User, utcnow
from app.pagination import PageParams, pagination
from app.schemas import (
    AuditLogItem,
    AuditLogPage,
    BookingStatusUpdate,
    StaffBookingDetail,
    StaffBookingListItem,
    StaffBookingPage,
    StaffRevenueByCurrency,
    StaffStatsOverview,
    StaffStatusStat,
    StaffTrendPoint,
)

router = APIRouter(prefix="/staff", tags=["staff"])

# 状态机：completed / cancelled 是终态，不在表里出现即不可再流转。
# 员工可以取消 pending 或 confirmed（例如用户来电要求取消），
# 但不能把 completed 退回 pending，也不能复活已取消订单。
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"completed", "cancelled"},
}

# 目标状态对应的落地时间戳字段。
STATUS_TIMESTAMP_FIELDS = {
    "confirmed": "confirmed_at",
    "completed": "completed_at",
    "cancelled": "cancelled_at",
}


def _get_booking(db: Session, booking_id: int) -> Booking:
    booking = db.scalar(
        select(Booking)
        .options(joinedload(Booking.package))
        .where(Booking.id == booking_id)
    )
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
        )
    return booking


@router.get(
    "/bookings",
    response_model=StaffBookingPage,
    summary="员工订单列表（分页）",
    description=(
        "需要 `staff` 角色（否则 403）。分页 `page`（≥1）与 `page_size`"
        "（默认 20，上限 100），可按 `status` 过滤。联系方式返回打码值，"
        "且不返回备注；需要完整信息请进入详情接口。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "分页参数越界或 status 不在允许集合内"},
    },
)
def list_bookings(
    paging: PageParams = Depends(pagination),
    status_filter: Literal["pending", "confirmed", "completed", "cancelled"] | None = Query(
        None, alias="status", description="按订单状态过滤"
    ),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> StaffBookingPage:
    """订单列表：默认只返回打码后的联系方式，且不含备注。"""
    count_stmt = select(func.count()).select_from(Booking)
    bookings_stmt = select(Booking).options(joinedload(Booking.package))
    if status_filter is not None:
        count_stmt = count_stmt.where(Booking.status == status_filter)
        bookings_stmt = bookings_stmt.where(Booking.status == status_filter)

    total = db.scalar(count_stmt) or 0
    bookings = db.scalars(
        bookings_stmt.order_by(
            Booking.created_at.desc(), Booking.id.desc()
        )
        .offset(paging.offset)
        .limit(paging.page_size)
    ).all()

    return StaffBookingPage(
        items=[StaffBookingListItem.model_validate(item) for item in bookings],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
        pages=paging.pages(total),
    )


@router.get(
    "/bookings/{booking_id}",
    response_model=StaffBookingDetail,
    summary="员工订单详情（记录审计）",
    description=(
        "需要 `staff` 角色。返回完整联系方式与备注，并向 `audit_logs` 写入"
        "操作者、时间、动作与订单 id；列表访问不写审计。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "订单不存在"},
    },
)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> Booking:
    """订单详情：返回完整联系方式与备注，并写入敏感数据访问审计。"""
    booking = _get_booking(db, booking_id)
    record_audit(
        db,
        actor=staff,
        action="booking.view",
        entity_type="booking",
        entity_id=booking.id,
    )
    # 审计与读取同事务提交：写不进去就不返回敏感数据，避免出现无记录的访问。
    db.commit()
    db.refresh(booking)
    return booking


@router.patch(
    "/bookings/{booking_id}/status",
    response_model=StaffBookingDetail,
    summary="员工流转订单状态",
    description=(
        "需要 `staff` 角色。允许 `pending -> confirmed|cancelled`、"
        "`confirmed -> completed|cancelled`；请求体 `status` 仅接受 "
        "confirmed/completed/cancelled。completed 与 cancelled 为终态，"
        "再次流转（含把 completed 退回 pending）返回 409；"
        "不存在的目标状态值返回 422。成功流转会写入对应时间戳与审计。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "订单不存在"},
        409: {"description": "当前状态不允许该流转（含已完成/已取消订单）"},
        422: {"description": "status 不是 confirmed/completed/cancelled"},
    },
)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> Booking:
    """流转订单状态；非法流转返回 409，不存在的订单返回 404。"""
    booking = _get_booking(db, booking_id)
    old_status = booking.status
    allowed = ALLOWED_TRANSITIONS.get(old_status, set())

    if payload.status not in allowed:
        if old_status in {"completed", "cancelled"}:
            detail = (
                f"Booking is already {old_status} and cannot be changed "
                "(terminal state)"
            )
        else:
            detail = (
                f"Cannot change booking status from {old_status} "
                f"to {payload.status}"
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=detail
        )

    # 带上 old_status 作为条件，避免两个员工同时操作时后到的请求覆盖结果。
    values: dict = {
        "status": payload.status,
        STATUS_TIMESTAMP_FIELDS[payload.status]: utcnow(),
    }
    result = db.execute(
        update(Booking)
        .where(Booking.id == booking_id, Booking.status == old_status)
        .values(**values)
    )
    if result.rowcount == 0:
        db.rollback()
        current = _get_booking(db, booking_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Booking status changed concurrently to {current.status}; "
                "reload and retry"
            ),
        )

    record_audit(
        db,
        actor=staff,
        action="booking.status_change",
        entity_type="booking",
        entity_id=booking_id,
        before={"status": old_status},
        after={"status": payload.status},
    )
    db.commit()
    db.refresh(booking)
    return booking


def _naive_utc(value: datetime) -> datetime:
    """把查询参数统一成数据库里的 naive UTC；无时区按 UTC 解释。"""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


STATS_MAX_DAYS = 90
STATUS_ORDER = ("pending", "confirmed", "completed", "cancelled")


def _stats_range(
    date_from: date | None, date_to: date | None
) -> tuple[date, date]:
    """默认最近 14 天（含今天），按 UTC 日期解释，最长 90 天。"""
    end = date_to or datetime.now(timezone.utc).date()
    start = date_from or (end - timedelta(days=13))
    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must be earlier than or equal to date_to",
        )
    if (end - start).days >= STATS_MAX_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"date range must not exceed {STATS_MAX_DAYS} days",
        )
    return start, end


@router.get(
    "/stats/overview",
    response_model=StaffStatsOverview,
    summary="员工概览统计",
    description=(
        "需要 `staff` 角色。全量返回订单总数与各状态分布；"
        "`date_from` / `date_to`（含边界，按 UTC 日期解释）限定成交金额与"
        "逐日趋势，默认最近 14 天，最长 90 天。成交金额按币种分组，"
        "完成时间取 `completed_at`；迁移前缺失该字段的历史订单回退用 `created_at`。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "日期范围颠倒或超过 90 天"},
    },
)
def get_stats_overview(
    date_from: date | None = Query(None, description="起始日期（含，UTC）"),
    date_to: date | None = Query(None, description="结束日期（含，UTC）"),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> StaffStatsOverview:
    """订单总数、状态分布、区间成交金额与逐日趋势。"""
    start_date, end_date = _stats_range(date_from, date_to)
    start_dt = datetime.combine(start_date, time.min)
    # 用「次日零点」做开区间，避免 last microsecond 的边界遗漏。
    end_dt = datetime.combine(end_date + timedelta(days=1), time.min)

    total_bookings = db.scalar(select(func.count()).select_from(Booking)) or 0

    # 状态分布只做计数，走 (status, created_at) 覆盖索引，无需回表取金额。
    status_rows = db.execute(
        select(Booking.status, func.count()).group_by(Booking.status)
    ).all()
    by_status: dict[str, int] = {name: 0 for name in STATUS_ORDER}
    for name, count in status_rows:
        by_status[name] = int(count)
    ordered_statuses = list(STATUS_ORDER) + sorted(
        set(by_status) - set(STATUS_ORDER)
    )
    status_counts = [
        StaffStatusStat(status=name, count=by_status[name])
        for name in ordered_statuses
    ]

    # 迁移前的历史订单可能没有 completed_at；先探测是否存在，
    # 没有就跳过两条回退查询，避免每次都在旧时间范围里白扫一遍。
    has_legacy_completed = (
        db.scalar(
            select(Booking.id)
            .where(
                Booking.status == "completed",
                Booking.completed_at.is_(None),
            )
            .limit(1)
        )
        is not None
    )

    # 成交金额：优先 completed_at；迁移前该列为空的历史订单回退 created_at。
    revenue: dict[str, list[float]] = {}
    revenue_rows = [
        db.execute(
            select(
                Booking.currency,
                func.count(),
                func.coalesce(func.sum(Booking.total_price), 0.0),
            )
            .where(
                Booking.status == "completed",
                Booking.completed_at >= start_dt,
                Booking.completed_at < end_dt,
            )
            .group_by(Booking.currency)
        ).all()
    ]
    if has_legacy_completed:
        revenue_rows.append(
            db.execute(
                select(
                    Booking.currency,
                    func.count(),
                    func.coalesce(func.sum(Booking.total_price), 0.0),
                )
                .where(
                    Booking.status == "completed",
                    Booking.completed_at.is_(None),
                    Booking.created_at >= start_dt,
                    Booking.created_at < end_dt,
                )
                .group_by(Booking.currency)
            ).all()
        )
    for rows in revenue_rows:
        for currency, orders, amount in rows:
            bucket = revenue.setdefault(currency, [0, 0.0])
            bucket[0] += int(orders)
            bucket[1] += float(amount or 0.0)
    revenue_items = [
        StaffRevenueByCurrency(
            currency=currency,
            orders=int(bucket[0]),
            amount=round(bucket[1], 2),
        )
        for currency, bucket in sorted(revenue.items())
    ]

    # 趋势：三条按日聚合查询（新建 / 完成 / 迁移前完成回退），
    # 日期范围已由 created_at / completed_at 索引先裁剪，再按日分组。
    created_rows = db.execute(
        select(func.date(Booking.created_at), func.count())
        .where(Booking.created_at >= start_dt, Booking.created_at < end_dt)
        .group_by(func.date(Booking.created_at))
    ).all()
    created_by_day = {day: int(count) for day, count in created_rows}

    completed_by_day: dict[str, list[float]] = {}
    for day, count, amount in db.execute(
        select(
            func.date(Booking.completed_at),
            func.count(),
            func.coalesce(func.sum(Booking.total_price), 0.0),
        )
        .where(
            Booking.status == "completed",
            Booking.completed_at >= start_dt,
            Booking.completed_at < end_dt,
        )
        .group_by(func.date(Booking.completed_at))
    ).all():
        bucket = completed_by_day.setdefault(day, [0, 0.0])
        bucket[0] += int(count)
        bucket[1] += float(amount or 0.0)
    if has_legacy_completed:
        for day, count, amount in db.execute(
            select(
                func.date(Booking.created_at),
                func.count(),
                func.coalesce(func.sum(Booking.total_price), 0.0),
            )
            .where(
                Booking.status == "completed",
                Booking.completed_at.is_(None),
                Booking.created_at >= start_dt,
                Booking.created_at < end_dt,
            )
            .group_by(func.date(Booking.created_at))
        ).all():
            bucket = completed_by_day.setdefault(day, [0, 0.0])
            bucket[0] += int(count)
            bucket[1] += float(amount or 0.0)

    trend: list[StaffTrendPoint] = []
    cursor = start_date
    while cursor <= end_date:
        key = cursor.isoformat()
        completed = completed_by_day.get(key, [0, 0.0])
        trend.append(
            StaffTrendPoint(
                date=cursor,
                created=created_by_day.get(key, 0),
                completed=int(completed[0]),
                revenue=round(completed[1], 2),
            )
        )
        cursor += timedelta(days=1)

    return StaffStatsOverview(
        generated_at=utcnow(),
        total_bookings=int(total_bookings),
        status_counts=status_counts,
        revenue_from=start_date,
        revenue_to=end_date,
        revenue=revenue_items,
        trend=trend,
    )


@router.get(
    "/audit-logs",
    response_model=AuditLogPage,
    summary="审计日志查询（分页）",
    description=(
        "需要 `staff` 角色。可按 `action`（精确匹配）、`entity_type`、"
        "`entity_id`、`actor_user_id` 与时间范围过滤；`created_from` / "
        "`created_to` 为 ISO 8601，含边界，无时区按 UTC 解释。"
        "按时间倒序返回，`details` 内含变更前后快照。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "时间范围颠倒或分页参数越界"},
    },
)
def list_audit_logs(
    paging: PageParams = Depends(pagination),
    action: str | None = Query(None, max_length=60, description="操作类型，精确匹配"),
    entity_type: str | None = Query(None, max_length=40),
    entity_id: str | None = Query(None, max_length=64),
    actor_user_id: int | None = Query(None, ge=1),
    created_from: datetime | None = Query(None, description="起始时间（含）"),
    created_to: datetime | None = Query(None, description="结束时间（含）"),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> AuditLogPage:
    """按操作类型与时间范围查询审计记录。"""
    if (
        created_from is not None
        and created_to is not None
        and _naive_utc(created_from) > _naive_utc(created_to)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="created_from must be earlier than or equal to created_to",
        )

    conditions = []
    if action is not None:
        conditions.append(AuditLog.action == action)
    if entity_type is not None:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        conditions.append(AuditLog.entity_id == entity_id)
    if actor_user_id is not None:
        conditions.append(AuditLog.actor_user_id == actor_user_id)
    if created_from is not None:
        conditions.append(AuditLog.created_at >= _naive_utc(created_from))
    if created_to is not None:
        conditions.append(AuditLog.created_at <= _naive_utc(created_to))

    count_stmt = select(func.count()).select_from(AuditLog)
    items_stmt = select(AuditLog)
    for condition in conditions:
        count_stmt = count_stmt.where(condition)
        items_stmt = items_stmt.where(condition)

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        items_stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(paging.offset)
        .limit(paging.page_size)
    ).all()

    return AuditLogPage(
        items=[AuditLogItem.model_validate(item) for item in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
        pages=paging.pages(total),
    )
