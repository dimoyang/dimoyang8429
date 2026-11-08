#!/usr/bin/env python3
"""备份 SQLite 数据库到本地文件，并按保留策略清理旧备份。

示例（在 backend 目录下执行）：
    .\\.venv\\Scripts\\python.exe scripts\\backup_db.py
    .\\.venv\\Scripts\\python.exe scripts\\backup_db.py --output-dir D:\\backups
    .\\.venv\\Scripts\\python.exe scripts\\backup_db.py --daily-keep 14 --weekly-keep 8
    .\\.venv\\Scripts\\python.exe scripts\\backup_db.py --no-retention

默认读取 DATABASE_URL（或 backend/.env），备份写入 backend/var/backups/。
备份完成后会重新统计备份文件的行数与订单指标，并与源库比对。

默认保留策略：最近 7 天每天保留最新一份，更早的每个 ISO 周保留最新一份、
最多 4 周；最新的一份永远不会被删除。只有本脚本命名的
``meditour-YYYYMMDD-HHMMSS.db`` 会被清理，其它文件不动。
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

from app.db_backup import BackupError, backup_database, prune_backups

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
    parser.add_argument(
        "--daily-keep",
        type=int,
        default=7,
        help="最近 N 天每天保留最新一份（默认 7）",
    )
    parser.add_argument(
        "--weekly-keep",
        type=int,
        default=4,
        help="更早的备份每个 ISO 周保留最新一份，最多 M 周（默认 4）",
    )
    parser.add_argument(
        "--no-retention",
        action="store_true",
        help="只备份，不清理旧备份",
    )
    args = parser.parse_args()

    if args.daily_keep < 0 or args.weekly_keep < 0:
        print("保留天数/周数不能为负数", file=sys.stderr)
        return 2

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

    if not args.no_retention:
        try:
            pruned = prune_backups(
                Path(args.output_dir),
                daily_keep=args.daily_keep,
                weekly_keep=args.weekly_keep,
            )
        except BackupError as exc:
            print(f"备份成功，但清理旧备份失败：{exc}", file=sys.stderr)
            return 1
        print("保留策略")
        print(
            f"  最近 {args.daily_keep} 天每天 1 份 + "
            f"每周 1 份最多 {args.weekly_keep} 周"
        )
        print(f"  保留: {len(pruned.kept)} 份")
        print(f"  删除: {len(pruned.deleted)} 份")
        for path in pruned.deleted:
            print(f"    - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
