from datetime import timedelta

from sqlalchemy import select

from .models import (
    Duel, Event, EventGroup, EventParticipant, Friendship, Group, GroupSubject, Homework,
    HomeworkGroup, Inventory, JoinRequest, Organization, Reward, Subject, Submission, TeacherLoad, User, now,
)
from .services import award, init_progress, notify, seed_rewards


async def seed_demo(db):
    if await db.scalar(select(User.id).where(User.max_id == 900001)):
        return
    organization = Organization(name="Колледж цифровых технологий")
    db.add(organization)
    await db.flush()
    oid = organization.id
    group = Group(organization_id=oid, name="ИС-21")
    group2 = Group(organization_id=oid, name="ИС-22")
    subjects = [Subject(organization_id=oid, name=name, color=color) for name, color in [
        ("Программирование", "#6366f1"), ("Математика", "#0284c7"), ("Английский язык", "#10b981"),
    ]]
    db.add_all([group, group2, *subjects])
    await db.flush()
    await seed_rewards(db, oid)
    for subject in subjects:
        await seed_rewards(db, oid, subject.id)
        for g in (group, group2):
            db.add(GroupSubject(group_id=g.id, subject_id=subject.id))
    people = [
        User(max_id=900001, display_name="Александр Волков", username="alex_volkov", role="STUDENT", organization_id=oid, group_id=group.id),
        User(max_id=900002, display_name="Михаил Соколов", username="misha_s", role="STUDENT", organization_id=oid, group_id=group.id),
        User(max_id=900003, display_name="Анна Смирнова", username="anna_teacher", role="TEACHER", organization_id=oid),
        User(max_id=900004, display_name="Мария Кузнецова", username="maria_manager", role="MANAGER", organization_id=oid),
        User(max_id=900005, display_name="Администратор", username="arena_admin", role="ADMIN"),
        User(max_id=900006, display_name="София Орлова", username="sofia_orlova", role="STUDENT", organization_id=oid, group_id=group.id),
        User(max_id=900007, display_name="Даниил Морозов", username="dan_m", role="PENDING"),
    ]
    db.add_all(people)
    await db.flush()
    student, friend, teacher, manager, admin, sofia, pending = people
    for subject in subjects:
        for g in (group, group2):
            db.add(TeacherLoad(teacher_id=teacher.id, subject_id=subject.id, group_id=g.id))
    db.add(JoinRequest(student_id=pending.id, group_id=group.id))
    for person in (student, friend, sofia):
        await init_progress(db, person)
    db.add(Friendship(low_id=min(student.id, friend.id), high_id=max(student.id, friend.id), requester_id=student.id, status="ACCEPTED"))
    db.add(Friendship(low_id=min(student.id, sofia.id), high_id=max(student.id, sofia.id), requester_id=sofia.id))

    async def demo_event(title, subject, points, students, days_ago=0):
        event = Event(teacher_id=teacher.id, subject_id=subject.id, title=title, description="Учебное мероприятие · демонстрационные данные",
                      points=points, min_participants=1, max_participants=10, closes_at=now() - timedelta(days=days_ago), status="COMPLETED")
        db.add(event)
        await db.flush()
        db.add(EventGroup(event_id=event.id, group_id=group.id))
        for player in students:
            db.add(EventParticipant(event_id=event.id, user_id=player.id))
            await award(db, player, points, "EVENT", event.id, title, subject.id)
        return event

    await demo_event("Проектная мастерская", subjects[0], 10, [student, friend])
    await demo_event("Математический квиз", subjects[1], 5, [student, friend, sofia])
    duel = Duel(challenger_id=student.id, opponent_id=friend.id, low_id=min(student.id, friend.id), high_id=max(student.id, friend.id),
                 organization_id=oid, duration="3d", status="ACTIVE", starts_at=now(),
                ends_at=now() + timedelta(days=2, hours=4), initial_challenger=15, initial_opponent=15)
    db.add(duel)
    await db.flush()
    await demo_event("Разбор алгоритмов", subjects[0], 6, [student])
    await demo_event("Разговорный клуб", subjects[2], 4, [friend])
    for index, (title, text) in enumerate([
        ("Алгоритмы вокруг нас", "Выберите повседневную задачу и опишите алгоритм её решения. Укажите входные данные, шаги и ожидаемый результат."),
        ("Производная и её применение", "Решите задачи 1–5 из раздела «Производная». Для двух задач объясните решение своими словами."),
        ("My future profession", "Write a short essay about your future profession (150–200 words). What inspires you?"),
    ]):
        homework = Homework(teacher_id=teacher.id, subject_id=subjects[index].id, title=title, text=text,
                            deadline=now() + timedelta(days=index + 1, hours=3), optional=index == 2)
        db.add(homework)
        await db.flush()
        db.add(HomeworkGroup(homework_id=homework.id, group_id=group.id))
        if index == 0:
            db.add(Submission(homework_id=homework.id, student_id=friend.id, text="Алгоритм поиска книги: определить название, найти в каталоге, проверить доступность, получить книгу."))
    event = Event(teacher_id=teacher.id, subject_id=subjects[0].id, title="Хакатон: идея за 60 минут", description="Собираемся в команде и превращаем идею в первый прототип. Бери ноутбук и хорошее настроение!",
                  points=8, min_participants=2, max_participants=8, closes_at=now() + timedelta(days=2))
    duty = Event(teacher_id=teacher.id, subject_id=subjects[1].id, title="Дежурство", description="Поможем подготовить аудиторию к следующему занятию.", kind="DUTY",
                 points=2, min_participants=2, max_participants=2, closes_at=now() + timedelta(days=1))
    db.add_all([event, duty])
    await db.flush()
    for item in (event, duty):
        db.add(EventGroup(event_id=item.id, group_id=group.id))
    db.add(EventParticipant(event_id=event.id, user_id=friend.id))
    titles = (await db.scalars(select(Reward).join(Inventory).where(Inventory.user_id == student.id, Reward.kind == "TITLE", Reward.subject_id.is_(None)))).all()
    frames = (await db.scalars(select(Reward).join(Inventory).where(Inventory.user_id == student.id, Reward.kind == "FRAME", Reward.subject_id.is_(None)))).all()
    badges = (await db.scalars(select(Reward).join(Inventory).where(Inventory.user_id == student.id, Reward.kind == "BADGE"))).all()
    student.active_title_id = titles[0].id if titles else None
    student.active_frame_id = frames[0].id if frames else None
    student.showcase = [r.id for r in badges[:3]]
    await notify(db, student.id, "Твоя арена готова", "Учись, открывай награды и бросай вызов друзьям!", "/")
    await notify(db, student.id, "Новое задание", "Алгоритмы вокруг нас · +1 балл", "/arena")
    await notify(db, manager.id, "Новая заявка в ИС-21", pending.display_name, "/manage/requests")
    await db.flush()
