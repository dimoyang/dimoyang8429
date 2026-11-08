"""行程路由：按用户隔离的 CRUD，支持按天安排。"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Itinerary, ItineraryDay, User
from app.schemas import ItineraryResponse, ItineraryWrite

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


def _get_owned(
    itinerary_id: int, db: Session, current_user: User
) -> Itinerary:
    """只暴露当前用户的行程，其他用户的记录统一按 404 处理。"""
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary not found",
        )
    return itinerary


def _build_days(payload: ItineraryWrite) -> list[ItineraryDay]:
    return [
        ItineraryDay(
            day_number=day.day_number,
            destination_ids=list(day.destination_ids),
            notes=day.notes,
        )
        for day in payload.days
    ]


@router.get(
    "",
    response_model=list[ItineraryResponse],
    summary="我的行程列表（裸数组）",
    description=(
        "需要 Bearer access token。只返回当前用户的行程，按出发日期排序。"
        "为兼容 Flutter 契约保持裸数组，不使用分页外层结构。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
    },
)
def list_itineraries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Itinerary]:
    return list(
        db.scalars(
            select(Itinerary)
            .where(Itinerary.user_id == current_user.id)
            .order_by(Itinerary.start_date, Itinerary.id)
        ).all()
    )


@router.get(
    "/{itinerary_id}",
    response_model=ItineraryResponse,
    summary="行程详情",
    description=(
        "需要 Bearer access token。只允许访问当前用户自己的行程；"
        "不存在或属于他人统一返回 404。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        404: {"description": "行程不存在或不属于当前用户"},
    },
)
def get_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Itinerary:
    return _get_owned(itinerary_id, db, current_user)


@router.post(
    "",
    response_model=ItineraryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建行程",
    description=(
        "需要 Bearer access token。结束日期不得早于开始日期，目的地不能为空，"
        "每天编号唯一且不得超过行程天数。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        422: {"description": "日期、目的地或每日安排校验失败"},
    },
)
def create_itinerary(
    payload: ItineraryWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Itinerary:
    itinerary = Itinerary(
        user_id=current_user.id,
        title=payload.title,
        start_date=payload.start_date,
        end_date=payload.end_date,
        destination_ids=list(payload.destination_ids),
        notes=payload.notes,
    )
    itinerary.days = _build_days(payload)
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)
    return itinerary


@router.put(
    "/{itinerary_id}",
    response_model=ItineraryResponse,
    summary="全量更新行程",
    description=(
        "需要 Bearer access token。只允许更新自己的行程，每日安排会被整体替换。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        404: {"description": "行程不存在或不属于当前用户"},
        422: {"description": "日期、目的地或每日安排校验失败"},
    },
)
def update_itinerary(
    itinerary_id: int,
    payload: ItineraryWrite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Itinerary:
    itinerary = _get_owned(itinerary_id, db, current_user)
    itinerary.title = payload.title
    itinerary.start_date = payload.start_date
    itinerary.end_date = payload.end_date
    itinerary.destination_ids = list(payload.destination_ids)
    itinerary.notes = payload.notes
    # 全量替换每日安排，delete-orphan 会清理旧的 day 记录。
    itinerary.days = _build_days(payload)
    db.commit()
    db.refresh(itinerary)
    return itinerary


@router.delete(
    "/{itinerary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除行程",
    description="需要 Bearer access token。只允许删除自己的行程，每日安排级联删除。",
    responses={
        401: {"description": "未登录或令牌无效"},
        404: {"description": "行程不存在或不属于当前用户"},
    },
)
def delete_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    itinerary = _get_owned(itinerary_id, db, current_user)
    db.delete(itinerary)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
