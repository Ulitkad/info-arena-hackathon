"""Social and duel DTOs."""

from typing import Literal

from .common import Input


class DuelInput(Input):
    opponent_id: int
    duration: Literal["1d", "3d", "7d", "1m"]
    subject_id: int | None = None
