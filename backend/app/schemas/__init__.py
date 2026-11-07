"""Public DTO namespace for API routes.

Domain modules keep validation concerns local while this facade preserves the
existing ``schemas as s`` imports used by the routers.
"""

from .auth import AuthInput, DevAuth, PhoneInput, ProfileInput, TokenInput
from .common import Input
from .learning import ContentInput, EventInput, HomeworkInput, ParticipantInput, ReviewInput
from .notifications import NotificationIds
from .organization import (
    AssignUser, GroupSubjects, InviteInput, Load, Moderation, NameInput, RewardInput, SubjectInput, TeacherLoads,
    UserLookup,
)
from .social import DuelInput

__all__ = [
    "AssignUser", "AuthInput", "ContentInput", "DevAuth", "DuelInput", "EventInput", "GroupSubjects",
    "HomeworkInput", "Input", "InviteInput", "Load", "Moderation", "NameInput", "NotificationIds",
    "ParticipantInput", "PhoneInput", "ProfileInput", "ReviewInput", "RewardInput", "SubjectInput",
    "TeacherLoads", "TokenInput", "UserLookup",
]
