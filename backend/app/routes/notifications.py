import asyncio

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas as s
from ..db import Session, session_dep
from ..models import Notification, User
from ..security import create_token, current_user, decode_token
from ..services import row

router = APIRouter()


@router.get("/api/notifications")
async def notifications(before: int | None = None, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    query = select(Notification).where(Notification.user_id == user.id)
    if before:
        query = query.where(Notification.id < before)
    items = (await db.scalars(query.order_by(Notification.id.desc()).limit(100))).all()
    unread = await db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.read.is_(False)))
    return {"items": [row(item) for item in items], "unread": unread,
            "next_before": items[-1].id if len(items) == 100 else None}


@router.post("/api/notifications/read-all")
async def read_all(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await db.execute(update(Notification).where(Notification.user_id == user.id).values(read=True, toasted=True))
    return {"ok": True}


@router.post("/api/notifications/{nid}/read")
async def read_one(nid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await db.execute(update(Notification).where(Notification.user_id == user.id, Notification.id == nid).values(read=True, toasted=True))
    return {"ok": True}


@router.post("/api/notifications/toasted")
async def toasted(data: s.NotificationIds, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await db.execute(update(Notification).where(Notification.user_id == user.id, Notification.id.in_(data.ids)).values(toasted=True))
    return {"ok": True}


@router.post("/api/ws-ticket")
async def ticket(user: User = Depends(current_user)):
    return {"ticket": create_token(user.id, audience="arena-ws", minutes=1)}


@router.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    try:
        payload = await asyncio.wait_for(ws.receive_json(), timeout=10)
        uid = decode_token(str(payload.get("ticket", "")), audience="arena-ws")
        async with Session() as db:
            if not await db.get(User, uid):
                await ws.close(code=4401)
                return
        cursor = 0
        while True:
            async with Session() as db:
                items = (await db.scalars(select(Notification).where(
                    Notification.user_id == uid, Notification.id > cursor,
                    Notification.toasted.is_(False), Notification.read.is_(False),
                ).order_by(Notification.id).limit(20))).all()
                unread = await db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == uid, Notification.read.is_(False)))
                data = {"type": "notifications", "items": [row(n) for n in items], "unread": unread}
                if items:
                    cursor = items[-1].id
            from fastapi.encoders import jsonable_encoder
            await ws.send_json(jsonable_encoder(data))
            # Receive client heartbeat, so disconnected sockets do not stay alive indefinitely.
            try:
                message = await asyncio.wait_for(ws.receive_text(), timeout=2)
                if message == "close":
                    break
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, HTTPException, asyncio.TimeoutError, ValueError, TypeError, AttributeError):
        try:
            await ws.close(code=4401)
        except RuntimeError:
            pass
