import hashlib
import hmac
import time

from sqlalchemy import select

from app.models import Duel, Event, EventParticipant, User
from app.security import create_token


async def applicant(arena, max_id):
    async with arena.sessions() as db:
        user = User(max_id=max_id, display_name=f"Участник {max_id}")
        db.add(user)
        await db.commit()
        return user, {"Authorization": f"Bearer {create_token(user.id)}"}


async def test_staff_invite_is_bound_to_first_user_and_keeps_exact_loads(arena):
    client, manager = arena.client, arena.auth(900004)
    oid = arena.users[900004].organization_id
    teacher, first = await applicant(arena, 810001)
    _, second = await applicant(arena, 810002)
    loads = [{"subject_id": 1, "group_id": 1}, {"subject_id": 2, "group_id": 2}]
    invite = await client.post(f"/api/organizations/{oid}/invites", headers=manager, json={"role": "TEACHER", "loads": loads})
    assert invite.status_code == 200, invite.text
    token = {"token": invite.json()["token"]}
    for _ in range(2):
        assert (await client.post("/api/invites/accept", headers=first, json=token)).status_code == 200
    assert (await client.post("/api/invites/accept", headers=second, json=token)).status_code == 409
    catalog = (await client.get(f"/api/organizations/{oid}/catalog", headers=manager)).json()
    actual = [{k: row[k] for k in ("subject_id", "group_id")} for row in catalog["loads"] if row["teacher_id"] == teacher.id]
    assert sorted(actual, key=str) == sorted(loads, key=str)


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
