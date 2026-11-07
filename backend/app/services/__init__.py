"""Application use-cases grouped by business domain.

The package keeps the old ``app.services`` import surface deliberately small so
routes and background jobs can migrate incrementally. New code should import
from the domain module it needs instead of adding unrelated functions here.
"""

from .access import accept_invite, activate_student, create_invite, find_user, validate_assignments, validate_load
from .achievements import achievement_progress, evaluate_achievements, seed_all_achievements, seed_achievements
from .duels import duel_scores, duel_slots, finish_duel, start_duel
from .events import complete_event, event_join, event_owner, student_access
from .files import validate_files
from .notifications import notify
from .progress import award, init_progress, seed_rewards, unlock_rewards
from .serializers import public_user, row

__all__ = [
    "accept_invite", "activate_student", "achievement_progress", "award", "complete_event", "create_invite",
    "duel_scores", "duel_slots", "event_join", "event_owner", "find_user", "finish_duel",
    "evaluate_achievements", "init_progress", "notify", "public_user", "row", "seed_all_achievements", "seed_achievements", "seed_rewards", "start_duel",
    "student_access", "unlock_rewards", "validate_assignments", "validate_files", "validate_load",
]
