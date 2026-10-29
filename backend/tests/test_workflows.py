import asyncio
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.models import Duel, Friendship, Inventory, JoinRequest, PointLedger, Progress, User, now
from app.seed import seed_demo
from app.services import award, duel_scores, finish_duel


async def test_demo_seed_is_idempotent_and_scores_are_academic(arena):
    async with arena.sessions() as db:
        await seed_demo(db)
        await db.commit()
        assert await db.scalar(select(func.count()).select_from(Friendship)) == 2
        duel = await db.scalar(select(Duel))
        assert await duel_scores(db, duel) == (6, 4)
    for persona in ("student", "friend", "teacher", "manager", "admin"):
        response = await arena.client.post("/api/auth/dev", json={"persona": persona})
        assert response.status_code == 200, response.text


async def test_award_is_idempotent_and_unlocks_once(arena):
    async with arena.sessions() as db:
        student = await db.get(User, arena.users[900001].id)
        before = await db.scalar(select(Progress.points).where(Progress.user_id == student.id, Progress.scope == "general"))
        assert await award(db, student, 100, "HOMEWORK", 9999, "Тест", 1)
        assert not await award(db, student, 100, "HOMEWORK", 9999, "Тест", 1)
        assert await db.scalar(select(Progress.points).where(Progress.user_id == student.id, Progress.scope == "general")) == before + 100
        assert await db.scalar(select(func.count()).select_from(PointLedger).where(PointLedger.source_id == 9999)) == 1
        inventory = (await db.scalars(select(Inventory.reward_id).where(Inventory.user_id == student.id))).all()
        assert len(inventory) == len(set(inventory))


async def test_homework_revision_and_concurrent_approval_awards_once(arena):
    client, student, teacher = arena.client, arena.auth(900001), arena.auth(900003)
    tasks = (await client.get("/api/homework", headers=student)).json()
    task = next(h for h in tasks if not h["optional"] and h["subject_id"] == 1)
    submission = await client.post(f"/api/homework/{task['id']}/submit", headers=student, json={"text": "Решение", "files": []})
    assert submission.status_code == 200, submission.text
    sid = submission.json()["id"]
    revision = await client.post(f"/api/submissions/{sid}/review", headers=teacher, json={"approve": False, "feedback": "Уточни решение"})
    assert revision.status_code == 200
    retry = await client.post(f"/api/homework/{task['id']}/submit", headers=student, json={"text": "Исправление", "files": []})
    assert retry.status_code == 200
    results = await asyncio.gather(*[
        client.post(f"/api/submissions/{sid}/review", headers=teacher, json={"approve": True}) for _ in range(2)
    ])
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    async with arena.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(PointLedger).where(
            PointLedger.user_id == arena.users[900001].id, PointLedger.source_kind == "HOMEWORK", PointLedger.source_id == task["id"],
        )) == 1
    forbidden = await client.post(f"/api/submissions/{sid}/review", headers=student, json={"approve": True})
    assert forbidden.status_code == 403


async def test_student_invite_rotation_and_moderation(arena):
    client, manager = arena.client, arena.auth(900004)
    oid = arena.users[900004].organization_id
    group = arena.users[900001].group_id
    body = {"role": "STUDENT", "group_id": group}
    old = (await client.post(f"/api/organizations/{oid}/invites", headers=manager, json=body)).json()
    new = (await client.post(f"/api/organizations/{oid}/invites", headers=manager, json=body)).json()
    from app.security import create_token
    async with arena.sessions() as db:
        applicant = User(max_id=800001, display_name="Новый ученик")
        db.add(applicant)
        await db.commit()
        auth = {"Authorization": f"Bearer {create_token(applicant.id)}"}
    assert (await client.post("/api/invites/accept", headers=auth, json={"token": old["token"]})).status_code == 404
    for _ in range(2):
        response = await client.post("/api/invites/accept", headers=auth, json={"token": new["token"]})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "PENDING"
    requests = (await client.get(f"/api/organizations/{oid}/requests", headers=manager)).json()
    request = next(r for r in requests if r["student"]["max_id"] == 800001)
    assert (await client.post(f"/api/requests/{request['id']}/moderate", headers=manager, json={"approve": True})).status_code == 200
    assert (await client.get("/api/me", headers=auth)).json()["role"] == "STUDENT"
    async with arena.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(JoinRequest).where(JoinRequest.student_id == applicant.id)) == 1


async def test_event_capacity_blacklist_deadline_and_idempotency(arena):
    client, teacher, student, friend = arena.client, arena.auth(900003), arena.auth(900001), arena.auth(900002)
    group = arena.users[900001].group_id
    response = await client.post("/api/events", headers=teacher, json={
        "title": "Тестовое событие", "subject_id": 1, "group_ids": [group], "kind": "OTHER",
        "points": 3, "min_participants": 1, "max_participants": 1, "closes_at": (now() + timedelta(hours=1)).isoformat() + "Z",
    })
    assert response.status_code == 201, response.text
    eid = response.json()["id"]
    assert (await client.post(f"/api/events/{eid}/join", headers=student)).status_code == 200
    assert (await client.post(f"/api/events/{eid}/join", headers=friend)).status_code == 409
    assert (await client.delete(f"/api/events/{eid}/participants/{arena.users[900001].id}", headers=teacher)).status_code == 200
    assert (await client.post(f"/api/events/{eid}/join", headers=student)).status_code == 403
    assert (await client.post(f"/api/events/{eid}/join", headers=friend)).status_code == 200
    assert (await client.post(f"/api/events/{eid}/close", headers=teacher)).status_code == 200
    assert (await client.post(f"/api/events/{eid}/participants", headers=teacher, json={"user_id": arena.users[900001].id})).status_code == 409
    for _ in range(2):
        assert (await client.post(f"/api/events/{eid}/complete", headers=teacher)).status_code == 200
    async with arena.sessions() as db:
        assert await db.scalar(select(func.count()).select_from(PointLedger).where(PointLedger.source_kind == "EVENT", PointLedger.source_id == eid)) == 1


async def test_duel_completion_excludes_bonus_and_is_idempotent(arena):
    async with arena.sessions() as db:
        duel = await db.scalar(select(Duel))
        student = await db.get(User, duel.challenger_id)
        friend = await db.get(User, duel.opponent_id)
        await award(db, friend, 30, "DUEL", 9999, "Бонус")
        duel.ends_at = now() - timedelta(microseconds=1)
        assert await duel_scores(db, duel) == (6, 4)
        await finish_duel(db, duel)
        await finish_duel(db, duel)
        assert duel.winner_id == student.id
        assert student.duel_wins == 1
        assert await db.scalar(select(func.count()).select_from(PointLedger).where(PointLedger.source_kind == "DUEL", PointLedger.source_id == duel.id)) == 1


def test_alembic_on_clean_sqlite(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{(tmp_path / 'new-data' / 'migration.db').as_posix()}"}
    for args in (("upgrade", "head"), ("check",), ("downgrade", "base"), ("upgrade", "head")):
        result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=backend, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
