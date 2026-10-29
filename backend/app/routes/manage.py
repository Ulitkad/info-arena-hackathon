from fastapi import APIRouter, Depends
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas as s
from ..db import session_dep
from ..models import (
    Duel, Event, EventGroup, EventParticipant, Group, GroupSubject, Homework, HomeworkGroup,
    Inventory, Invite, JoinRequest, Organization, Reward, Subject, TeacherLoad, User,
)
from ..security import current_user, fail, require, scope
from ..services import (
    activate_student, create_invite, find_user, init_progress, notify, public_user, row,
    seed_rewards, unlock_rewards, validate_assignments, validate_files,
)

router = APIRouter(prefix="/api")


async def manageable(db, user, organization_id):
    require(user, "ADMIN", "MANAGER")
    scope(user, organization_id)
    organization = await db.get(Organization, organization_id)
    if not organization:
        fail("Учреждение не найдено", 404)
    return organization


@router.get("/organizations")
async def organizations(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "ADMIN", "MANAGER")
    query = select(Organization)
    if user.role != "ADMIN":
        query = query.where(Organization.id == user.organization_id)
    return [row(item) for item in (await db.scalars(query)).all()]


@router.post("/organizations", status_code=201)
async def create_organization(data: s.NameInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "ADMIN")
    organization = Organization(name=data.name)
    db.add(organization)
    await db.flush()
    await seed_rewards(db, organization.id)
    return row(organization)


