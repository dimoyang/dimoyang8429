#!/usr/bin/env python3
"""数据保留清理：过期令牌、审计日志、软删除账号、邮件预览与上传临时文件。

默认 dry-run 只统计、不写入；确认无误后加 `--no-dry-run` 才真正删除。
保留期全部来自环境变量（见 README「数据保留」）：

    MEDITOUR_TOKEN_RETENTION_DAYS                默认 30
    MEDITOUR_AUDIT_LOG_RETENTION_DAYS            默认 365
    MEDITOUR_SOFT_DELETED_ACCOUNT_RETENTION_DAYS 默认 30
    MEDITOUR_MAIL_PREVIEW_RETENTION_DAYS         默认 14
    MEDITOUR_UPLOAD_TEMP_RETENTION_DAYS          默认 1

示例（在 backend 目录下执行）：
    .\\.venv\\Scripts\\python.exe scripts\\cleanup_data.py
    .\\.venv\\Scripts\\python.exe scripts\\cleanup_data.py --no-dry-run

注意：软删除账号只清理可再生的关联数据（行程、会话、令牌），**不删除用户行
与订单**，原因见 app/retention.py 顶部说明。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import retention
from app.config import settings
from app.database import SessionLocal


def _format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KiB"
    return f"{size / (1024 * 1024):.1f} MiB"


def _print_item(item: retention.CleanupItem, dry_run: bool) -> None:
    action = "将删除" if dry_run else "已删除"
    line = f"  {action} {item.label}: {item.count}"
    if item.freed_bytes:
        line += f"（释放 {_format_bytes(item.freed_bytes)}）"
    if item.detail:
        line += f"；{item.detail}"
    print(line)
    if item.samples:
        print(f"    示例: {', '.join(item.samples)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="按保留期清理过期数据")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="只统计将删除的内容，不写入（默认行为）",
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="真正执行删除",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="跳过交互确认（用于定时任务）",
    )
    parser.add_argument(
        "--now",
        help="覆盖当前时间（ISO 8601），仅用于演算，不建议在生产使用",
    )
    args = parser.parse_args()

    now = (
        datetime.fromisoformat(args.now).astimezone(timezone.utc)
        if args.now
        else datetime.now(timezone.utc)
    )

    print(
        "数据清理"
        + ("（dry-run，不写入）" if args.dry_run else "（真实执行）")
    )
    print(
        "保留期:"
        f" tokens={settings.TOKEN_RETENTION_DAYS}d"
        f" audit={settings.AUDIT_LOG_RETENTION_DAYS}d"
        f" soft_deleted={settings.SOFT_DELETED_ACCOUNT_RETENTION_DAYS}d"
        f" mail={settings.MAIL_PREVIEW_RETENTION_DAYS}d"
        f" upload_temp={settings.UPLOAD_TEMP_RETENTION_DAYS}d"
    )

    if not args.dry_run and not args.yes:
        if not sys.stdin.isatty():
            print("非交互环境请显式加 --yes 以确认删除。", file=sys.stderr)
            return 1
        answer = input("将真正删除上述过期数据，确认继续？[y/N] ")
        if answer.strip().lower() not in {"y", "yes"}:
            print("已取消。")
            return 1

    print("\n[令牌与审计日志]")
    total_rows = 0
    with SessionLocal() as db:
        items = retention.cleanup_expired_tokens(
            db, now, settings.TOKEN_RETENTION_DAYS, args.dry_run
        )
        items.append(
            retention.cleanup_audit_logs(
                db, now, settings.AUDIT_LOG_RETENTION_DAYS, args.dry_run
            )
        )
        items.append(
            retention.cleanup_soft_deleted_accounts(
                db,
                now,
                settings.SOFT_DELETED_ACCOUNT_RETENTION_DAYS,
                args.dry_run,
            )
        )
    for item in items:
        total_rows += item.count
        _print_item(item, args.dry_run)

    print("\n[邮件预览与上传临时文件]")
    file_items = retention.cleanup_mail_files(
        now,
        settings.MAIL_PREVIEW_DIR,
        settings.MAIL_OUTBOX,
        settings.MAIL_PREVIEW_RETENTION_DAYS,
        args.dry_run,
    )
    file_items.append(
        retention.cleanup_upload_temp_files(
            now,
            settings.UPLOAD_DIR,
            settings.UPLOAD_TEMP_RETENTION_DAYS,
            args.dry_run,
        )
    )
    for item in file_items:
        _print_item(item, args.dry_run)

    total_files = sum(
        item.count for item in file_items if item.label.endswith("_files")
    )
    outbox_lines = sum(
        item.count for item in file_items if item.label == "mail_outbox_lines"
    )
    freed = sum(item.freed_bytes for item in file_items)
    verb = "将删除" if args.dry_run else "已删除"
    print(
        f"\n合计{verb} {total_rows} 行数据库记录、{total_files} 个文件、"
        f"{outbox_lines} 行 outbox 索引，释放 {_format_bytes(freed)}。"
    )
    if args.dry_run:
        print("这是预演。确认无误后加 --no-dry-run 执行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
