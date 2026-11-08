"""员工侧订单路由：查看全部订单并推进运营状态。

员工可以查看全部订单，而不是只看「与自己无关」的订单：系统当前没有
派单/归属字段，客服需要处理任意客户发起的订单。若后续引入归属，
应在此处增加过滤条件而不是靠前端隐藏。
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_staff
from app.models import AuditLog, Booking, User
from app.pagination import PageParams, pagination
from app.schemas import (
    BookingStatusUpdate,
    StaffBookingDetail,
    StaffBookingListItem,
    StaffBookingPage,
)

router = APIRouter(prefix="/staff", tags=["staff"])

# 只允许前进：pending -> confirmed -> completed。取消仍由用户侧接口完成。
ALLOWED_TRANSITIONS = {"pending": "confirmed", "confirmed": "completed"}


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
    db.add(
        AuditLog(
            actor_user_id=staff.id,
            actor_email=staff.email,
            action="booking.view",
            entity_type="booking",
            entity_id=booking.id,
        )
    )
    # 审计与读取同事务提交：写不进去就不返回敏感数据，避免出现无记录的访问。
    db.commit()
    db.refresh(booking)
    return booking


@router.patch(
    "/bookings/{booking_id}/status",
    response_model=StaffBookingDetail,
    summary="员工推进订单状态",
    description=(
        "需要 `staff` 角色。只允许 `pending -> confirmed`、"
        "`confirmed -> completed`；请求体 `status` 仅接受 confirmed/completed。"
        "跳过中间状态或对已结束订单再流转返回 409。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "订单不存在"},
        409: {"description": "当前状态不允许该流转（含已完成/已取消订单）"},
        422: {"description": "status 不是 confirmed/completed"},
    },
)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Booking:
    """推进订单状态；非法流转返回 409，不存在的订单返回 404。"""
    booking = _get_booking(db, booking_id)

    next_status = ALLOWED_TRANSITIONS.get(booking.status)
    if next_status is None or payload.status != next_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot change booking status from {booking.status} "
                f"to {payload.status}"
            ),
        )

    booking.status = next_status
    db.commit()
    db.refresh(booking)
    return booking
