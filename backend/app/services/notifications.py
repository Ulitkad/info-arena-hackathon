"""Notification creation use-case."""

from ..models import Notification


async def notify(db, user_id, title, body="", link="/"):
    db.add(Notification(user_id=user_id, title=title, body=body, link=link))
