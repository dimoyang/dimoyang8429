"""人工翻译批量导入（CSV → content_translations）。

选型：CSV 而不是 JSON。翻译人员与内容运营直接用 Excel/Numbers 维护表格，
五列扁平结构没有嵌套，导出 CSV 即可；JSON 需要处理引号、转义与层级，
对非工程使用者更容易出错，也不便于 Git diff 审阅。

两阶段执行：
1. 全量校验：列齐全、语言码受支持、entity_type/field 在白名单内、
   entity 真实存在、值非空、文件内无重复唯一键。任一行有错就列出
   所有问题并拒绝写入（不会部分导入）。
2. 按唯一键 (entity_type, entity_id, lang, field) 幂等 upsert：
   不存在则插入，存在且值不同则更新，值相同则跳过。重复执行同一文件
   不会产生额外写入。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.i18n import SUPPORTED_LANGUAGES
from app.models import ContentTranslation, Hospital, MedicalPackage, utcnow

COLUMNS = ("entity_type", "entity_id", "lang", "field", "value")

# 允许导入的实体与字段。destination 不在其中：content_translations.entity_id
# 是整数，而目的地主键是 slug 字符串，当前表结构无法表达。
ENTITY_FIELDS: dict[str, tuple[str, ...]] = {
    "package": ("name", "description"),
    "hospital": ("name",),
}

# en/zh 的主数据在业务表列（name/name_en 等）中维护；写进翻译表不会被
# 公开接口读取，属于“看似生效”的死数据，因此直接拒绝。
COLUMN_LANGUAGES = ("zh", "en")


@dataclass(frozen=True)
class RowProblem:
    """一行数据的问题。line 是 CSV 文件中的物理行号（表头为第 1 行）。"""

    line: int
    message: str


@dataclass(frozen=True)
class ParsedRow:
    line: int
    entity_type: str
    entity_id: int
    lang: str
    field: str
    value: str

    @property
    def key(self) -> tuple[str, int, str, str]:
        return (self.entity_type, self.entity_id, self.lang, self.field)


@dataclass
class ImportSummary:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.unchanged


class TranslationImportError(Exception):
    """校验失败：携带全部问题，便于一次性修正后再导入。"""

    def __init__(self, problems: list[RowProblem]) -> None:
        self.problems = problems
        super().__init__(f"{len(problems)} problem(s) found")

    def format(self) -> str:
        return "\n".join(
            f"第 {problem.line} 行: {problem.message}"
            for problem in self.problems
        )


def _parse_rows(path: Path) -> tuple[list[ParsedRow], list[RowProblem]]:
    path = Path(path)
    rows: list[ParsedRow] = []
    problems: list[RowProblem] = []
    seen: dict[tuple[str, int, str, str], int] = {}

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            return [], [
                RowProblem(
                    line=1,
                    message=f"缺少必需列: {', '.join(missing)}",
                )
            ]

        for line, raw in enumerate(reader, start=2):
            entity_type = (raw.get("entity_type") or "").strip().lower()
            field = (raw.get("field") or "").strip().lower()
            lang = (raw.get("lang") or "").strip().lower()
            raw_id = (raw.get("entity_id") or "").strip()
            value = (raw.get("value") or "").strip()

            row_problems: list[str] = []

            if entity_type not in ENTITY_FIELDS:
                row_problems.append(
                    f"未知 entity_type '{entity_type}'，允许: "
                    + ", ".join(sorted(ENTITY_FIELDS))
                )
            elif field not in ENTITY_FIELDS[entity_type]:
                row_problems.append(
                    f"未知 field '{field}'（{entity_type} 允许: "
                    + ", ".join(ENTITY_FIELDS[entity_type])
                    + "）"
                )

            if lang in COLUMN_LANGUAGES:
                row_problems.append(
                    f"语言 '{lang}' 的主数据在业务表列中维护，不接受导入"
                )
            elif lang not in SUPPORTED_LANGUAGES:
                row_problems.append(
                    f"不支持的语言码 '{lang}'，允许: "
                    + ", ".join(
                        code
                        for code in SUPPORTED_LANGUAGES
                        if code not in COLUMN_LANGUAGES
                    )
                )

            try:
                entity_id = int(raw_id)
            except ValueError:
                entity_id = 0
                row_problems.append(f"entity_id 必须是正整数，收到 '{raw_id}'")
            else:
                if entity_id <= 0:
                    row_problems.append("entity_id 必须是正整数")

            if not value:
                row_problems.append("value 不能为空")

            if row_problems:
                problems.append(RowProblem(line=line, message="；".join(row_problems)))
                continue

            key = (entity_type, entity_id, lang, field)
            first_line = seen.get(key)
            if first_line is not None:
                problems.append(
                    RowProblem(
                        line=line,
                        message=(
                            "与第 "
                            f"{first_line} 行的唯一键重复"
                            f"（{entity_type}/{entity_id}/{lang}/{field}）"
                        ),
                    )
                )
                continue
            seen[key] = line
            rows.append(
                ParsedRow(
                    line=line,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    lang=lang,
                    field=field,
                    value=value,
                )
            )

    return rows, problems


def _validate_entities(
    db: Session, rows: list[ParsedRow]
) -> list[RowProblem]:
    """确认 entity_id 真实存在；避免导入后永远匹配不到内容。"""
    problems: list[RowProblem] = []

    model_by_type = {"package": MedicalPackage, "hospital": Hospital}
    id_sets: dict[str, set[int]] = {}
    for row in rows:
        id_sets.setdefault(row.entity_type, set()).add(row.entity_id)

    found: dict[str, set[int]] = {}
    for entity_type, ids in id_sets.items():
        model = model_by_type[entity_type]
        found[entity_type] = set(
            db.scalars(select(model.id).where(model.id.in_(ids))).all()
        )

    for row in rows:
        if row.entity_id not in found[row.entity_type]:
            problems.append(
                RowProblem(
                    line=row.line,
                    message=(
                        f"{row.entity_type} id={row.entity_id} 不存在"
                    ),
                )
            )
    return problems


def import_translations(
    db: Session, path: Path, dry_run: bool = False
) -> ImportSummary:
    """导入翻译文件；任何校验问题都会抛 TranslationImportError 且不写库。"""
    rows, problems = _parse_rows(path)
    problems.extend(_validate_entities(db, rows))
    if problems:
        problems.sort(key=lambda problem: problem.line)
        raise TranslationImportError(problems)

    summary = ImportSummary()
    for row in rows:
        existing = db.scalar(
            select(ContentTranslation).where(
                ContentTranslation.entity_type == row.entity_type,
                ContentTranslation.entity_id == row.entity_id,
                ContentTranslation.lang == row.lang,
                ContentTranslation.field == row.field,
            )
        )
        if existing is None:
            summary.inserted += 1
            if not dry_run:
                db.add(
                    ContentTranslation(
                        entity_type=row.entity_type,
                        entity_id=row.entity_id,
                        lang=row.lang,
                        field=row.field,
                        value=row.value,
                    )
                )
            continue

        if existing.value == row.value:
            summary.unchanged += 1
            continue

        summary.updated += 1
        if not dry_run:
            existing.value = row.value
            existing.updated_at = utcnow()

    if not dry_run:
        db.commit()
    return summary
