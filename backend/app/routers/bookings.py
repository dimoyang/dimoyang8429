"""预约路由：创建订单与我的订单。"""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Booking, MedicalPackage, User
from app.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


DUPLICATE_PENDING_DETAIL = (
    "A pending booking for this package and date already exists"
)


def _generate_order_no() -> str:
    return f"MT{datetime.now():%Y%m%d%H%M%S}{secrets.token_hex(3).upper()}"


@router.post(
    "/",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建预约订单",
    description=(
        "需要 Bearer access token。金额只由服务端按套餐计算，客户端传入的价格会被忽略。"
        "同一用户对同一套餐、同一预约时间只允许一个 pending 订单。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        404: {"description": "套餐不存在"},
        409: {"description": "同一套餐与预约时间已存在待处理订单"},
        422: {"description": "预约时间、联系方式或需要项校验失败"},
    },
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
    if not package.is_active:
        # 下架套餐对用户不可见，因此同样按 404 处理，避免暴露其存在。
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical package is not available for booking",
        )

    # 同一用户对同一套餐、同一预约时间只允许存在一个待处理订单。
    # 精确到秒级预约时间意味着不同日期的正常预约不受影响。
    slot = (
        Booking.user_id == current_user.id,
        Booking.package_id == package.id,
        Booking.appointment_date == payload.appointment_date,
        Booking.status == "pending",
    )
    if db.scalar(select(Booking).where(*slot)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DUPLICATE_PENDING_DETAIL,
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
    try:
        db.commit()
    except IntegrityError:
        # 并发兜底：查重与插入不是原子操作，部分唯一索引
        # uq_bookings_pending_slot 只允许一个请求成功，其余在这里转成 409。
        db.rollback()
        if db.scalar(select(Booking).where(*slot)) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=DUPLICATE_PENDING_DETAIL,
            )
        raise
    db.refresh(booking)
    return booking


@router.get(
    "/",
    response_model=list[BookingResponse],
    summary="我的订单列表（裸数组）",
    description=(
        "需要 Bearer access token。只返回当前用户自己的订单，按 id 倒序。"
        "为兼容 Flutter 现有契约保持裸数组，不套 `{items: ...}` 分页外层。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
    },
)
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


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="取消自己的待处理订单",
    description=(
        "需要 Bearer access token。仅允许 `pending -> cancelled`；"
        "订单不存在或属于他人统一按 404 处理，避免泄露他人订单是否存在。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        404: {"description": "订单不存在或不属于当前用户"},
        409: {"description": "订单当前状态不是 pending"},
    },
)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    """取消自己的待处理订单；仅允许 pending -> cancelled。"""
    booking = db.scalar(
        select(Booking)
        .options(joinedload(Booking.package))
        .where(Booking.id == booking_id, Booking.user_id == current_user.id)
    )
    if booking is None:
        # 不区分“不存在”和“属于别人”，避免泄露他人订单是否存在。
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )
    # 条件更新让「检查状态 + 改状态」在数据库层不可分割：
    # 只有第一个请求能命中 status='pending'，并发请求的 rowcount 为 0。
    result = db.execute(
        update(Booking)
        .where(
            Booking.id == booking_id,
            Booking.user_id == current_user.id,
            Booking.status == "pending",
        )
        .values(status="cancelled")
    )
    if result.rowcount == 0:
        db.rollback()
        # 回查区分「不存在/非本人」（404）与「状态已变」（409）。
        current = db.scalar(
            select(Booking).where(
                Booking.id == booking_id,
                Booking.user_id == current_user.id,
            )
        )
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found",
            )
        # 请求本身合法，但与资源当前状态冲突，因此用 409 而不是 422。
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only pending bookings can be cancelled (current status: {current.status})",
        )

    db.commit()
    db.refresh(booking)
    return booking
