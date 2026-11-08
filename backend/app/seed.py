"""种子数据：从 `backend/seed/*.json` 读取内容并幂等写入数据库。

数据文件是唯一内容源，按用途分两套：

- `seed/base/`：最小可用目录（2 家医院、2 个套餐、4 个目的地、德语示例译文）。
- `seed/demo/`：更完整的演示目录（额外 6 家医院、20 个套餐、10 个目的地、
  de/fr 译文），用于本地体验和联调。

启动时的行为由两个开关控制（见 README「种子数据」）：

- `MEDITOUR_AUTO_SEED`：开发默认开、生产默认关。关闭时启动不写任何数据。
- `MEDITOUR_SEED_DEMO_DATA`：开发默认开、生产默认关。开启时在 base 之外追加 demo。

写入规则：

- 按自然键判断是否存在：医院/套餐用 `name_en`，目的地用 `id`，译文用
  `(entity_type, entity_key, lang, field)`。
- 默认只插入缺失行，**不修改**已有行，因此不会覆盖员工在后台改过的内容。
- `sync=True`（命令行 `--sync`）时才会把已有行的字段更新为文件里的值；
  仍然只增不删，文件里删掉的条目不会从数据库删除。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ContentTranslation,
    Destination,
    Hospital,
    MedicalPackage,
    User,
)
from app.security import hash_password
from app.translations_import import ENTITY_FIELDS

SEED_ROOT = Path(__file__).resolve().parent.parent / "seed"
BASE_PROFILE = "base"
DEMO_PROFILE = "demo"
FILES = ("hospitals", "packages", "destinations", "translations")
COLUMN_LANGUAGES = ("zh", "en")
SUPPORTED_TRANSLATION_LANGUAGES = ("de", "fr")

DEMO_EMAIL = "demo@meditour.com"
DEMO_PASSWORD = "Demo123456"


class SeedError(Exception):
    """种子文件缺失、格式错误或引用不存在，启动时应直接失败并给出可读原因。"""


def _load(profile: str, name: str) -> list[dict[str, Any]]:
    path = SEED_ROOT / profile / f"{name}.json"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SeedError(f"缺少种子文件 {path}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SeedError(
            f"{path} 第 {exc.lineno} 行 JSON 格式错误：{exc.msg}"
        ) from exc
    if not isinstance(payload, list):
        raise SeedError(f"{path} 顶层必须是数组")
    return payload


def _unique_keys(
    rows: list[dict[str, Any]], key: str, label: str
) -> None:
    seen: dict[str, int] = {}
    for index, row in enumerate(rows, start=1):
        value = str(row.get(key) or "").strip()
        if not value:
            raise SeedError(f"{label} 第 {index} 条缺少 {key}")
        if value in seen:
            raise SeedError(
                f"{label} 第 {index} 条的 {key}={value!r} 与第 {seen[value]} 条重复"
            )
        seen[value] = index


def _text(row: dict[str, Any], field: str, label: str, index: int) -> str:
    value = str(row.get(field) or "").strip()
    if not value:
        raise SeedError(f"{label} 第 {index} 条缺少 {field}")
    return value


def _number(
    row: dict[str, Any], field: str, label: str, index: int, *, minimum: float = 0
) -> float:
    try:
        value = float(row.get(field))
    except (TypeError, ValueError) as exc:
        raise SeedError(f"{label} 第 {index} 条的 {field} 必须是数字") from exc
    if value < minimum:
        raise SeedError(f"{label} 第 {index} 条的 {field} 不能小于 {minimum}")
    return value


def _integer(
    row: dict[str, Any], field: str, label: str, index: int, *, minimum: int = 1
) -> int:
    value = _number(row, field, label, index, minimum=minimum)
    if int(value) != value:
        raise SeedError(f"{label} 第 {index} 条的 {field} 必须是整数")
    return int(value)


def _string_list(
    row: dict[str, Any], field: str, label: str, index: int
) -> list[str]:
    value = row.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise SeedError(f"{label} 第 {index} 条的 {field} 必须是字符串数组")
    return value


def _apply_hospitals(
    db: Session, rows: list[dict[str, Any]], label: str, *, sync: bool
) -> tuple[int, int]:
    _unique_keys(rows, "name_en", label)
    created = updated = 0
    for index, row in enumerate(rows, start=1):
        name_en = _text(row, "name_en", label, index)
        values = {
            "name": _text(row, "name", label, index),
            "level": _text(row, "level", label, index),
        }
        existing = db.scalar(
            select(Hospital).where(Hospital.name_en == name_en)
        )
        if existing is None:
            db.add(Hospital(name_en=name_en, **values))
            created += 1
            continue
        if sync and any(
            getattr(existing, field) != value for field, value in values.items()
        ):
            for field, value in values.items():
                setattr(existing, field, value)
            updated += 1
    db.flush()
    return created, updated


def _apply_packages(
    db: Session, rows: list[dict[str, Any]], label: str, *, sync: bool
) -> tuple[int, int]:
    _unique_keys(rows, "name_en", label)
    hospitals = {
        hospital.name_en: hospital
        for hospital in db.scalars(select(Hospital)).all()
    }
    created = updated = 0
    for index, row in enumerate(rows, start=1):
        name_en = _text(row, "name_en", label, index)
        hospital_key = _text(row, "hospital_key", label, index)
        hospital = hospitals.get(hospital_key)
        if hospital is None:
            raise SeedError(
                f"{label} 第 {index} 条引用的医院 name_en={hospital_key!r} 不存在，"
                "请先在同目录 hospitals.json 中定义"
            )
        values = {
            "name": _text(row, "name", label, index),
            "price": _number(row, "price", label, index),
            "duration_days": _integer(row, "duration_days", label, index),
            "category": _text(row, "category", label, index),
            "description": _text(row, "description", label, index),
            "description_en": _text(row, "description_en", label, index),
            "hospital_id": hospital.id,
        }
        # 演示套餐允许没有图片；--sync 时不要用空值覆盖后台已上传的图片。
        image_url = str(row.get("image_url") or "").strip()
        if image_url:
            values["image_url"] = image_url
        existing = db.scalar(
            select(MedicalPackage).where(
                MedicalPackage.name_en == name_en
            )
        )
        if existing is None:
            db.add(
                MedicalPackage(
                    name_en=name_en,
                    currency=settings.DEFAULT_CURRENCY,
                    **values,
                )
            )
            created += 1
            continue
        if sync and any(
            getattr(existing, field) != value for field, value in values.items()
        ):
            for field, value in values.items():
                setattr(existing, field, value)
            updated += 1
    db.flush()
    return created, updated


def _apply_destinations(
    db: Session, rows: list[dict[str, Any]], label: str, *, sync: bool
) -> tuple[int, int]:
    _unique_keys(rows, "id", label)
    created = updated = 0
    for index, row in enumerate(rows, start=1):
        destination_id = _text(row, "id", label, index)
        values = {
            "name": _text(row, "name", label, index),
            "name_en": _text(row, "name_en", label, index),
            "tagline": _text(row, "tagline", label, index),
            "image_url": _text(row, "image_url", label, index),
            "search_terms": _string_list(row, "search_terms", label, index),
            "best_season": _text(row, "best_season", label, index),
            "suggest_days": _text(row, "suggest_days", label, index),
            "intro": _text(row, "intro", label, index),
            "experiences": row.get("experiences"),
            "tips": _string_list(row, "tips", label, index),
            "sort_order": _integer(row, "sort_order", label, index, minimum=0),
        }
        if not isinstance(values["experiences"], list) or not all(
            isinstance(item, dict) for item in values["experiences"]
        ):
            raise SeedError(
                f"{label} 第 {index} 条的 experiences 必须是对象数组"
            )
        existing = db.scalar(
            select(Destination).where(Destination.id == destination_id)
        )
        if existing is None:
            db.add(Destination(id=destination_id, **values))
            created += 1
            continue
        if sync and any(
            getattr(existing, field) != value for field, value in values.items()
        ):
            for field, value in values.items():
                setattr(existing, field, value)
            updated += 1
    db.flush()
    return created, updated


def _entity_ids(db: Session) -> dict[str, dict[str, str]]:
    return {
        "package": {
            package.name_en: str(package.id)
            for package in db.scalars(select(MedicalPackage)).all()
        },
        "hospital": {
            hospital.name_en: str(hospital.id)
            for hospital in db.scalars(select(Hospital)).all()
        },
        "destination": {
            destination.id: destination.id
            for destination in db.scalars(select(Destination)).all()
        },
    }


def _apply_translations(
    db: Session, rows: list[dict[str, Any]], label: str, *, sync: bool
) -> tuple[int, int]:
    ids = _entity_ids(db)
    created = updated = 0
    for index, row in enumerate(rows, start=1):
        entity_type = _text(row, "entity_type", label, index).lower()
        if entity_type not in ENTITY_FIELDS:
            raise SeedError(
                f"{label} 第 {index} 条的 entity_type={entity_type!r} 不支持"
            )
        entity_key = _text(row, "entity_key", label, index)
        lang = _text(row, "lang", label, index).lower()
        field = _text(row, "field", label, index).lower()
        value = _text(row, "value", label, index)

        if lang in COLUMN_LANGUAGES:
            raise SeedError(
                f"{label} 第 {index} 条的语言 {lang!r} 应直接写在业务表列中，"
                "种子译文只接受 de/fr"
            )
        if lang not in SUPPORTED_TRANSLATION_LANGUAGES:
            raise SeedError(
                f"{label} 第 {index} 条的语言 {lang!r} 不支持，"
                f"可选：{', '.join(SUPPORTED_TRANSLATION_LANGUAGES)}"
            )
        if field not in ENTITY_FIELDS[entity_type]:
            raise SeedError(
                f"{label} 第 {index} 条的 field={field!r} 对 {entity_type} 不适用，"
                f"可选：{', '.join(ENTITY_FIELDS[entity_type])}"
            )
        entity_id = ids[entity_type].get(entity_key)
        if entity_id is None:
            raise SeedError(
                f"{label} 第 {index} 条引用的 {entity_type} "
                f"entity_key={entity_key!r} 不存在，请先定义主数据"
            )

        existing = db.scalar(
            select(ContentTranslation).where(
                ContentTranslation.entity_type == entity_type,
                ContentTranslation.entity_id == entity_id,
                ContentTranslation.lang == lang,
                ContentTranslation.field == field,
            )
        )
        if existing is None:
            db.add(
                ContentTranslation(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    lang=lang,
                    field=field,
                    value=value,
                )
            )
            created += 1
            continue
        if sync and existing.value != value:
            existing.value = value
            updated += 1
    db.flush()
    return created, updated


def seed_data(
    db: Session,
    *,
    demo: bool | None = None,
    sync: bool = False,
) -> dict[str, tuple[int, int]]:
    """写入种子数据；返回各实体的 (新增, 更新) 计数。

    `demo=None` 时读取 `settings.SEED_DEMO_DATA`。重复调用不会产生重复行；
    `sync=True` 才会更新已有行的字段，且永远不删除文件里已移除的条目。
    """
    if demo is None:
        demo = settings.SEED_DEMO_DATA

    stats: dict[str, tuple[int, int]] = {}
    profiles = [BASE_PROFILE]
    if demo:
        profiles.append(DEMO_PROFILE)

    if settings.SEED_DEMO_USER and db.scalar(
        select(User).where(User.email == DEMO_EMAIL)
    ) is None:
        db.add(
            User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name="Demo User",
                preferred_language="en",
            )
        )
        db.flush()

    for profile in profiles:
        # 主数据先写、译文后写：译文需要解析出对应实体的 id。
        for name, handler in (
            ("hospitals", _apply_hospitals),
            ("packages", _apply_packages),
            ("destinations", _apply_destinations),
            ("translations", _apply_translations),
        ):
            rows = _load(profile, name)
            label = f"{profile}/{name}.json"
            created, updated = handler(db, rows, label, sync=sync)
            previous = stats.get(name, (0, 0))
            stats[name] = (
                previous[0] + created,
                previous[1] + updated,
            )

    db.commit()
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把 backend/seed 下的 JSON 写入数据库（幂等）"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="用文件内容更新已存在的记录（仍不删除数据库中的多余记录）",
    )
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument(
        "--demo", dest="demo", action="store_true", help="同时写入 demo 目录"
    )
    profile.add_argument(
        "--base",
        dest="demo",
        action="store_false",
        help="只写入 base 目录",
    )
    parser.set_defaults(demo=None)
    args = parser.parse_args(argv)

    from app.database import SessionLocal
    from app.db_migrate import ensure_database_schema

    ensure_database_schema()
    with SessionLocal() as db:
        stats = seed_data(db, demo=args.demo, sync=args.sync)
    mode = "同步" if args.sync else "仅补缺"
    print(f"种子写入完成（{mode}）：")
    for name in FILES:
        created, updated = stats.get(name, (0, 0))
        print(f"  {name}: 新增 {created}，更新 {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
