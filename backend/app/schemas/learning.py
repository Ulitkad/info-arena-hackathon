"""Homework and event DTOs."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .common import Input


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
