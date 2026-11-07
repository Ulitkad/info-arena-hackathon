"""Data-access primitives.

Repositories contain reusable query composition only; authorization and state
changes remain in services/use-cases.
"""

from .notifications import NotificationRepository
from .users import UserRepository

__all__ = ["NotificationRepository", "UserRepository"]
