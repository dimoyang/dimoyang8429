#!/usr/bin/env python3
"""员工角色管理：显式授予/撤销 staff，或创建员工账号。

示例（在 backend 目录下执行）：
    .\\.venv\\Scripts\\python.exe scripts\\manage_staff.py --email staff@example.com
    .\\.venv\\Scripts\\python.exe scripts\\manage_staff.py --email staff@example.com --password "Staff123456"
    .\\.venv\\Scripts\\python.exe scripts\\manage_staff.py --email staff@example.com --revoke

授予后员工用原密码登录即可；白名单（MEDITOUR_STAFF_EMAILS）只是另一种引导方式，
不会自动创建账号。撤销立即生效，无需等待令牌过期。
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password
from app.staff import grant_staff, revoke_staff


def main() -> int:
    parser = argparse.ArgumentParser(description="授予或撤销员工角色")
    parser.add_argument("--email", required=True, help="目标账号邮箱")
    parser.add_argument(
        "--password",
        help="账号不存在时用该密码创建；已存在时忽略（不会改密）",
    )
    parser.add_argument(
        "--name", default=None, help="创建账号时使用的显示名（可选）"
    )
    parser.add_argument(
        "--revoke", action="store_true", help="撤销员工角色，降级为普通用户"
    )
    args = parser.parse_args()

    email = args.email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))

        if user is None:
            if args.revoke:
                print(f"未找到账号 {email}，无需撤销。")
                return 1
            if not args.password:
                print(
                    f"未找到账号 {email}。请先注册，或用 --password 直接创建。"
                )
                return 1
            user = User(
                email=email,
                password_hash=hash_password(args.password),
                full_name=args.name,
                role="staff",
            )
            db.add(user)
            db.commit()
            print(f"已创建员工账号 {email}（role=staff）。")
            return 0

        if args.revoke:
            revoke_staff(db, email)
            db.commit()
            print(f"已撤销 {email} 的员工角色（role=user）。")
            return 0

        grant_staff(db, email)
        # 白名单场景下，删除名单后需再次撤销才是完整的回收流程。
        db.commit()
        print(f"已授予 {email} 员工角色（role=staff）。")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
