"""员工侧订单路由：查看全部订单并推进运营状态。

员工可以查看全部订单，而不是只看「与自己无关」的订单：系统当前没有
派单/归属字段，客服需要处理任意客户发起的订单。若后续引入归属，
应在此处增加过滤条件而不是靠前端隐藏。
"""

import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import require_staff
from app.models import AuditLog, Booking, User
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


@router.get("/bookings", response_model=StaffBookingPage)
def list_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return StaffBookingPage(
        items=[StaffBookingListItem.model_validate(item) for item in bookings],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/bookings/{booking_id}", response_model=StaffBookingDetail)
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
    "/bookings/{booking_id}/status", response_model=StaffBookingDetail
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
