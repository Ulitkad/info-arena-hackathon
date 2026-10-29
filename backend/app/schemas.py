from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class AuthInput(Input):
    init_data: str = Field(min_length=1, max_length=16384)
    invite_token: str | None = Field(default=None, max_length=100)


class DevAuth(Input):
    persona: Literal["student", "teacher", "manager", "admin", "friend"] = "student"


class NameInput(Input):
    name: str = Field(min_length=1, max_length=100)


class SubjectInput(NameInput):
    color: str = Field(default="#0284c7", pattern=r"^#[0-9a-fA-F]{6}$")


class GroupSubjects(Input):
    subject_ids: list[int] = Field(max_length=100)


class Load(Input):
    subject_id: int
    group_id: int


class InviteInput(Input):
    role: Literal["STUDENT", "TEACHER", "MANAGER"]
    group_id: int | None = None
    loads: list[Load] = Field(default_factory=list, max_length=100)


class TokenInput(Input):
    token: str = Field(min_length=20, max_length=100)


class UserLookup(Input):
    query: str = Field(min_length=1, max_length=100)


class AssignUser(UserLookup):
    role: Literal["ADMIN", "MANAGER", "TEACHER", "STUDENT"]
    group_id: int | None = None
    loads: list[Load] = Field(default_factory=list, max_length=100)


class Moderation(Input):
    approve: bool


class ContentInput(Input):
    text: str = Field(default="", max_length=10000)
    files: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def has_content(self):
        if not self.text and not self.files:
            raise ValueError("Добавьте текст или хотя бы один файл")
        return self


class HomeworkInput(ContentInput):
    title: str = Field(min_length=1, max_length=160)
    subject_id: int
    group_ids: list[int] = Field(min_length=1, max_length=100)
    deadline: datetime
    optional: bool = False

    @field_validator("deadline")
    @classmethod
    def utc_date(cls, value):
        if value.tzinfo is None:
            raise ValueError("Дата должна содержать часовой пояс")
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class ReviewInput(Input):
    approve: bool
    feedback: str = Field(default="", max_length=2000)


class EventInput(Input):
    title: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=10000)
    subject_id: int
    group_ids: list[int] = Field(min_length=1, max_length=100)
    kind: Literal["DUTY", "OTHER"] = "OTHER"
    points: int = Field(default=2, ge=1, le=30)
    min_participants: int = Field(ge=1, le=10000)
    max_participants: int = Field(ge=1, le=10000)
    closes_at: datetime

    @field_validator("closes_at")
    @classmethod
    def utc_date(cls, value):
        if value.tzinfo is None:
            raise ValueError("Дата должна содержать часовой пояс")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    @model_validator(mode="after")
    def valid_event(self):
        if self.min_participants > self.max_participants:
            raise ValueError("Минимум участников не может превышать максимум")
        if self.kind == "DUTY":
            self.title, self.points = "Дежурство", 2
        elif not self.title:
            raise ValueError("Укажите название мероприятия")
        return self


class ParticipantInput(Input):
    user_id: int


class DuelInput(Input):
    opponent_id: int
    duration: Literal["1d", "3d", "7d", "1m"]
    subject_id: int | None = None


class RewardInput(Input):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["TITLE", "FRAME", "BADGE"]
    threshold: int = Field(ge=1, le=100000)
    subject_id: int | None = None
    asset_url: str | None = Field(default=None, max_length=200)
    icon: Literal["award", "sparkles", "crown", "flame", "swords", "star", "shield"] = "award"


class ProfileInput(Input):
    active_title_id: int | None = None
    active_frame_id: int | None = None
    showcase: list[int] = Field(default_factory=list, max_length=3)


class NotificationIds(Input):
    ids: list[int] = Field(min_length=1, max_length=100)


class PhoneInput(Input):
    auth_date: int
    phone: str = Field(max_length=30)
    hash: str = Field(pattern="^[a-fA-F0-9]{64}$")
