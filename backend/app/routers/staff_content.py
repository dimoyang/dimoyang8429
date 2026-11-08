"""员工侧内容运营：套餐、医院、目的地的增删改查。

与 `app/routers/destinations.py`（公开只读契约）分开，避免员工写接口
污染公开端点的响应结构。所有端点都需要 `staff` 角色。

删除策略：
- 套餐被订单引用、医院被套餐引用、目的地被行程引用时返回 409，
  而不是级联删除业务数据。套餐的常规操作是「下架」而不是删除。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.database import get_db
from app.deps import require_staff
from app.models import (
    Booking,
    Destination,
    Hospital,
    Itinerary,
    ItineraryDay,
    MedicalPackage,
    User,
)
from app.pagination import PageParams, pagination
from app.schemas import (
    DestinationCreate,
    DestinationPage,
    DestinationUpdate,
    HospitalCreate,
    HospitalPage,
    HospitalResponse,
    HospitalUpdate,
    PackageCreate,
    PackagePage,
    PackageResponse,
    PackageUpdate,
    StaffDestinationResponse,
)

router = APIRouter(prefix="/staff", tags=["staff"])


def _get_package(db: Session, package_id: int) -> MedicalPackage:
    package = db.get(MedicalPackage, package_id)
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical package not found",
        )
    return package


def _get_hospital(db: Session, hospital_id: int) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital not found",
        )
    return hospital


def _get_destination(db: Session, destination_id: str) -> Destination:
    destination = db.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found",
        )
    return destination


def _require_hospital_exists(db: Session, hospital_id: int) -> Hospital:
    hospital = db.get(Hospital, hospital_id)
    if hospital is None:
        # 请求体字段引用了不存在的医院，属于语义校验失败。
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown hospital_id: {hospital_id}",
        )
    return hospital


# --------------------------------------------------------------------------
# 套餐
# --------------------------------------------------------------------------


@router.get(
    "/packages",
    response_model=PackagePage,
    summary="员工套餐列表（含下架）",
    description=(
        "需要 `staff` 角色。默认包含已下架套餐；传 `include_inactive=false` "
        "只看在售套餐。分页参数与公开列表一致（page ≥1，page_size ≤100）。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "分页参数越界"},
    },
)
def list_packages(
    paging: PageParams = Depends(pagination),
    include_inactive: bool = Query(
        True, description="是否包含已下架套餐；传 false 只看在售"
    ),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> PackagePage:
    stmt = select(MedicalPackage)
    count_stmt = select(func.count()).select_from(MedicalPackage)
    if not include_inactive:
        stmt = stmt.where(MedicalPackage.is_active.is_(True))
        count_stmt = count_stmt.where(MedicalPackage.is_active.is_(True))

    total = db.scalar(count_stmt) or 0
    items = db.scalars(
        stmt.order_by(MedicalPackage.id)
        .offset(paging.offset)
        .limit(paging.page_size)
    ).all()
    return PackagePage(
        items=[PackageResponse.model_validate(item) for item in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
        pages=paging.pages(total),
    )


@router.post(
    "/packages",
    response_model=PackageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新建套餐",
    description="需要 `staff` 角色。`hospital_id` 必须指向已存在的医院（否则 422）。",
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "字段校验失败或 hospital_id 不存在"},
    },
)
def create_package(
    payload: PackageCreate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> MedicalPackage:
    _require_hospital_exists(db, payload.hospital_id)
    package = MedicalPackage(**payload.model_dump())
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.get(
    "/packages/{package_id}",
    response_model=PackageResponse,
    summary="套餐详情（含下架）",
    description="需要 `staff` 角色。已下架套餐仍可读取，便于重新上架或编辑。",
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "套餐不存在"},
    },
)
def get_package(
    package_id: int,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> MedicalPackage:
    return _get_package(db, package_id)


@router.patch(
    "/packages/{package_id}",
    response_model=PackageResponse,
    summary="更新套餐（含上下架）",
    description=(
        "需要 `staff` 角色。只更新请求体里出现的字段。把 `is_active` 设为 "
        "false 即为下架：套餐立即从公开列表消失且不能再被预约，"
        "但已存在的历史订单金额不受影响（订单价格是下单时的快照）。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "套餐不存在"},
        422: {"description": "字段校验失败或 hospital_id 不存在"},
    },
)
def update_package(
    package_id: int,
    payload: PackageUpdate,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> MedicalPackage:
    package = _get_package(db, package_id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "hospital_id" in changes:
        _require_hospital_exists(db, changes["hospital_id"])
    before = {
        field: getattr(package, field)
        for field in changes
        if getattr(package, field) != changes[field]
    }
    for field, value in changes.items():
        setattr(package, field, value)
    # 只有真正发生变化的字段才写审计，避免空 PATCH 产生噪声。
    if before:
        record_audit(
            db,
            actor=staff,
            action="package.update",
            entity_type="package",
            entity_id=package.id,
            before=before,
            after={field: changes[field] for field in before},
        )
    db.commit()
    db.refresh(package)
    return package


@router.delete(
    "/packages/{package_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除套餐",
    description=(
        "需要 `staff` 角色。套餐已产生订单时返回 409，应改为下架"
        "（PATCH `is_active=false`），避免历史订单失去关联。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "套餐不存在"},
        409: {"description": "套餐已被订单引用，不能删除"},
    },
)
def delete_package(
    package_id: int,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> Response:
    package = _get_package(db, package_id)
    referenced = db.scalar(
        select(Booking.id).where(Booking.package_id == package.id).limit(1)
    )
    if referenced is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Package is referenced by existing bookings; "
                "deactivate it (is_active=false) instead of deleting"
            ),
        )
    record_audit(
        db,
        actor=staff,
        action="package.delete",
        entity_type="package",
        entity_id=package.id,
        before={
            "name": package.name,
            "price": package.price,
            "currency": package.currency,
            "is_active": package.is_active,
            "hospital_id": package.hospital_id,
        },
    )
    db.delete(package)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# 医院
# --------------------------------------------------------------------------


@router.get(
    "/hospitals",
    response_model=HospitalPage,
    summary="员工医院列表（分页）",
    description="需要 `staff` 角色。分页参数与其它列表一致。",
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "分页参数越界"},
    },
)
def list_hospitals(
    paging: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> HospitalPage:
    total = db.scalar(select(func.count()).select_from(Hospital)) or 0
    items = db.scalars(
        select(Hospital)
        .order_by(Hospital.id)
        .offset(paging.offset)
        .limit(paging.page_size)
    ).all()
    return HospitalPage(
        items=[HospitalResponse.model_validate(item) for item in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
        pages=paging.pages(total),
    )


@router.post(
    "/hospitals",
    response_model=HospitalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新建医院",
    description="需要 `staff` 角色。",
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "字段校验失败"},
    },
)
def create_hospital(
    payload: HospitalCreate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Hospital:
    hospital = Hospital(**payload.model_dump())
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


@router.get(
    "/hospitals/{hospital_id}",
    response_model=HospitalResponse,
    summary="医院详情",
    description="需要 `staff` 角色。",
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "医院不存在"},
    },
)
def get_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Hospital:
    return _get_hospital(db, hospital_id)


@router.patch(
    "/hospitals/{hospital_id}",
    response_model=HospitalResponse,
    summary="更新医院",
    description="需要 `staff` 角色。只更新请求体里出现的字段。",
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "医院不存在"},
        422: {"description": "字段校验失败"},
    },
)
def update_hospital(
    hospital_id: int,
    payload: HospitalUpdate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Hospital:
    hospital = _get_hospital(db, hospital_id)
    for field, value in payload.model_dump(
        exclude_unset=True, exclude_none=True
    ).items():
        setattr(hospital, field, value)
    db.commit()
    db.refresh(hospital)
    return hospital


@router.delete(
    "/hospitals/{hospital_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除医院",
    description=(
        "需要 `staff` 角色。医院下仍有套餐时返回 409，"
        "需先迁移或删除套餐。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "医院不存在"},
        409: {"description": "医院仍有套餐引用"},
    },
)
def delete_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> Response:
    hospital = _get_hospital(db, hospital_id)
    referenced = db.scalar(
        select(MedicalPackage.id)
        .where(MedicalPackage.hospital_id == hospital.id)
        .limit(1)
    )
    if referenced is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hospital still has packages; move or delete them first",
        )
    record_audit(
        db,
        actor=staff,
        action="hospital.delete",
        entity_type="hospital",
        entity_id=hospital.id,
        before={
            "name": hospital.name,
            "name_en": hospital.name_en,
            "level": hospital.level,
        },
    )
    db.delete(hospital)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------
# 目的地
# --------------------------------------------------------------------------


@router.get(
    "/destinations",
    response_model=DestinationPage,
    summary="员工目的地列表（分页）",
    description=(
        "需要 `staff` 角色。额外返回 `sort_order`，按 sort_order、id 排序，"
        "与公开列表顺序一致。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        422: {"description": "分页参数越界"},
    },
)
def list_destinations(
    paging: PageParams = Depends(pagination),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> DestinationPage:
    total = db.scalar(select(func.count()).select_from(Destination)) or 0
    items = db.scalars(
        select(Destination)
        .order_by(Destination.sort_order, Destination.id)
        .offset(paging.offset)
        .limit(paging.page_size)
    ).all()
    return DestinationPage(
        items=[StaffDestinationResponse.model_validate(item) for item in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
        pages=paging.pages(total),
    )


@router.post(
    "/destinations",
    response_model=StaffDestinationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新建目的地",
    description=(
        "需要 `staff` 角色。`id` 是与前端一致的 slug，创建后不可修改；"
        "重复的 slug 返回 409。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        409: {"description": "slug 已存在"},
        422: {"description": "字段校验失败或 slug 格式不合法"},
    },
)
def create_destination(
    payload: DestinationCreate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Destination:
    if db.get(Destination, payload.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Destination '{payload.id}' already exists",
        )
    destination = Destination(**payload.model_dump())
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return destination


@router.get(
    "/destinations/{destination_id}",
    response_model=StaffDestinationResponse,
    summary="目的地详情",
    description="需要 `staff` 角色。",
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "目的地不存在"},
    },
)
def get_destination(
    destination_id: str,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Destination:
    return _get_destination(db, destination_id)


@router.patch(
    "/destinations/{destination_id}",
    response_model=StaffDestinationResponse,
    summary="更新目的地",
    description=(
        "需要 `staff` 角色。只更新请求体里出现的字段；"
        "slug（`id`）不可修改，如需变更请新建后删除旧记录。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "目的地不存在"},
        422: {"description": "字段校验失败"},
    },
)
def update_destination(
    destination_id: str,
    payload: DestinationUpdate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_staff),
) -> Destination:
    destination = _get_destination(db, destination_id)
    for field, value in payload.model_dump(
        exclude_unset=True, exclude_none=True
    ).items():
        setattr(destination, field, value)
    db.commit()
    db.refresh(destination)
    return destination


def _destination_reference(db: Session, destination_id: str) -> str | None:
    """返回第一条引用该目的地的行程标题，用于给出可理解的 409 提示。"""
    for itinerary_id, destination_ids in db.execute(
        select(Itinerary.id, Itinerary.destination_ids)
    ).all():
        if destination_id in (destination_ids or []):
            return f"itinerary #{itinerary_id}"
    for itinerary_id, destination_ids in db.execute(
        select(ItineraryDay.itinerary_id, ItineraryDay.destination_ids)
    ).all():
        if destination_id in (destination_ids or []):
            return f"itinerary #{itinerary_id}"
    return None


@router.delete(
    "/destinations/{destination_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除目的地",
    description=(
        "需要 `staff` 角色。目的地仍被任意行程（整体或按天）引用时返回 409，"
        "避免行程里出现指向不存在目的地的 id。"
    ),
    responses={
        401: {"description": "未登录或令牌无效"},
        403: {"description": "已登录但不是 staff"},
        404: {"description": "目的地不存在"},
        409: {"description": "目的地仍被行程引用"},
    },
)
def delete_destination(
    destination_id: str,
    db: Session = Depends(get_db),
    staff: User = Depends(require_staff),
) -> Response:
    destination = _get_destination(db, destination_id)
    reference = _destination_reference(db, destination.id)
    if reference is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Destination '{destination.id}' is still referenced by "
                f"{reference}"
            ),
        )
    record_audit(
        db,
        actor=staff,
        action="destination.delete",
        entity_type="destination",
        entity_id=destination.id,
        before={
            "name": destination.name,
            "name_en": destination.name_en,
            "sort_order": destination.sort_order,
        },
    )
    db.delete(destination)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
