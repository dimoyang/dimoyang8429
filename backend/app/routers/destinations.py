"""目的地路由：列表、关键词搜索与详情。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Destination
from app.schemas import DestinationResponse

router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("", response_model=list[DestinationResponse])
def list_destinations(
    query: str | None = Query(None, max_length=120),
    db: Session = Depends(get_db),
) -> list[Destination]:
    stmt = select(Destination).order_by(Destination.sort_order, Destination.id)
    if query and query.strip():
        like = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Destination.name.like(like),
                Destination.name_en.like(like),
                Destination.tagline.like(like),
            )
        )
    return list(db.scalars(stmt).all())


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(
    destination_id: str,
    db: Session = Depends(get_db),
) -> Destination:
    destination = db.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found",
        )
    return destination
