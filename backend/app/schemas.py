"""请求/响应模型：字段名与 Flutter 前端契约严格一致。"""

import re
from datetime import date, datetime, timezone

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class TokenResponse(BaseModel):
    access_token: str
    # 新增字段；现有前端会忽略它，保持向后兼容。
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    full_name: str | None = None
    preferred_language: str = Field(default="en", max_length=10)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    phone: str | None
    preferred_language: str


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


class PackagePage(BaseModel):
    items: list[PackageResponse]
    total: int
    page: int
    page_size: int
    pages: int


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
