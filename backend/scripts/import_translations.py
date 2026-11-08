#!/usr/bin/env python3
"""批量导入人工翻译（CSV）。

示例（在 backend 目录下执行）：
    .\\.venv\\Scripts\\python.exe scripts\\import_translations.py translations.csv
    .\\.venv\\Scripts\\python.exe scripts\\import_translations.py translations.csv --dry-run

CSV 表头固定为：entity_type,entity_id,lang,field,value

- 只接受非 zh/en 的语言码（en/zh 主数据在业务表列中维护）；
- package 允许 name/description，hospital 允许 name；
- 校验不通过时列出全部问题并退出码 1，不会写入任何一行；
- 通过后按 (entity_type, entity_id, lang, field) 幂等 upsert，可重复执行。

与其它脚本一样，需要先设置 MEDITOUR_SECRET_KEY（或 backend/.env）。
"""

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

from app.database import SessionLocal
from app.translations_import import TranslationImportError, import_translations

load_dotenv(BACKEND_DIR / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="导入人工翻译 CSV")
    parser.add_argument("file", help="CSV 文件路径")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只校验并统计将要写入的行，不实际修改数据库",
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        print(f"文件不存在：{path}", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        try:
            summary = import_translations(db, path, dry_run=args.dry_run)
        except TranslationImportError as exc:
            print(f"导入失败，共 {len(exc.problems)} 处问题：", file=sys.stderr)
            print(exc.format(), file=sys.stderr)
            return 1

    prefix = "预演完成（未写库）" if args.dry_run else "导入完成"
    print(prefix)
    print(f"  文件: {path}")
    print(f"  总行数: {summary.total}")
    print(f"  新增: {summary.inserted}")
    print(f"  更新: {summary.updated}")
    print(f"  未变化: {summary.unchanged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
