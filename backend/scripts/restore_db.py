#!/usr/bin/env python3
"""用备份覆盖 SQLite 数据库。

安全规则：
- 目标库已有业务表时拒绝执行，必须显式加 --force；
- 覆盖前自动保留 <库名>.pre-restore-<时间戳>.db.bak，误操作时还能找回；
- 恢复后重新统计行数与订单指标，与备份不一致时以非零状态退出。

示例（在 backend 目录下执行，先停掉后端进程）：
    .\\.venv\\Scripts\\python.exe scripts\\restore_db.py --backup var\\backups\\meditour-20261108-101500.db
    .\\.venv\\Scripts\\python.exe scripts\\restore_db.py --backup <file> --force

注意：恢复后请用当前代码重新执行一次 `alembic upgrade head`，确认备份里的
schema 版本不会落后于应用。
"""

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

from app.db_backup import BackupError, fingerprint, restore_database

load_dotenv(BACKEND_DIR / ".env")


def _default_database_url() -> str:
    return os.getenv(
        "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'meditour.db').as_posix()}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="从备份恢复 MediTour SQLite 数据库")
    parser.add_argument("--backup", required=True, help="备份文件路径")
    parser.add_argument(
        "--database-url",
        default=_default_database_url(),
        help="目标数据库连接串（默认 DATABASE_URL）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="目标非空时仍覆盖（覆盖前会自动保留 pre-restore 副本）",
    )
    args = parser.parse_args()

    backup_path = Path(args.backup)
    try:
        backup_fingerprint = fingerprint(backup_path)
        result = restore_database(
            backup_path, args.database_url, force=args.force
        )
    except BackupError as exc:
        print(f"恢复失败：{exc}", file=sys.stderr)
        return 1

    data = result.fingerprint
    print("恢复完成")
    print(f"  备份: {result.backup}")
    print(f"  目标: {result.target}")
    if result.safety_copy:
        print(f"  覆盖前副本: {result.safety_copy}")
    print(f"  大小: {data.size_bytes} bytes")
    print(f"  表行数: {data.tables}")
    print(f"  订单状态: {data.bookings_by_status or '{}'}")
    print(f"  订单总金额: {data.booking_total_price}")
    print(
        "  校验: 与备份一致"
        if data.tables == backup_fingerprint.tables
        else "  校验: 不一致（见上方行数）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
