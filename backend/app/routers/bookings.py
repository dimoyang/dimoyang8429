"""预约路由：创建订单与我的订单。"""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Booking, MedicalPackage, User
from app.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _generate_order_no() -> str:
    return f"MT{datetime.now():%Y%m%d%H%M%S}{secrets.token_hex(3).upper()}"


@router.post(
    "/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED
)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    package = db.get(MedicalPackage, payload.package_id)
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical package not found",
        )

    # 同一用户对同一套餐、同一预约时间只允许存在一个待处理订单。
    # 精确到秒级预约时间意味着不同日期的正常预约不受影响。
    duplicate = db.scalar(
        select(Booking).where(
            Booking.user_id == current_user.id,
            Booking.package_id == package.id,
            Booking.appointment_date == payload.appointment_date,
            Booking.status == "pending",
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending booking for this package and date already exists",
        )

    booking = Booking(
        order_no=_generate_order_no(),
        user_id=current_user.id,
        package_id=package.id,
        package=package,
        appointment_date=payload.appointment_date,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        notes=payload.notes,
        need_translator=payload.need_translator,
        need_accommodation=payload.need_accommodation,
        need_pickup=payload.need_pickup,
        # 金额只由服务端按套餐计算，忽略任何客户端传入的价格。
        total_price=package.price,
        currency=package.currency or settings.DEFAULT_CURRENCY,
        status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/", response_model=list[BookingResponse])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .options(joinedload(Booking.package))
            .where(Booking.user_id == current_user.id)
            .order_by(Booking.id.desc())
        ).all()
    )
