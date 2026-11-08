"""医疗内容多语言：读取 content_translations 并按 请求语言 → en → zh 回退。

en / zh 仍存放在业务表列中（name/name_en、description/description_en），
本模块只负责加载 de/fr 等额外语言覆盖值。
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ContentTranslation

# 当前接口支持的语言；新增语言需要同时补种子/翻译数据。
SUPPORTED_LANGUAGES = ("zh", "en", "de", "fr")


def normalize_lang(lang: str) -> str:
    normalized = lang.strip().lower()
    if normalized not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Unsupported lang; supported values: "
                + ", ".join(SUPPORTED_LANGUAGES)
            ),
        )
    return normalized


def load_translations(
    db: Session,
    entity_type: str,
    entity_ids: list[int | str],
    lang: str,
    fields: tuple[str, ...],
) -> dict[str, dict[str, str]]:
    """一次性取回多个实体在指定语言下的译文，避免 N+1 查询。

    返回的键统一为字符串：套餐/医院传整数主键也可以，目的地直接传 slug。
    """
    if not entity_ids:
        return {}

    normalized_ids = [str(entity_id) for entity_id in entity_ids]
    rows = db.scalars(
        select(ContentTranslation).where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.entity_id.in_(normalized_ids),
            ContentTranslation.lang == lang,
            ContentTranslation.field.in_(fields),
        )
    ).all()

    result: dict[str, dict[str, str]] = {}
    for row in rows:
        result.setdefault(str(row.entity_id), {})[row.field] = row.value
    return result


def pick(translated: str | None, english: str, chinese: str) -> str:
    """回退顺序：请求语言译文 → 英文 → 中文。"""
    return translated or english or chinese