@router.get("/organizations/{oid}/catalog")
async def catalog(oid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    scope(user, oid)
    require(user, "ADMIN", "MANAGER", "TEACHER", "STUDENT")
    groups = (await db.scalars(select(Group).where(Group.organization_id == oid))).all()
    subjects = (await db.scalars(select(Subject).where(Subject.organization_id == oid))).all()
    group_ids = [item.id for item in groups]
    links = (await db.scalars(select(GroupSubject).where(GroupSubject.group_id.in_(group_ids)))).all()
    loads = (await db.scalars(select(TeacherLoad).where(TeacherLoad.group_id.in_(group_ids)))).all()
    if user.role == "TEACHER":
        loads = [item for item in loads if item.teacher_id == user.id]
        groups = [item for item in groups if item.id in {load.group_id for load in loads}]
        subjects = [item for item in subjects if item.id in {load.subject_id for load in loads}]
        links = [item for item in links if (item.group_id, item.subject_id) in {(load.group_id, load.subject_id) for load in loads}]
    if user.role == "STUDENT":
        groups = [item for item in groups if item.id == user.group_id]
        links = [item for item in links if item.group_id == user.group_id]
        subjects = [item for item in subjects if item.id in {link.subject_id for link in links}]
        loads = []
    return {"groups": [row(item) for item in groups], "subjects": [row(item) for item in subjects],
            "links": [row(item) for item in links], "loads": [row(item) for item in loads]}


@router.post("/organizations/{oid}/groups", status_code=201)
async def create_group(oid: int, data: s.NameInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await manageable(db, user, oid)
    if await db.scalar(select(Group.id).where(Group.organization_id == oid, Group.name == data.name)):
        fail("Группа с таким названием уже существует", 409)
    group = Group(organization_id=oid, name=data.name)
    db.add(group)
    await db.flush()
    return row(group)


@router.put("/groups/{gid}")
async def rename_group(gid: int, data: s.NameInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    group = await db.get(Group, gid)
    if not group:
        fail("Группа не найдена", 404)
    await manageable(db, user, group.organization_id)
    if await db.scalar(select(Group.id).where(Group.organization_id == group.organization_id, Group.name == data.name, Group.id != gid)):
        fail("Название уже занято", 409)
    group.name = data.name
    return {"ok": True}


@router.delete("/groups/{gid}")
async def delete_group(gid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    group = await db.get(Group, gid)
    if not group:
        fail("Группа не найдена", 404)
    await manageable(db, user, group.organization_id)
    occupied = await db.scalar(select(User.id).where(User.group_id == gid).limit(1))
    content = await db.scalar(select(HomeworkGroup.group_id).where(HomeworkGroup.group_id == gid).limit(1))
    events = await db.scalar(select(EventGroup.group_id).where(EventGroup.group_id == gid).limit(1))
    if occupied or content or events:
        fail("Удалить можно пустую группу без заданий и мероприятий", 409)
    await db.delete(group)
    return {"ok": True}


@router.post("/organizations/{oid}/subjects", status_code=201)
async def create_subject(oid: int, data: s.SubjectInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await manageable(db, user, oid)
    if await db.scalar(select(Subject.id).where(Subject.organization_id == oid, Subject.name == data.name)):
        fail("Предмет с таким названием уже существует", 409)
    subject = Subject(organization_id=oid, **data.model_dump())
    db.add(subject)
    await db.flush()
    await seed_rewards(db, oid, subject.id)
    return row(subject)


@router.put("/subjects/{sid}")
async def rename_subject(sid: int, data: s.SubjectInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    subject = await db.get(Subject, sid)
    if not subject:
        fail("Предмет не найден", 404)
    await manageable(db, user, subject.organization_id)
    if await db.scalar(select(Subject.id).where(Subject.organization_id == subject.organization_id, Subject.name == data.name, Subject.id != sid)):
        fail("Название уже занято", 409)
    subject.name, subject.color = data.name, data.color
    return {"ok": True}


@router.delete("/subjects/{sid}")
async def delete_subject(sid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    subject = await db.get(Subject, sid)
    if not subject:
        fail("Предмет не найден", 404)
    await manageable(db, user, subject.organization_id)
    for model in (Homework, Event, Duel):
        if await db.scalar(select(model.id).where(model.subject_id == sid).limit(1)):
            fail("Предмет используется в заданиях, событиях или дуэлях", 409)
    if await db.scalar(select(Inventory.user_id).join(Reward).where(Reward.subject_id == sid).limit(1)):
        fail("По предмету уже выданы награды", 409)
    await db.delete(subject)
    return {"ok": True}


@router.put("/groups/{gid}/subjects")
async def link_subjects(gid: int, data: s.GroupSubjects, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    group = await db.get(Group, gid)
    if not group:
        fail("Группа не найдена", 404)
    await manageable(db, user, group.organization_id)
    for sid in set(data.subject_ids):
        subject = await db.get(Subject, sid)
        if not subject or subject.organization_id != group.organization_id:
            fail("Предмет не принадлежит учреждению", 403)
    existing = (await db.scalars(select(GroupSubject).where(GroupSubject.group_id == gid))).all()
    removed = {link.subject_id for link in existing} - set(data.subject_ids)
    for sid in removed:
        if await db.scalar(select(TeacherLoad.teacher_id).where(TeacherLoad.group_id == gid, TeacherLoad.subject_id == sid).limit(1)):
            fail("Сначала снимите нагрузку преподавателя по этому предмету", 409)
        await db.delete(await db.get(GroupSubject, (gid, sid)))
    for sid in set(data.subject_ids) - {item.subject_id for item in existing}:
        db.add(GroupSubject(group_id=gid, subject_id=sid))
    await db.flush()
    students = (await db.scalars(select(User).where(User.group_id == gid))).all()
    for student in students:
        await init_progress(db, student)
    return {"ok": True}


@router.post("/organizations/{oid}/invites")
async def invite(oid: int, data: s.InviteInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await manageable(db, user, oid)
    if data.role == "MANAGER":
        require(user, "ADMIN")
    return await create_invite(db, oid, data.role, data.group_id, data.loads)


@router.get("/organizations/{oid}/invites")
async def invites(oid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await manageable(db, user, oid)
    items = (await db.scalars(select(Invite).where(Invite.organization_id == oid).order_by(Invite.id.desc()).limit(100))).all()
    return [{**row(item, "token_hash"), "loads": item.loads if item.role == "TEACHER" else []}
            for item in items if user.role == "ADMIN" or item.role != "MANAGER"]


@router.delete("/invites/{iid}")
async def revoke_invite(iid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    item = await db.get(Invite, iid)
    if not item:
        fail("Приглашение не найдено", 404)
    await manageable(db, user, item.organization_id)
    if item.role == "MANAGER":
        require(user, "ADMIN")
    item.revoked = True
    return {"ok": True}


@router.get("/organizations/{oid}/members")
async def members(oid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "ADMIN", "MANAGER", "TEACHER")
    scope(user, oid)
    query = select(User).where(User.organization_id == oid)
    if user.role == "TEACHER":
        gids = (await db.scalars(select(TeacherLoad.group_id).where(TeacherLoad.teacher_id == user.id))).all()
        query = query.where(User.group_id.in_(gids), User.role == "STUDENT")
    return [public_user(item) for item in (await db.scalars(query.order_by(User.display_name).limit(2000))).all()]


@router.post("/organizations/{oid}/members")
async def assign_user(oid: int, data: s.AssignUser, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await manageable(db, user, oid)
    if data.role in ("ADMIN", "MANAGER"):
        require(user, "ADMIN")
    target = await find_user(db, data.query)
    if target.id == user.id or target.role == "ADMIN":
        fail("Нельзя изменить эту учетную запись", 409)
    if target.organization_id and target.organization_id != oid:
        fail("Пользователь уже состоит в другом учреждении", 409)
    if data.role == "STUDENT":
        group = await db.get(Group, data.group_id)
        if not group or group.organization_id != oid:
            fail("Группа не найдена", 404)
        await activate_student(db, target, group)
        pending = (await db.scalars(select(JoinRequest).where(JoinRequest.student_id == target.id, JoinRequest.status == "PENDING"))).all()
        for item in pending:
            item.status = "APPROVED" if item.group_id == group.id else "REJECTED"
    else:
        if target.group_id or target.role not in ("PENDING", data.role):
            fail("Нельзя изменить действующую роль пользователя", 409)
        target.role, target.organization_id = data.role, oid
        if data.role == "TEACHER":
            await validate_assignments(db, oid, data.loads)
            await db.execute(delete(TeacherLoad).where(TeacherLoad.teacher_id == target.id))
            for item in data.loads:
                db.add(TeacherLoad(teacher_id=target.id, **item.model_dump()))
        await notify(db, target.id, "Вам открыт доступ", f"Ваша роль: {data.role}")
    return public_user(target)


@router.delete("/groups/{gid}/members/{uid}")
async def remove_student(gid: int, uid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    group, student = await db.get(Group, gid), await db.get(User, uid)
    if not group:
        fail("Группа не найдена", 404)
    await manageable(db, user, group.organization_id)
    if not student or student.group_id != gid:
        fail("Ученик не найден", 404)
    student.group_id, student.organization_id, student.role = None, None, "PENDING"
    pending = (await db.scalars(select(JoinRequest).where(JoinRequest.student_id == uid, JoinRequest.status == "PENDING"))).all()
    for request in pending:
        request.status = "REJECTED"
    duels = (await db.scalars(select(Duel).where(Duel.status.in_(["PENDING", "ACTIVE"]), or_(Duel.challenger_id == uid, Duel.opponent_id == uid)))).all()
    for duel in duels:
        duel.status = "CANCELLED"
        other = duel.opponent_id if duel.challenger_id == uid else duel.challenger_id
        await notify(db, other, "Дуэль отменена", "Соперник покинул группу", "/friends")
    parts = (await db.scalars(select(EventParticipant).join(Event).where(EventParticipant.user_id == uid, Event.status != "COMPLETED"))).all()
    for part in parts:
        part.status = "LEFT"
    await notify(db, uid, "Участие в группе завершено", "Для продолжения используйте новое приглашение")
    return {"ok": True}


@router.get("/organizations/{oid}/requests")
async def join_requests(oid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await manageable(db, user, oid)
    results = (await db.execute(select(JoinRequest, User, Group).join(User, User.id == JoinRequest.student_id)
                               .join(Group, Group.id == JoinRequest.group_id)
                               .where(Group.organization_id == oid, JoinRequest.status == "PENDING")
                               .order_by(Group.name, JoinRequest.created_at))).all()
    return [{**row(item), "student": public_user(student), "group": row(group)} for item, student, group in results]


@router.post("/requests/{rid}/moderate")
async def moderate(rid: int, data: s.Moderation, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    item = await db.get(JoinRequest, rid)
    if not item:
        fail("Заявка не найдена", 404)
    group = await db.get(Group, item.group_id)
    await manageable(db, user, group.organization_id)
    if item.status != "PENDING":
        return {"ok": True}
    student = await db.get(User, item.student_id)
    if data.approve:
        await activate_student(db, student, group)
    else:
        await notify(db, student.id, "Заявка отклонена", f"Группа {group.name}. Обратитесь к управляющему.")
    item.status = "APPROVED" if data.approve else "REJECTED"
    return {"ok": True}


@router.post("/groups/{gid}/approve-all")
async def approve_all(gid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    group = await db.get(Group, gid)
    if not group:
        fail("Группа не найдена", 404)
    await manageable(db, user, group.organization_id)
    items = (await db.scalars(select(JoinRequest).where(
        JoinRequest.group_id == gid, JoinRequest.status == "PENDING",
    ).order_by(JoinRequest.created_at).limit(100))).all()
    for item in items:
        student = await db.get(User, item.student_id)
        await activate_student(db, student, group)
        item.status = "APPROVED"
    return {"approved": len(items)}


@router.get("/organizations/{oid}/rewards")
async def rewards(oid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    scope(user, oid)
    return [row(item) for item in (await db.scalars(select(Reward).where(Reward.organization_id == oid).order_by(Reward.threshold))).all()]


async def validate_reward(db, user, oid, data):
    if data.subject_id:
        subject = await db.get(Subject, data.subject_id)
        if not subject or subject.organization_id != oid:
            fail("Предмет не найден", 404)
    if data.asset_url:
        await validate_files(db, user, [data.asset_url])


@router.post("/organizations/{oid}/rewards", status_code=201)
async def create_reward(oid: int, data: s.RewardInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await manageable(db, user, oid)
    await validate_reward(db, user, oid, data)
    reward = Reward(organization_id=oid, **data.model_dump())
    db.add(reward)
    await db.flush()
    for student in (await db.scalars(select(User).where(User.organization_id == oid, User.role == "STUDENT"))).all():
        await unlock_rewards(db, student, data.subject_id)
    return row(reward)


@router.put("/rewards/{rid}")
async def update_reward(rid: int, data: s.RewardInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    reward = await db.get(Reward, rid)
    if not reward:
        fail("Награда не найдена", 404)
    await manageable(db, user, reward.organization_id)
    if reward.special:
        fail("Системная награда дуэли не редактируется", 409)
    await validate_reward(db, user, reward.organization_id, data)
    if reward.kind != data.kind or reward.subject_id != data.subject_id:
        if await db.scalar(select(Inventory.user_id).where(Inventory.reward_id == rid).limit(1)):
            fail("Нельзя изменить тип или предмет уже выданной награды", 409)
    for key, value in data.model_dump().items():
        setattr(reward, key, value)
    await db.flush()
    for student in (await db.scalars(select(User).where(User.organization_id == reward.organization_id, User.role == "STUDENT"))).all():
        await unlock_rewards(db, student, reward.subject_id)
    return row(reward)


@router.delete("/rewards/{rid}")
async def delete_reward(rid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    reward = await db.get(Reward, rid)
    if not reward:
        fail("Награда не найдена", 404)
    await manageable(db, user, reward.organization_id)
    if reward.special or await db.scalar(select(Inventory.user_id).where(Inventory.reward_id == rid).limit(1)):
        fail("Нельзя удалить системную или уже выданную награду", 409)
    await db.delete(reward)
    return {"ok": True}
