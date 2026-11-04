import hashlib
import hmac
import time
import asyncio

import pytest

from sqlalchemy import select

from app.models import Duel, Event, EventParticipant, GroupSubject, Invite, TeacherLoad, User
from app.security import create_token


async def applicant(arena, max_id):
    async with arena.sessions() as db:
        user = User(max_id=max_id, display_name=f"Участник {max_id}")
        db.add(user)
        await db.commit()
        return user, {"Authorization": f"Bearer {create_token(user.id)}"}


async def test_staff_invite_is_single_use_and_keeps_exact_loads(arena):
    client, manager = arena.client, arena.auth(900004)
    oid = arena.users[900004].organization_id
    teacher, first = await applicant(arena, 810001)
    _, second = await applicant(arena, 810002)
    loads = [{"subject_id": 1, "group_id": 1}, {"subject_id": 2, "group_id": 2}]
    invite = await client.post(f"/api/organizations/{oid}/invites", headers=manager, json={"role": "TEACHER", "loads": loads})
    assert invite.status_code == 200, invite.text
    token = {"token": invite.json()["token"]}
    assert (await client.post("/api/invites/accept", headers=first, json=token)).status_code == 200
    assert (await client.post("/api/invites/accept", headers=first, json=token)).status_code == 409
    assert (await client.post("/api/invites/accept", headers=second, json=token)).status_code == 409
    catalog = (await client.get(f"/api/organizations/{oid}/catalog", headers=manager)).json()
    actual = [{k: row[k] for k in ("subject_id", "group_id")} for row in catalog["loads"] if row["teacher_id"] == teacher.id]
    assert sorted(actual, key=str) == sorted(loads, key=str)


@pytest.mark.parametrize("role", ["TEACHER", "MANAGER"])
async def test_staff_invite_concurrent_activation_has_one_winner(arena, role):
    oid = arena.users[900004].organization_id
    first_user, first = await applicant(arena, 810011)
    second_user, second = await applicant(arena, 810012)
    body = {"role": role, "loads": [{"subject_id": 1, "group_id": 1}] if role == "TEACHER" else []}
    response = await arena.client.post(f"/api/organizations/{oid}/invites", headers=arena.auth(900005), json=body)
    assert response.status_code == 200, response.text
    invitation = response.json()
    results = await asyncio.gather(*[
        arena.client.post("/api/invites/accept", headers=auth, json={"token": invitation["token"]})
        for auth in (first, second)
    ])
    assert sorted(r.status_code for r in results) == [200, 409]
    async with arena.sessions() as db:
        users = [await db.get(User, u.id) for u in (first_user, second_user)]
        winner = next(u for u in users if u.role == role)
        assert winner.organization_id == oid
        assert len([u for u in users if u.role == "PENDING" and u.organization_id is None]) == 1
        assert (await db.get(Invite, invitation["id"])).used_by == winner.id


@pytest.mark.parametrize("role", ["TEACHER", "MANAGER"])
async def test_revoked_staff_invite_cannot_be_activated(arena, role):
    _, auth = await applicant(arena, 810021)
    body = {"role": role, "loads": [{"subject_id": 1, "group_id": 1}] if role == "TEACHER" else []}
    response = await arena.client.post("/api/organizations/1/invites", headers=arena.auth(900005), json=body)
    assert response.status_code == 200, response.text
    invitation = response.json()
    assert (await arena.client.delete(f"/api/invites/{invitation['id']}", headers=arena.auth(900005))).status_code == 200
    assert (await arena.client.post("/api/invites/accept", headers=auth, json={"token": invitation["token"]})).status_code == 404


async def test_invalid_teacher_invite_does_not_consume_token(arena):
    teacher, auth = await applicant(arena, 810031)
    invitation = (await arena.client.post("/api/organizations/1/invites", headers=arena.auth(900004),
                                         json={"role": "TEACHER", "loads": [{"subject_id": 1, "group_id": 1}]})).json()
    async with arena.sessions() as db:
        await db.delete(await db.get(GroupSubject, (1, 1)))
        await db.commit()
    token = {"token": invitation["token"]}
    assert (await arena.client.post("/api/invites/accept", headers=auth, json=token)).status_code == 409
    async with arena.sessions() as db:
        assert (await db.get(Invite, invitation["id"])).used_by is None
        assert (await db.get(User, teacher.id)).role == "PENDING"
        db.add(GroupSubject(group_id=1, subject_id=1))
        await db.commit()
    assert (await arena.client.post("/api/invites/accept", headers=auth, json=token)).status_code == 200


async def test_staff_cannot_be_assigned_by_username(arena):
    user, _ = await applicant(arena, 810041)
    for role in ("TEACHER", "MANAGER"):
        response = await arena.client.post("/api/organizations/1/members", headers=arena.auth(900005),
                                           json={"query": str(user.max_id), "role": role, "loads": []})
        assert response.status_code == 409, response.text


