"""医疗服务路由：套餐分页与医院列表。"""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Hospital, MedicalPackage
from app.schemas import HospitalResponse, PackagePage, PackageResponse

router = APIRouter(prefix="/medical", tags=["medical"])


@router.get("/packages", response_model=PackagePage)
def list_packages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PackagePage:
    total = db.scalar(select(func.count()).select_from(MedicalPackage)) or 0
    items = db.scalars(
        select(MedicalPackage)
        .order_by(MedicalPackage.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PackagePage(
        items=[PackageResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/hospitals", response_model=list[HospitalResponse])
def list_hospitals(db: Session = Depends(get_db)) -> list[Hospital]:
    return list(db.scalars(select(Hospital).order_by(Hospital.id)).all())
