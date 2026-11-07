"""Notification DTOs."""

from pydantic import Field

from .common import Input


class NotificationIds(Input):
    ids: list[int] = Field(min_length=1, max_length=100)
