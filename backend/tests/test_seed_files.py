"""种子数据文件：内容规模、四语覆盖、幂等与 --sync 增量更新。"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import seed
from app.database import Base
from app.models import ContentTranslation, Destination, Hospital, MedicalPackage


def _fresh_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _read(profile: str, name: str):
    path = seed.SEED_ROOT / profile / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_seed_files_have_enough_content() -> None:
    base_hospitals = _read("base", "hospitals")
    base_packages = _read("base", "packages")
    base_destinations = _read("base", "destinations")
    demo_hospitals = _read("demo", "hospitals")
    demo_packages = _read("demo", "packages")
    demo_destinations = _read("demo", "destinations")

    assert (len(base_hospitals), len(base_packages), len(base_destinations)) == (
        2,
        2,
        4,
    )
    # 演示目录要能撑起一页以上目的地、多个分类与价格区间。
    assert len(demo_hospitals) >= 6
    assert len(demo_packages) >= 20
    assert len(base_destinations) + len(demo_destinations) >= 12
    categories = {row["category"] for row in base_packages + demo_packages}
    prices = [row["price"] for row in base_packages + demo_packages]
    assert len(categories) >= 10
    assert min(prices) <= 300
    assert max(prices) >= 45000


def test_seed_files_cover_four_languages() -> None:
    base_translations = _read("base", "translations")
    demo_translations = _read("demo", "translations")
    languages = {row["lang"] for row in base_translations + demo_translations}
    # zh/en 直接存业务表列，de/fr 存翻译表；四种语言全部有内容。
    assert languages == {"de", "fr"}
    assert any(row["entity_type"] == "destination" for row in demo_translations)
    assert any(row["entity_type"] == "package" for row in demo_translations)
    assert any(row["entity_type"] == "hospital" for row in demo_translations)

    for row in base_translations + demo_translations:
        assert row["value"].strip()
        assert row["entity_key"].strip()


def test_seed_is_idempotent_and_sync_updates_in_place() -> None:
    db = _fresh_session()
    seed.seed_data(db, demo=True)
    first = (
        db.scalar(select(func.count()).select_from(Hospital)),
        db.scalar(select(func.count()).select_from(MedicalPackage)),
        db.scalar(select(func.count()).select_from(Destination)),
        db.scalar(select(func.count()).select_from(ContentTranslation)),
    )

    # 重复启动不产生重复行。
    stats = seed.seed_data(db, demo=True)
    assert all(created == 0 for created, _ in stats.values())
    assert (
        db.scalar(select(func.count()).select_from(Hospital)),
        db.scalar(select(func.count()).select_from(MedicalPackage)),
        db.scalar(select(func.count()).select_from(Destination)),
        db.scalar(select(func.count()).select_from(ContentTranslation)),
    ) == first

    # 模拟员工改坏一条种子内容：默认不覆盖。
    package = db.scalar(
        select(MedicalPackage).where(
            MedicalPackage.name_en == "Knee Replacement Surgery"
        )
    )
    package.name = "被改过的名字"
    package.price = 1
    db.commit()
    seed.seed_data(db, demo=True)
    db.refresh(package)
    assert package.name == "被改过的名字"
    assert package.price == 1

    # --sync 才会按文件恢复，且不删除数据库中的其它记录。
    stats = seed.seed_data(db, demo=True, sync=True)
    assert stats["packages"][1] >= 1
    db.refresh(package)
    assert package.name == "膝关节置换手术"
    assert package.price == 15000
    assert (
        db.scalar(select(func.count()).select_from(MedicalPackage))
        == first[1]
    )


def test_seed_rejects_duplicate_or_unknown_entities() -> None:
    db = _fresh_session()
    with pytest.raises(seed.SeedError, match="重复"):
        seed._apply_hospitals(
            db,
            [
                {"name": "甲", "name_en": "Same", "level": "三级甲等"},
                {"name": "乙", "name_en": "Same", "level": "三级甲等"},
            ],
            "demo/hospitals.json",
            sync=False,
        )

    with pytest.raises(seed.SeedError, match="不存在"):
        seed._apply_translations(
            db,
            [
                {
                    "entity_type": "package",
                    "entity_key": "Missing Package",
                    "lang": "de",
                    "field": "name",
                    "value": "Fehlt",
                }
            ],
            "demo/translations.json",
            sync=False,
        )

    with pytest.raises(seed.SeedError, match="de/fr"):
        seed._apply_translations(
            db,
            [
                {
                    "entity_type": "destination",
                    "entity_key": "beijing",
                    "lang": "zh",
                    "field": "name",
                    "value": "北京",
                }
            ],
            "demo/translations.json",
            sync=False,
        )
