"""请求/响应模型：字段名与 Flutter 前端契约严格一致。"""

import re
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.config import settings


class TokenResponse(BaseModel):
    access_token: str
    # 新增字段；现有前端会忽略它，保持向后兼容。
    refresh_token: str
    token_type: str = "bearer"
    # 新增字段：客户端可据此决定是否展示员工入口；普通用户为 user。
    role: str = "user"
    # 新增字段：邮箱验证状态。当前不阻断登录，客户端可据此展示引导。
    email_verified: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    full_name: str | None = None
    preferred_language: str = Field(default="en", max_length=10)


class EmailVerificationConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class SessionResponse(BaseModel):
    """会话列表项：只暴露可识别设备的元信息，不返回任何令牌。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    last_used_at: datetime
    user_agent: str
    ip: str
    current: bool = False


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=6, max_length=72)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=72)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    phone: str | None
    preferred_language: str
    role: str
    # 派生字段：users.email_verified_at 是否已写入。当前不阻断登录。
    email_verified: bool = False


class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_en: str
    level: str


class PackageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_en: str
    price: float
    currency: str
    duration_days: int
    image_url: str
    description: str
    description_en: str
    category: str
    hospital_id: int
    is_active: bool


class PackagePage(BaseModel):
    items: list[PackageResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PackageCreate(BaseModel):
    """员工创建套餐。currency 缺省取全局单一币种配置。"""

    name: str = Field(min_length=1, max_length=160)
    name_en: str = Field(default="", max_length=160)
    price: float = Field(gt=0)
    currency: str = Field(
        default_factory=lambda: settings.DEFAULT_CURRENCY,
        min_length=3,
        max_length=8,
    )
    duration_days: int = Field(default=1, ge=1)
    image_url: str = Field(default="", max_length=500)
    description: str = ""
    description_en: str = ""
    category: str = Field(default="", max_length=60)
    hospital_id: int
    is_active: bool = True


class PackageUpdate(BaseModel):
    """员工局部更新套餐；未提供的字段保持不变。"""

    name: str | None = Field(default=None, min_length=1, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    price: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    duration_days: int | None = Field(default=None, ge=1)
    image_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    description_en: str | None = None
    category: str | None = Field(default=None, max_length=60)
    hospital_id: int | None = None
    is_active: bool | None = None


class HospitalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    name_en: str = Field(default="", max_length=160)
    level: str = Field(default="", max_length=40)


class HospitalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    name_en: str | None = Field(default=None, max_length=160)
    level: str | None = Field(default=None, max_length=40)


class HospitalPage(BaseModel):
    items: list[HospitalResponse]
    total: int
    page: int
    page_size: int
    pages: int


class UploadResponse(BaseModel):
    """上传结果：url 可直接给前端展示，path 是站内相对路径。"""

    url: str
    path: str
    filename: str
    size: int
    content_type: str


_PHONE_SEPARATORS = re.compile(r"[\s\-().]")
_PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")


class BookingCreate(BaseModel):
    package_id: int
    appointment_date: datetime
    contact_name: str = Field(min_length=1, max_length=120)
    contact_phone: str = Field(max_length=32)
    contact_email: EmailStr
    # notes 可能包含健康信息，限制长度以降低泄露与滥用风险。
    notes: str = Field(default="", max_length=2000)
    need_translator: bool = False
    need_accommodation: bool = False
    need_pickup: bool = False

    @field_validator("appointment_date")
    @classmethod
    def require_future_datetime(cls, value: datetime) -> datetime:
        """前端按 naive ISO 发送；带时区时先换算为 UTC，再要求必须是未来时间。"""
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        if value <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("appointment_date must be in the future")
        return value

    @field_validator("contact_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("contact_name must not be blank")
        return value

    @field_validator("contact_phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = _PHONE_SEPARATORS.sub("", value.strip())
        if not _PHONE_PATTERN.fullmatch(normalized):
            raise ValueError("contact_phone must be 7-15 digits with an optional leading +")
        return normalized

    @field_validator("contact_email")
    @classmethod
    def normalize_contact_email(cls, value: str) -> str:
        return value.strip().lower()


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    package_id: int
    package_name: str
    package_name_en: str
    appointment_date: datetime
    total_price: float
    currency: str
    status: str
    created_at: datetime
    # 状态时间戳：未发生对应流转时为空，前端可据此展示时间线。
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None

    @field_serializer("appointment_date")
    def serialize_appointment_date(self, value: datetime) -> str:
        """预约时间按前端传入的 naive 墙钟时间返回 ISO 8601。"""
        return value.isoformat(timespec="seconds")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        """创建时间按 UTC 返回，带 Z 后缀，避免客户端按本地时间解析。"""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")

    @field_serializer("confirmed_at", "cancelled_at", "completed_at")
    def serialize_status_times(self, value: datetime | None) -> str | None:
        return None if value is None else _serialize_utc_datetime(value)


def _serialize_local_datetime(value: datetime) -> str:
    """预约时间按用户填写的 naive 墙钟时间返回。"""
    return value.isoformat(timespec="seconds")


def _serialize_utc_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def mask_phone(value: str) -> str:
    """列表页只展示必要字符，完整号码需进入详情（并记录审计）。"""
    phone = value.strip()
    if not phone:
        return ""
    if len(phone) <= 4:
        return "*" * len(phone)
    keep = 3 if len(phone) >= 8 else 1
    return f"{phone[:keep]}****{phone[-2:]}"


def mask_email(value: str) -> str:
    local, _, domain = value.strip().partition("@")
    if not domain:
        return "****"
    return f"{local[:1]}****@{domain}"


class StaffBookingListItem(BaseModel):
    """员工订单列表项：不含备注，联系方式仅返回打码值。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    user_id: int
    package_id: int
    package_name: str
    package_name_en: str
    appointment_date: datetime
    total_price: float
    currency: str
    status: str
    created_at: datetime
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    contact_name: str
    contact_phone: str
    contact_email: str

    @field_serializer("appointment_date")
    def serialize_appointment_date(self, value: datetime) -> str:
        return _serialize_local_datetime(value)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _serialize_utc_datetime(value)

    @field_serializer("confirmed_at", "cancelled_at", "completed_at")
    def serialize_status_times(self, value: datetime | None) -> str | None:
        return None if value is None else _serialize_utc_datetime(value)

    @field_serializer("contact_phone")
    def serialize_contact_phone(self, value: str) -> str:
        return mask_phone(value)

    @field_serializer("contact_email")
    def serialize_contact_email(self, value: str) -> str:
        return mask_email(value)


