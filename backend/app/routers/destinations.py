"""目的地路由：列表、关键词搜索与详情（可选多语言）。

不传 `lang` 时响应与旧版本完全一致（中文主数据 + `name_en`）。
传 `lang=de|fr` 时，`name` / `tagline` / `intro` / `best_season` /
`suggest_days` 依次取 请求语言译文 → 英文（`name_en`，其余字段无英文列）→ 中文。
数组字段（`search_terms` / `experiences` / `tips`）保持原类型与主数据，
不做字符串化，避免破坏前端契约。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.i18n import load_translations, normalize_lang, pick
from app.models import Destination
from app.schemas import DestinationResponse

router = APIRouter(prefix="/destinations", tags=["destinations"])

# 只翻译标量字段；数组字段维持原类型，见模块 docstring。
TRANSLATABLE_FIELDS = (
    "name",
    "tagline",
    "intro",
    "best_season",
    "suggest_days",
)


def _localized_scalar(
    translated: str | None,
    english: str,
    chinese: str,
    language: str,
) -> str:
    """与医疗套餐一致：请求语言 → en → zh。"""
    if language == "zh":
        return chinese or english
    if language == "en":
        return english or chinese
    return pick(translated, english, chinese)


def _apply_translations(
    responses: list[DestinationResponse],
    translations: dict[str, dict[str, str]],
    language: str,
) -> None:
    for response in responses:
        translated = translations.get(response.id, {})
        response.name = _localized_scalar(
            translated.get("name"),
            response.name_en,
            response.name,
            language,
        )
        # 以下字段没有英文列，英文回退为空，最终仍回落到中文主数据。
        response.tagline = _localized_scalar(
            translated.get("tagline"), "", response.tagline, language
        )
        response.intro = _localized_scalar(
            translated.get("intro"), "", response.intro, language
        )
        response.best_season = _localized_scalar(
            translated.get("best_season"), "", response.best_season, language
        )
        response.suggest_days = _localized_scalar(
            translated.get("suggest_days"), "", response.suggest_days, language
        )


@router.get(
    "",
    response_model=list[DestinationResponse],
    summary="目的地列表（裸数组）",
    description=(
        "公开接口。可选 `query` 关键词与 `lang=zh|en|de|fr`；"
        "不传 `lang` 时响应与旧版本完全一致。"
    ),
    responses={422: {"description": "lang 不是支持的语言"}},
)
def list_destinations(
    query: str | None = Query(None, max_length=120),
    lang: str | None = Query(
        None, description="可选语言：zh / en / de / fr；不传时保持旧响应"
    ),
    db: Session = Depends(get_db),
) -> list[DestinationResponse]:
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
    responses = [
        DestinationResponse.model_validate(item)
        for item in db.scalars(stmt).all()
    ]

    if lang is not None:
        language = normalize_lang(lang)
        translations = load_translations(
            db,
            "destination",
            [response.id for response in responses],
            language,
            TRANSLATABLE_FIELDS,
        )
        _apply_translations(responses, translations, language)

    return responses


@router.get(
    "/{destination_id}",
    response_model=DestinationResponse,
    summary="目的地详情",
    description=(
        "公开接口。`id` 为前端使用的 slug（如 `beijing`）。"
        "可选 `lang=zh|en|de|fr`；不传时响应与旧版本完全一致。"
    ),
    responses={
        404: {"description": "目的地不存在"},
        422: {"description": "lang 不是支持的语言"},
    },
)
def get_destination(
    destination_id: str,
    lang: str | None = Query(
        None, description="可选语言：zh / en / de / fr；不传时保持旧响应"
    ),
    db: Session = Depends(get_db),
) -> DestinationResponse:
    destination = db.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found",
        )
    response = DestinationResponse.model_validate(destination)

    if lang is not None:
        language = normalize_lang(lang)
        translations = load_translations(
            db,
            "destination",
            [response.id],
            language,
            TRANSLATABLE_FIELDS,
        )
        _apply_translations([response], translations, language)

    return response
