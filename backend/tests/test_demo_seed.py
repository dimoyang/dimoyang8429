"""联调演示种子数据：默认不写入、开启后可重复执行且不污染已有数据。"""

from __future__ import annotations

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app import seed
from app.config import settings
from app.database import Base
from app.models import ContentTranslation, Destination, Hospital, MedicalPackage


def _fresh_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _counts(db) -> tuple[int, int, int, int]:
    return (
        db.scalar(select(func.count()).select_from(Hospital)),
        db.scalar(select(func.count()).select_from(MedicalPackage)),
        db.scalar(select(func.count()).select_from(Destination)),
        db.scalar(
            select(func.count())
            .select_from(ContentTranslation)
            .where(ContentTranslation.lang.in_(("de", "fr")))
        ),
    )


def test_demo_seed_is_off_by_default(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SEED_DEMO_DATA", False)
    db = _fresh_session()
    seed.seed_data(db)
    hospitals, packages, destinations, translations = _counts(db)
    assert (hospitals, packages, destinations) == (2, 2, 4)
    # 只有原有 3 条德语示例译文。
    assert translations == 3


def test_demo_seed_adds_catalog_and_is_idempotent(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SEED_DEMO_DATA", True)
    db = _fresh_session()
    seed.seed_data(db)
    first = _counts(db)

    # 新增 6 家医院、20 个套餐、10 个目的地。
    assert first[:3] == (8, 22, 14)
    # 原有 3 条德语 + 演示的 40 条 hospital/package 译文 + 24 条目的地译文。
    assert first[3] == 67

    # 重复执行不产生重复行。
    seed.seed_data(db)
    assert _counts(db) == first

    # 分类足够多、价格区间覆盖低端与高端。
    categories = set(db.scalars(select(MedicalPackage.category)).all())
    assert len(categories) >= 10
    assert db.scalar(select(func.min(MedicalPackage.price))) <= 300
    assert db.scalar(select(func.max(MedicalPackage.price))) >= 45000
    assert db.scalar(
        select(func.count())
        .select_from(MedicalPackage)
        .where(MedicalPackage.duration_days > 7)
    ) >= 10

    # 关掉开关不会删除已写入的数据（只做增量）。
    monkeypatch.setattr(settings, "SEED_DEMO_DATA", False)
    seed.seed_data(db)
    assert _counts(db) == first