class StaffBookingDetail(BaseModel):
    """员工订单详情：含完整联系方式与备注，读取时会写入审计日志。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    user_id: int
    package_id: int
    package_name: str
    package_name_en: str
    appointment_date: datetime
    total_price: float
    currency: str
    status: str
    created_at: datetime
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    contact_name: str
    contact_phone: str
    contact_email: str
    notes: str
    need_translator: bool
    need_accommodation: bool
    need_pickup: bool

    @field_serializer("appointment_date")
    def serialize_appointment_date(self, value: datetime) -> str:
        return _serialize_local_datetime(value)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _serialize_utc_datetime(value)

    @field_serializer("confirmed_at", "cancelled_at", "completed_at")
    def serialize_status_times(self, value: datetime | None) -> str | None:
        return None if value is None else _serialize_utc_datetime(value)


class StaffBookingPage(BaseModel):
    items: list[StaffBookingListItem]
    total: int
    page: int
    page_size: int
    pages: int


class BookingStatusUpdate(BaseModel):
    """员工可执行的订单状态变更目标。

    只接受 confirmed / completed / cancelled；具体能否从当前状态流转由
    服务端判断：非法目标值属于请求格式错误（422），非法流转属于状态
    冲突（409）。completed 与 cancelled 是终态，不能再退回 pending。
    """

    status: Literal["confirmed", "completed", "cancelled"]


class AuditLogItem(BaseModel):
    """审计记录：谁、何时、对什么做了什么、改前改后是什么。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int
    actor_email: str
    action: str
    entity_type: str
    entity_id: str
    details: dict | None = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _serialize_utc_datetime(value)


class AuditLogPage(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int
    pages: int


class DestinationExperience(BaseModel):
    icon: str = ""
    title: str
    description: str = ""


class DestinationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_en: str
    tagline: str
    image_url: str
    search_terms: list[str] = Field(default_factory=list)
    best_season: str
    suggest_days: str
    intro: str
    experiences: list[DestinationExperience] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)


class StaffDestinationResponse(DestinationResponse):
    """员工侧额外返回排序值，便于调整首页展示顺序。"""

    sort_order: int


class DestinationCreate(BaseModel):
    """新建目的地。id 是与前端一致的 slug，创建后不可修改。"""

    id: str = Field(
        min_length=1,
        max_length=40,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
        description="slug，仅小写字母、数字与连字符，例如 beijing",
    )
    name: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=120)
    tagline: str = Field(default="", max_length=200)
    image_url: str = Field(default="", max_length=500)
    search_terms: list[str] = Field(default_factory=list)
    best_season: str = Field(default="", max_length=80)
    suggest_days: str = Field(default="", max_length=40)
    intro: str = ""
    experiences: list[DestinationExperience] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    sort_order: int = 0


class DestinationUpdate(BaseModel):
    """局部更新目的地；不接受 id，slug 是稳定标识。"""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    name_en: str | None = Field(default=None, min_length=1, max_length=120)
    tagline: str | None = Field(default=None, max_length=200)
    image_url: str | None = Field(default=None, max_length=500)
    search_terms: list[str] | None = None
    best_season: str | None = Field(default=None, max_length=80)
    suggest_days: str | None = Field(default=None, max_length=40)
    intro: str | None = None
    experiences: list[DestinationExperience] | None = None
    tips: list[str] | None = None
    sort_order: int | None = None


class DestinationPage(BaseModel):
    items: list[StaffDestinationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ItineraryDayPayload(BaseModel):
    day_number: int = Field(ge=1)
    destination_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class ItineraryWrite(BaseModel):
    """创建与全量更新共用的请求体。"""

    title: str = Field(min_length=1, max_length=160)
    start_date: date
    end_date: date
    destination_ids: list[str] = Field(default_factory=list)
    days: list[ItineraryDayPayload] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def validate_plan(self) -> "ItineraryWrite":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        if not self.destination_ids:
            raise ValueError("destination_ids must not be empty")

        day_count = (self.end_date - self.start_date).days + 1
        day_numbers = [day.day_number for day in self.days]
        if len(day_numbers) != len(set(day_numbers)):
            raise ValueError("day_number must be unique")
        if any(number > day_count for number in day_numbers):
            raise ValueError("day_number exceeds trip length")
        return self


class ItineraryDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_number: int
    destination_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class ItineraryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    start_date: date
    end_date: date
    destination_ids: list[str] = Field(default_factory=list)
    days: list[ItineraryDayResponse] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime
    updated_at: datetime
