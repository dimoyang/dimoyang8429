"""人工翻译导入：幂等 upsert、全量校验与错误行号。"""

import csv
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import ContentTranslation, Hospital, MedicalPackage
from app.translations_import import TranslationImportError, import_translations

HEADER = ("entity_type", "entity_id", "lang", "field", "value")


def _make_package(client) -> int:
    """直接建一个套餐，避免依赖员工接口与种子数据顺序。"""
    with SessionLocal() as db:
        hospital_id = db.scalar(select(Hospital.id).order_by(Hospital.id))
        package = MedicalPackage(
            name="导入测试套餐",
            name_en="Import Test Package",
            price=99.0,
            currency="EUR",
            hospital_id=hospital_id,
        )
        db.add(package)
        db.commit()
        return package.id


def _write_csv(path, rows) -> str:
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)
    return str(path)


def _count(db, entity_type: str, entity_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(ContentTranslation)
        .where(
            ContentTranslation.entity_type == entity_type,
            ContentTranslation.entity_id == entity_id,
        )
    )


def test_import_inserts_localized_content_and_is_idempotent(
    client, tmp_path
) -> None:
    package_id = _make_package(client)
    path = _write_csv(
        tmp_path / "translations.csv",
        [
            ("package", package_id, "de", "name", "Importierter Name"),
            (
                "package",
                package_id,
                "de",
                "description",
                "Beschreibung, mit Komma",
            ),
        ],
    )

    with SessionLocal() as db:
        summary = import_translations(db, path)
    assert (summary.inserted, summary.updated, summary.unchanged) == (2, 0, 0)
    assert summary.total == 2

    listing = client.get(
        "/api/v1/medical/packages?lang=de&page=1&page_size=100"
    )
    assert listing.status_code == 200
    item = next(
        item for item in listing.json()["items"] if item["id"] == package_id
    )
    assert item["name"] == "Importierter Name"
    assert item["description"] == "Beschreibung, mit Komma"

    # 再导一次同一文件：全部未变化，不产生重复行。
    with SessionLocal() as db:
        again = import_translations(db, path)
        count = _count(db, "package", package_id)
    assert (again.inserted, again.updated, again.unchanged) == (0, 0, 2)
    assert count == 2


def test_import_updates_existing_value(client, tmp_path) -> None:
    package_id = _make_package(client)
    first = _write_csv(
        tmp_path / "v1.csv",
        [("package", package_id, "fr", "name", "Ancien nom")],
    )
    second = _write_csv(
        tmp_path / "v2.csv",
        [("package", package_id, "fr", "name", "Nouveau nom")],
    )

    with SessionLocal() as db:
        assert import_translations(db, first).inserted == 1
    with SessionLocal() as db:
        summary = import_translations(db, second)
        row = db.scalar(
            select(ContentTranslation).where(
                ContentTranslation.entity_type == "package",
                ContentTranslation.entity_id == package_id,
                ContentTranslation.lang == "fr",
                ContentTranslation.field == "name",
            )
        )
    assert (summary.inserted, summary.updated, summary.unchanged) == (0, 1, 0)
    assert row is not None and row.value == "Nouveau nom"

    listing = client.get(
        "/api/v1/medical/packages?lang=fr&page=1&page_size=100"
    ).json()["items"]
    item = next(item for item in listing if item["id"] == package_id)
    assert item["name"] == "Nouveau nom"


def test_import_supports_hospital_names(client, tmp_path) -> None:
    with SessionLocal() as db:
        hospital_id = db.scalar(select(Hospital.id).order_by(Hospital.id))

    path = _write_csv(
        tmp_path / "translations.csv",
        [("hospital", hospital_id, "fr", "name", "Hôpital de Pékin")],
    )
    with SessionLocal() as db:
        assert import_translations(db, path).inserted == 1

    hospitals = client.get("/api/v1/medical/hospitals?lang=fr").json()
    target = next(item for item in hospitals if item["id"] == hospital_id)
    assert target["name"] == "Hôpital de Pékin"


def test_invalid_rows_report_lines_and_write_nothing(client, tmp_path) -> None:
    package_id = _make_package(client)
    path = _write_csv(
        tmp_path / "translations.csv",
        [
            ("package", package_id, "es", "name", "Idioma no válido"),
            ("package", package_id, "de", "name", "   "),
            ("package", 999999, "de", "name", "No existe"),
            ("package", package_id, "de", "name", "Fila válida"),
        ],
    )

    with SessionLocal() as db:
        with pytest.raises(TranslationImportError) as excinfo:
            import_translations(db, path)
        count = _count(db, "package", package_id)

    problems = excinfo.value.problems
    assert [problem.line for problem in problems] == [2, 3, 4]
    assert "不支持的语言码" in problems[0].message
    assert "value 不能为空" in problems[1].message
    assert "不存在" in problems[2].message
    # 有错时整批拒绝，合法行也不会写入。
    assert count == 0


def test_column_languages_and_unknown_fields_are_rejected(
    client, tmp_path
) -> None:
    package_id = _make_package(client)
    path = _write_csv(
        tmp_path / "translations.csv",
        [
            ("package", package_id, "en", "name", "English override"),
            ("package", package_id, "zh", "name", "中文覆盖"),
            ("package", package_id, "de", "level", "Falsches Feld"),
            ("destination", 1, "de", "name", "Nicht unterstützt"),
        ],
    )

    with SessionLocal() as db:
        with pytest.raises(TranslationImportError) as excinfo:
            import_translations(db, path)

    messages = [problem.message for problem in excinfo.value.problems]
    assert all("业务表列" in messages[index] for index in (0, 1))
    assert "未知 field" in messages[2]
    assert "未知 entity_type" in messages[3]


def test_duplicate_keys_and_bad_ids_are_rejected(client, tmp_path) -> None:
    package_id = _make_package(client)
    path = _write_csv(
        tmp_path / "translations.csv",
        [
            ("package", package_id, "de", "name", "Erste"),
            ("package", package_id, "de", "name", "Zweite"),
            ("package", "abc", "de", "name", "Ungültige ID"),
        ],
    )

    with SessionLocal() as db:
        with pytest.raises(TranslationImportError) as excinfo:
            import_translations(db, path)

    problems = excinfo.value.problems
    assert [problem.line for problem in problems] == [3, 4]
    assert "唯一键重复" in problems[0].message
    assert "entity_id 必须是正整数" in problems[1].message


def test_dry_run_reports_without_writing(client, tmp_path) -> None:
    package_id = _make_package(client)
    path = _write_csv(
        tmp_path / "translations.csv",
        [
            ("package", package_id, "de", "name", "Trockenlauf"),
            ("package", package_id, "de", "description", "Trockenlauf Text"),
        ],
    )

    with SessionLocal() as db:
        summary = import_translations(db, path, dry_run=True)
        count = _count(db, "package", package_id)
    assert (summary.inserted, summary.updated, summary.unchanged) == (2, 0, 0)
    assert count == 0


def test_missing_column_is_reported(client, tmp_path) -> None:
    path = tmp_path / "broken.csv"
    path.write_text(
        "entity_type,entity_id,lang,value\n"
        "package,1,de,Fehlt\n",
        encoding="utf-8",
    )

    with SessionLocal() as db:
        with pytest.raises(TranslationImportError) as excinfo:
            import_translations(db, path)

    assert len(excinfo.value.problems) == 1
    assert excinfo.value.problems[0].line == 1
    assert "缺少必需列" in excinfo.value.problems[0].message
