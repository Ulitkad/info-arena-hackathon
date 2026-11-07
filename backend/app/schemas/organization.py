"""Institution, membership and reward DTOs."""

from typing import Literal

from pydantic import Field

from .common import Input


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


class UserLookup(Input):
    query: str = Field(min_length=1, max_length=100)


class AssignUser(UserLookup):
    role: Literal["ADMIN", "MANAGER", "TEACHER", "STUDENT"]
    group_id: int | None = None
    loads: list[Load] = Field(default_factory=list, max_length=100)


class TeacherLoads(Input):
    loads: list[Load] = Field(min_length=1, max_length=100)


class Moderation(Input):
    approve: bool


class RewardInput(Input):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["TITLE", "FRAME", "BADGE", "CUSTOM"]
    threshold: int = Field(ge=1, le=100000)
    subject_id: int | None = None
    asset_url: str | None = Field(default=None, max_length=200)
    icon: Literal["award", "sparkles", "crown", "flame", "swords", "star", "shield"] = "award"
    frame_style: Literal["skyline", "aurora", "sunset", "mint", "lavender", "flame", "ocean", "orbit", "pixel", "constellation"] | None = None
