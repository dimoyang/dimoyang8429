"""医疗服务路由：套餐分页与医院列表（可选多语言）。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import load_translations, normalize_lang, pick
from app.models import Hospital, MedicalPackage
from app.pagination import PageParams, pagination
from app.schemas import HospitalResponse, PackagePage, PackageResponse

router = APIRouter(prefix="/medical", tags=["medical"])


def _localized(translated: str | None, chinese: str, english: str, lang: str) -> str:
    if lang == "zh":
        return chinese or english
    if lang == "en":
        return english or chinese
    return pick(translated, english, chinese)


@router.get(
    "/packages",
    response_model=PackagePage,
    summary="套餐分页列表",
    description=(
        "公开接口。分页参数 `page`（≥1）与 `page_size`（默认 20，上限 100）。"
        "可选 `lang=zh|en|de|fr`；不传 `lang` 时响应与旧版本完全一致"
        "（`name` 为中文、`name_en` 为英文）。"
    ),
    responses={
        422: {"description": "分页参数越界或 lang 不是支持的语言"},
    },
)
def list_packages(
    paging: PageParams = Depends(pagination),
    lang: str | None = Query(
        None, description="可选语言：zh / en / de / fr；不传时响应与旧版本完全一致"
    ),
    db: Session = Depends(get_db),
) -> PackagePage:
    total = db.scalar(select(func.count()).select_from(MedicalPackage)) or 0
    items = db.scalars(
        select(MedicalPackage)
        .order_by(MedicalPackage.id)
        .offset(paging.offset)
        .limit(paging.page_size)
    ).all()
    responses = [PackageResponse.model_validate(item) for item in items]

    if lang is not None:
        language = normalize_lang(lang)
        translations = load_translations(
            db,
            "package",
            [response.id for response in responses],
            language,
            ("name", "description"),
        )
        for response in responses:
            translated = translations.get(response.id, {})
            response.name = _localized(
                translated.get("name"),
                response.name,
                response.name_en,
                language,
            )
            response.description = _localized(
                translated.get("description"),
                response.description,
                response.description_en,
                language,
            )

    return PackagePage(
        items=responses,
        total=total,
        page=paging.page,
        page_size=paging.page_size,
        pages=paging.pages(total),
    )


@router.get(
    "/hospitals",
    response_model=list[HospitalResponse],
    summary="医院列表（裸数组）",
    description=(
        "公开接口。为保持 Flutter 契约必须返回裸数组，而不是 `{items: ...}`。"
        "可选 `lang=zh|en|de|fr`；不传时响应与旧版本完全一致。"
    ),
    responses={
        422: {"description": "lang 不是支持的语言"},
    },
)
def list_hospitals(
    lang: str | None = Query(
        None, description="可选语言：zh / en / de / fr；不传时响应与旧版本完全一致"
    ),
    db: Session = Depends(get_db),
) -> list[HospitalResponse]:
    hospitals = list(db.scalars(select(Hospital).order_by(Hospital.id)).all())
    responses = [HospitalResponse.model_validate(item) for item in hospitals]

    if lang is not None:
        language = normalize_lang(lang)
        translations = load_translations(
            db,
            "hospital",
            [response.id for response in responses],
            language,
            ("name",),
        )
        for response in responses:
            response.name = _localized(
                translations.get(response.id, {}).get("name"),
                response.name,
                response.name_en,
                language,
            )

    return responses