async def test_existing_teacher_loads_can_be_updated_without_lookup(arena):
    teacher = arena.users[900003]
    url = f"/api/organizations/1/teachers/{teacher.id}/loads"
    loads = [{"subject_id": 2, "group_id": 2}]
    assert (await arena.client.put(url, headers=arena.auth(900004), json={"loads": loads})).status_code == 200
    async with arena.sessions() as db:
        actual = (await db.scalars(select(TeacherLoad).where(TeacherLoad.teacher_id == teacher.id))).all()
        assert [(load.subject_id, load.group_id) for load in actual] == [(2, 2)]
    assert (await arena.client.put(url, headers=arena.auth(900001), json={"loads": loads})).status_code == 403
    assert (await arena.client.put(url, headers=arena.auth(900004), json={"loads": []})).status_code == 422
    other = (await arena.client.post("/api/organizations", headers=arena.auth(900005), json={"name": "Другое"})).json()
    assert (await arena.client.put(f"/api/organizations/{other['id']}/teachers/{teacher.id}/loads",
                                   headers=arena.auth(900005), json={"loads": loads})).status_code == 404


async def test_organization_boundaries_and_role_permissions(arena):
    client, admin, manager = arena.client, arena.auth(900005), arena.auth(900004)
    organization = await client.post("/api/organizations", headers=admin, json={"name": "Другое учреждение"})
    assert organization.status_code == 201, organization.text
    oid = organization.json()["id"]
    assert (await client.get(f"/api/organizations/{oid}/catalog", headers=admin)).status_code == 200
    assert (await client.get(f"/api/organizations/{oid}/catalog", headers=manager)).status_code == 403
    assert (await client.post(f"/api/organizations/{oid}/groups", headers=manager, json={"name": "Чужая группа"})).status_code == 403
    own_oid = arena.users[900004].organization_id
    assert (await client.post(f"/api/organizations/{own_oid}/invites", headers=manager, json={"role": "MANAGER"})).status_code == 403
    assert (await client.get(f"/api/organizations/{own_oid}/requests", headers=arena.auth(900003))).status_code == 403
    assert (await client.get("/api/homework", headers=arena.auth(900005))).status_code == 403


async def test_removing_student_revokes_learning_access_and_cancels_duel(arena):
    student = arena.users[900001]
    async with arena.sessions() as db:
        event = await db.scalar(select(Event).where(Event.status == "OPEN"))
        db.add(EventParticipant(event_id=event.id, user_id=student.id))
        await db.commit()
    response = await arena.client.delete(f"/api/groups/{student.group_id}/members/{student.id}", headers=arena.auth(900004))
    assert response.status_code == 200, response.text
    me = (await arena.client.get("/api/me", headers=arena.auth(900001))).json()
    assert me["role"] == "PENDING" and me["group_id"] is None and me["organization_id"] is None
    assert (await arena.client.get("/api/homework", headers=arena.auth(900001))).status_code == 403
    async with arena.sessions() as db:
        duel = await db.scalar(select(Duel))
        assert duel.status == "CANCELLED"
        participants = (await db.execute(select(EventParticipant, Event.status).join(Event).where(EventParticipant.user_id == student.id))).all()
        assert all(part.status == "LEFT" for part, status in participants if status != "COMPLETED")
        assert all(part.status == "JOINED" for part, status in participants if status == "COMPLETED")


async def test_phone_signature_is_bound_to_current_max_user(arena):
    stamp, phone = int(time.time()), "79991234567"
    check = f"authDate={stamp}\nphone={phone}\nuserId=900001"
    signature = hmac.new(b"test-max-token", check.encode(), hashlib.sha256).hexdigest()
    payload = {"auth_date": stamp, "phone": f"+{phone}", "hash": signature}
    assert (await arena.client.post("/api/me/phone", headers=arena.auth(900001), json=payload)).status_code == 200
    assert (await arena.client.post("/api/me/phone", headers=arena.auth(900002), json=payload)).status_code == 401
    payload["phone"] = "+79990000000"
    assert (await arena.client.post("/api/me/phone", headers=arena.auth(900001), json=payload)).status_code == 401
    async with arena.sessions() as db:
        user = await db.get(User, arena.users[900001].id)
        assert user.phone == phone


async def test_duel_acceptance_rechecks_friendship(arena):
    client, student = arena.client, arena.auth(900001)
    sofia = arena.users[900006]
    friends = (await client.get("/api/friends", headers=student)).json()
    pending = next(item for item in friends if item["user"]["id"] == sofia.id)
    assert (await client.post(f"/api/friendships/{pending['id']}/respond", headers=student, json={"approve": True})).status_code == 200
    challenge = await client.post("/api/duels", headers=student, json={"opponent_id": sofia.id, "duration": "1d"})
    assert challenge.status_code == 201, challenge.text
    assert (await client.delete(f"/api/friendships/{pending['id']}", headers=student)).status_code == 200
    accepted = await client.post(f"/api/duels/{challenge.json()['id']}/accept", headers=arena.auth(900006))
    assert accepted.status_code == 409, accepted.text
