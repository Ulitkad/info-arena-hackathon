"""Shared Pydantic input configuration."""

from pydantic import BaseModel, ConfigDict


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
