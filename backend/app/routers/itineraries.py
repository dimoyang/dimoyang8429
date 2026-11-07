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


@router.get("", response_model=list[ItineraryResponse])
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


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
def get_itinerary(
    itinerary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Itinerary:
    return _get_owned(itinerary_id, db, current_user)


@router.post(
    "", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED
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


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
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
    "/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT
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
