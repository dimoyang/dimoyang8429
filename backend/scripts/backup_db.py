#!/usr/bin/env python3
"""备份 SQLite 数据库到本地文件。

示例（在 backend 目录下执行）：
    .\\.venv\\Scripts\\python.exe scripts\\backup_db.py
    .\\.venv\\Scripts\\python.exe scripts\\backup_db.py --output-dir D:\\backups

默认读取 DATABASE_URL（或 backend/.env），备份写入 backend/var/backups/。
备份完成后会重新统计备份文件的行数与订单指标，并与源库比对。
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

from app.db_backup import BackupError, backup_database

load_dotenv(BACKEND_DIR / ".env")


def _default_database_url() -> str:
    return os.getenv(
        "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'meditour.db').as_posix()}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="备份 MediTour SQLite 数据库")
    parser.add_argument(
        "--database-url",
        default=_default_database_url(),
        help="源数据库连接串（默认 DATABASE_URL）",
    )
    parser.add_argument(
        "--output-dir",
        default=str(BACKEND_DIR / "var" / "backups"),
        help="备份目录，不存在会自动创建",
    )
    parser.add_argument(
        "--name", help="备份文件名（默认 meditour-<时间戳>.db）"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="允许覆盖已存在的同名备份"
    )
    args = parser.parse_args()

    filename = args.name or f"meditour-{datetime.now():%Y%m%d-%H%M%S}.db"
    target = Path(args.output_dir) / filename

    try:
        result = backup_database(
            args.database_url, target, overwrite=args.overwrite
        )
    except BackupError as exc:
        print(f"备份失败：{exc}", file=sys.stderr)
        return 1

    data = result.fingerprint
    print("备份完成")
    print(f"  源库: {result.source}")
    print(f"  备份: {result.target}")
    print(f"  大小: {data.size_bytes} bytes")
    print(f"  sha256: {data.sha256}")
    print(f"  表行数: {data.tables}")
    print(f"  订单状态: {data.bookings_by_status or '{}'}")
    print(f"  订单总金额: {data.booking_total_price}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
