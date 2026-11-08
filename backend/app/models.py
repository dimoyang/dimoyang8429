"""ORM 模型：覆盖 P1 端点所需实体。"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """SQLite DateTime 保存 naive UTC；用 timezone-aware now 避免 utcnow 弃用。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    # 角色：user（普通用户）/ staff（员工，可查看并流转订单）。
    # 只能通过服务端白名单或管理脚本授予，注册接口不接受客户端指定。
    role: Mapped[str] = mapped_column(
        String(20), default="user", server_default="user"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # 令牌版本：改密/重置/注销时自增，使已签发的 access/refresh 一并失效。
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    # 软删除标记：保留用户行以维持订单外键，同时禁止登录。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 邮箱验证时间：为空表示未验证。当前不阻断登录，只作为状态返回给前端引导。
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")

    @property
    def email_verified(self) -> bool:
        """供响应模型直接读取的派生字段。"""
        return self.email_verified_at is not None


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    name_en: Mapped[str] = mapped_column(String(160), default="")
    level: Mapped[str] = mapped_column(String(40), default="")

    packages: Mapped[list["MedicalPackage"]] = relationship(back_populates="hospital")


class MedicalPackage(Base):
    __tablename__ = "medical_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    name_en: Mapped[str] = mapped_column(String(160), default="")
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8))
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    image_url: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    description_en: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(60), default="")
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id"))
    # 上下架开关：false 时不出现在公开列表，也不能被新预约引用。
    # 已存在的历史订单不受影响（订单金额是下单时的快照）。
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )

    hospital: Mapped[Hospital] = relationship(back_populates="packages")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # 用户订单常按状态查询；复合索引前缀也能服务仅按 user_id 的查询。
        Index("ix_bookings_user_status", "user_id", "status"),
        # 员工列表：按状态过滤 + 按创建时间倒序。
        Index("ix_bookings_status_created_at", "status", "created_at"),
        # 员工列表不筛选状态时的全局时间排序。
        Index("ix_bookings_created_at", "created_at"),
        # 并发兜底：同一用户、套餐、预约时间只允许一个 pending 订单。
        # 只约束 pending，因此取消后可以重新预约同一时段。
        Index(
            "uq_bookings_pending_slot",
            "user_id",
            "package_id",
            "appointment_date",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    package_id: Mapped[int] = mapped_column(ForeignKey("medical_packages.id"))
    appointment_date: Mapped[datetime] = mapped_column(DateTime)
    contact_name: Mapped[str] = mapped_column(String(120))
    contact_phone: Mapped[str] = mapped_column(String(40))
    contact_email: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str] = mapped_column(Text, default="")
    need_translator: Mapped[bool] = mapped_column(Boolean, default=False)
    need_accommodation: Mapped[bool] = mapped_column(Boolean, default=False)
    need_pickup: Mapped[bool] = mapped_column(Boolean, default=False)
    total_price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # 状态时间戳：分别记录确认、取消、完成的时刻，便于对账与审计。
    # 迁移前的历史行留空（无法回溯真实时间），巡检脚本会单独列出。
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    user: Mapped[User] = relationship(back_populates="bookings")
    package: Mapped["MedicalPackage"] = relationship()

    @property
    def package_name(self) -> str:
        return self.package.name if self.package is not None else ""

    @property
    def package_name_en(self) -> str:
        return self.package.name_en if self.package is not None else ""


