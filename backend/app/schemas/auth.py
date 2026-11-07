"""Authentication and profile DTOs."""

from typing import Literal

from pydantic import Field

from .common import Input


class AuthInput(Input):
    init_data: str = Field(min_length=1, max_length=16384)
    invite_token: str | None = Field(default=None, max_length=100)


class DevAuth(Input):
    persona: Literal["student", "teacher", "manager", "admin", "friend"] = "student"


class TokenInput(Input):
    token: str = Field(min_length=20, max_length=100)


class ProfileInput(Input):
    active_title_id: int | None = None
    active_frame_id: int | None = None
    showcase: list[int] = Field(default_factory=list, max_length=3)


class PhoneInput(Input):
    auth_date: int
    phone: str = Field(max_length=30)
    hash: str = Field(pattern="^[a-fA-F0-9]{64}$")
