"""数据保留与清理。

清理任务由 `scripts/cleanup_data.py` 手动触发，不在应用启动时自动执行，
避免误删和不可预期的启动耗时。所有函数都支持 dry-run：只统计、不写入。

软删除账号只清理可再生的关联数据（行程、会话、令牌），**不删除用户行与订单**：
- `bookings.user_id` 外键引用用户行，物理删除用户会破坏订单归属；
- 订单属于交易记录，需要保留用于对账与审计；
- 注销时用户行已经匿名化（邮箱/姓名/电话被替换），保留空壳行不构成隐私风险。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    AuthSession,
    Booking,
    EmailVerificationToken,
    Itinerary,
    ItineraryDay,
    PasswordResetToken,
    TokenRevocation,
    User,
)

TEMP_UPLOAD_SUFFIXES = {".tmp", ".part", ".upload"}


@dataclass
class CleanupItem:
    """一类数据的清理结果；samples 只用于 dry-run 时展示少量示例。"""

    label: str
    count: int
    freed_bytes: int = 0
    detail: str = ""
    samples: list[str] = field(default_factory=list)


def _cutoff(now: datetime, days: int) -> datetime:
    """数据库列存的是 naive UTC，统一去掉时区再与列比较。"""
    cutoff = now - timedelta(days=days)
    return cutoff.replace(tzinfo=None) if cutoff.tzinfo else cutoff


def _count(db: Session, model: object, condition: object) -> int:
    return int(
        db.scalar(select(func.count()).select_from(model).where(condition))
        or 0
    )


def _delete_rows(
    db: Session, model: object, condition: object, dry_run: bool
) -> None:
    if not dry_run:
        db.execute(delete(model).where(condition))
        db.commit()


def cleanup_expired_tokens(
    db: Session, now: datetime, retention_days: int, dry_run: bool
) -> list[CleanupItem]:
    """过期令牌在保留期后删除；已使用但尚未过期的令牌同样按使用时间清理。"""
    cutoff = _cutoff(now, retention_days)
    results: list[CleanupItem] = []
    targets = [
        (
            "password_reset_tokens",
            PasswordResetToken,
            or_(
                PasswordResetToken.expires_at < cutoff,
                PasswordResetToken.used_at < cutoff,
            ),
        ),
        (
            "email_verification_tokens",
            EmailVerificationToken,
            or_(
                EmailVerificationToken.expires_at < cutoff,
                EmailVerificationToken.used_at < cutoff,
            ),
        ),
        (
            "token_revocations",
            TokenRevocation,
            TokenRevocation.expires_at < cutoff,
        ),
        (
            "auth_sessions",
            AuthSession,
            or_(
                AuthSession.expires_at < cutoff,
                AuthSession.revoked_at < cutoff,
            ),
        ),
    ]

    for label, model, condition in targets:
        count = _count(db, model, condition)
        samples = [
            str(value)
            for value in db.scalars(
                select(model.id).where(condition).order_by(model.id).limit(10)
            )
        ]
        _delete_rows(db, model, condition, dry_run)
        results.append(
            CleanupItem(label=label, count=count, samples=samples)
        )
    return results


def cleanup_audit_logs(
    db: Session, now: datetime, retention_days: int, dry_run: bool
) -> CleanupItem:
    cutoff = _cutoff(now, retention_days)
    condition = AuditLog.created_at < cutoff
    count = _count(db, AuditLog, condition)
    samples = [
        str(value)
        for value in db.scalars(
            select(AuditLog.id).where(condition).order_by(AuditLog.id).limit(10)
        )
    ]
    _delete_rows(db, AuditLog, condition, dry_run)
    return CleanupItem(label="audit_logs", count=count, samples=samples)


def cleanup_soft_deleted_accounts(
    db: Session, now: datetime, retention_days: int, dry_run: bool
) -> CleanupItem:
    """清理到期软删除账号的行行程/会话/验证令牌，保留用户行与订单。"""
    cutoff = _cutoff(now, retention_days)
    user_ids = list(
        db.scalars(
            select(User.id).where(
                User.deleted_at.is_not(None), User.deleted_at < cutoff
            )
        )
    )
    if not user_ids:
        return CleanupItem(
            label="soft_deleted_accounts",
            count=0,
            detail="没有到期账号",
        )

    itinerary_ids = select(Itinerary.id).where(Itinerary.user_id.in_(user_ids))
    conditions = [
        ("itinerary_days", ItineraryDay, ItineraryDay.itinerary_id.in_(itinerary_ids)),
        ("itineraries", Itinerary, Itinerary.user_id.in_(user_ids)),
        ("auth_sessions", AuthSession, AuthSession.user_id.in_(user_ids)),
        (
            "password_reset_tokens",
            PasswordResetToken,
            PasswordResetToken.user_id.in_(user_ids),
        ),
        (
            "email_verification_tokens",
            EmailVerificationToken,
            EmailVerificationToken.user_id.in_(user_ids),
        ),
    ]
    total = 0
    detail_parts: list[str] = []
    for label, model, condition in conditions:
        count = _count(db, model, condition)
        total += count
        if count:
            detail_parts.append(f"{label}={count}")
        _delete_rows(db, model, condition, dry_run)

    kept_bookings = _count(
        db, Booking, Booking.user_id.in_(user_ids)
    )
    return CleanupItem(
        label="soft_deleted_accounts",
        count=total,
        detail=(
            f"到期账号 {len(user_ids)} 个；保留用户行与 {kept_bookings} 条订单"
        ),
        samples=[str(user_id) for user_id in user_ids[:10]],
    )


def cleanup_mail_files(
    now: datetime,
    preview_dir: Path,
    outbox: Path,
    retention_days: int,
    dry_run: bool,
) -> list[CleanupItem]:
    """删除过期邮件预览与 outbox 索引行（索引行含收件人与令牌）。"""
    cutoff = now - timedelta(days=retention_days)
    if cutoff.tzinfo is None:
        # outbox 的时间戳带时区；naive 输入按 UTC 解释后再比较。
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    cutoff_epoch = cutoff.timestamp()
    results: list[CleanupItem] = []

    preview_files: list[Path] = []
    if preview_dir.exists():
        preview_files = [
            path
            for path in preview_dir.glob("*.eml")
            if path.is_file() and path.stat().st_mtime < cutoff_epoch
        ]
    freed = sum(path.stat().st_size for path in preview_files)
    if preview_files and not dry_run:
        for path in preview_files:
            path.unlink(missing_ok=True)
    results.append(
        CleanupItem(
            label="mail_preview_files",
            count=len(preview_files),
            freed_bytes=freed,
            samples=[path.name for path in preview_files[:10]],
        )
    )

    removed_lines = 0
    outbox_size = 0
    if outbox.exists():
        lines = outbox.read_text(encoding="utf-8").splitlines()
        kept: list[str] = []
        for line in lines:
            stamp = line.split("\t", 1)[0]
            try:
                parsed = datetime.fromisoformat(stamp)
            except ValueError:
                # 无法解析的行保守保留，避免误删人工添加的内容。
                kept.append(line)
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed >= cutoff:
                kept.append(line)
            else:
                removed_lines += 1
                outbox_size += len(line.encode("utf-8")) + 1
        if removed_lines and not dry_run:
            outbox.write_text(
                "\n".join(kept) + ("\n" if kept else ""), encoding="utf-8"
            )
    results.append(
        CleanupItem(
            label="mail_outbox_lines",
            count=removed_lines,
            freed_bytes=outbox_size,
        )
    )
    return results


def cleanup_upload_temp_files(
    now: datetime,
    upload_dir: Path,
    retention_days: int,
    dry_run: bool,
) -> CleanupItem:
    """只清理明确的临时文件后缀；最终上传的图片不会被自动删除。"""
    cutoff_epoch = (now - timedelta(days=retention_days)).timestamp()
    files: list[Path] = []
    if upload_dir.exists():
        files = [
            path
            for path in upload_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in TEMP_UPLOAD_SUFFIXES
            and path.stat().st_mtime < cutoff_epoch
        ]
    freed = sum(path.stat().st_size for path in files)
    if files and not dry_run:
        for path in files:
            path.unlink(missing_ok=True)
    return CleanupItem(
        label="upload_temp_files",
        count=len(files),
        freed_bytes=freed,
        samples=[path.name for path in files[:10]],
    )