class Destination(Base):
    """目的地：字段与 Flutter Destination 模型保持一致。"""

    __tablename__ = "destinations"

    # 使用与前端一致的 slug（如 beijing），便于离线内容与本地收藏对齐。
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    name_en: Mapped[str] = mapped_column(String(120))
    tagline: Mapped[str] = mapped_column(String(200), default="")
    image_url: Mapped[str] = mapped_column(String(500), default="")
    search_terms: Mapped[list[str]] = mapped_column(JSON, default=list)
    best_season: Mapped[str] = mapped_column(String(80), default="")
    suggest_days: Mapped[str] = mapped_column(String(40), default="")
    intro: Mapped[str] = mapped_column(Text, default="")
    experiences: Mapped[list[dict]] = mapped_column(JSON, default=list)
    tips: Mapped[list[str]] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Itinerary(Base):
    __tablename__ = "itineraries"
    __table_args__ = (
        # 列表按用户过滤并按出发日期排序；前缀可服务仅按 user_id 的查询。
        Index("ix_itineraries_user_start", "user_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    # 行程整体涉及的目的地；每日安排见 ItineraryDay。
    destination_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    days: Mapped[list["ItineraryDay"]] = relationship(
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryDay.day_number",
    )


class ItineraryDay(Base):
    __tablename__ = "itinerary_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    itinerary_id: Mapped[int] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"), index=True
    )
    day_number: Mapped[int] = mapped_column(Integer)
    destination_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")

    itinerary: Mapped[Itinerary] = relationship(back_populates="days")


class TokenRevocation(Base):
    """已吊销的令牌（按 jti）。持久化在数据库，重启后仍然有效。"""

    __tablename__ = "token_revocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_type: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PasswordResetToken(Base):
    """忘记密码令牌：只存 SHA-256 摘要，短时效且一次性。"""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EmailVerificationToken(Base):
    """邮箱验证令牌：只存 SHA-256 摘要，短时效且一次性。"""

    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuthSession(Base):
    """一次登录对应的设备会话；refresh token 轮换时沿用同一行。

    与 TokenRevocation 的分工：
    - `token_revocations` 是“已吊销令牌”的反向名单，只记录 jti，供 access/refresh
      校验使用，不含设备信息；
    - `auth_sessions` 是“有效会话”的正向登记，保存创建时间、最后使用时间和
      粗略来源，用于会话列表与单设备吊销。
    两者职责不同，不合并；否则列表查询要先扫吊销表，且无法表达“会话仍有效但
    access token 已单独登出”。
    """

    __tablename__ = "auth_sessions"
    __table_args__ = (
        # 列表查询按用户过滤未吊销会话；前缀也覆盖仅按 user_id 的查询。
        Index("ix_auth_sessions_user_active", "user_id", "revoked_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # 对客户端暴露的会话标识（随机串），同时写入 access/refresh token 的 sid。
    sid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # 当前有效的 refresh token jti；轮换后更新为新值。
    refresh_jti: Mapped[str] = mapped_column(String(64))
    # 粗略来源：只保留截断后的 User-Agent 与打码 IP，不存原始请求头。
    user_agent: Mapped[str] = mapped_column(String(200), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    """操作审计：记录谁、何时、对什么做了什么、改前改后是什么。

    目前覆盖：员工查看订单详情、员工流转订单状态、员工改价/删除内容、
    用户取消订单、用户导出数据。列表类只读查询不写，避免噪声。
    `details` 存 JSON（`{"before": {...}, "after": {...}}`），实体 id 统一
    用字符串保存，兼容整数主键与目的地 slug。
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index(
            "ix_audit_logs_entity",
            "entity_type",
            "entity_id",
            "created_at",
        ),
        # 审计查询接口按操作类型 + 时间范围过滤。
        Index(
            "ix_audit_logs_action_created_at",
            "action",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    # 冗余保存操作者邮箱：用户后续被匿名化后仍能还原当时的操作人。
    actor_email: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(64))
    # 变更前后快照；只读访问（如查看详情）为空。
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ContentTranslation(Base):
    """多语言内容：按实体 + 字段存译文，避免为每种语言平铺列。

    en / zh 仍以业务表的 name/name_en 等列为主；本表存放 de/fr 等额外语言。
    回退顺序为 请求语言 → en → zh。

    唯一约束 (entity_type, entity_id, lang, field) 的索引前缀已经覆盖
    (entity_type, entity_id, lang) 查询，因此不再单独建重复索引。
    """

    __tablename__ = "content_translations"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "lang",
            "field",
            name="uq_content_translation_entity_lang_field",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int] = mapped_column(Integer)
    lang: Mapped[str] = mapped_column(String(8))
    field: Mapped[str] = mapped_column(String(60))
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
