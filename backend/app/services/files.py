"""Use-cases for validating uploaded media ownership."""

from sqlalchemy import select

from ..models import Upload
from ..security import fail


async def validate_files(db, user, files):
    for url in set(files):
        upload = await db.scalar(select(Upload).where(Upload.url == url, Upload.owner_id == user.id))
        if not upload:
            fail("Можно прикреплять только собственные загруженные файлы", 403)
