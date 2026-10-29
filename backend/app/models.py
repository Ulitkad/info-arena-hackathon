from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(default=now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    max_id: Mapped[int] = mapped_column(unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    username: Mapped[str | None] = mapped_column(String(100), index=True)
    phone: Mapped[str | None] = mapped_column(String(30), index=True)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="PENDING")
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"), index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), index=True)
    active_title_id: Mapped[int | None] = mapped_column(ForeignKey("rewards.id"))
    active_frame_id: Mapped[int | None] = mapped_column(ForeignKey("rewards.id"))
    showcase: Mapped[list] = mapped_column(JSON, default=list)
    duel_wins: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=now)


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(16), default="#0284c7")


class GroupSubject(Base):
    __tablename__ = "group_subjects"
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)


class TeacherLoad(Base):
    __tablename__ = "teacher_loads"
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)


class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    loads: Mapped[list] = mapped_column(JSON, default=list)
    revoked: Mapped[bool] = mapped_column(default=False)
    used_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)


class JoinRequest(Base):
    __tablename__ = "join_requests"
    __table_args__ = (Index("uq_pending_student", "student_id", unique=True, sqlite_where=text("status = 'PENDING'")),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(default=now)


class Reward(Base):
    __tablename__ = "rewards"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    threshold: Mapped[int] = mapped_column(Integer)
    asset_url: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(30), default="award")
    special: Mapped[bool] = mapped_column(Boolean, default=False)


class Inventory(Base):
    __tablename__ = "inventory"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id", ondelete="CASCADE"), primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(default=now)


class Progress(Base):
    __tablename__ = "progress"
    __table_args__ = (UniqueConstraint("user_id", "scope"), CheckConstraint("points >= 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scope: Mapped[str] = mapped_column(String(40))
    points: Mapped[int] = mapped_column(default=0)


class PointLedger(Base):
    __tablename__ = "point_ledger"
    __table_args__ = (UniqueConstraint("user_id", "source_kind", "source_id"), CheckConstraint("points > 0"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id"))
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    source_kind: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=now, index=True)


class Upload(Base):
    __tablename__ = "uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    url: Mapped[str] = mapped_column(String(200), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(Integer)


class Homework(Base):
    __tablename__ = "homework"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    title: Mapped[str] = mapped_column(String(160))
    text: Mapped[str] = mapped_column(Text, default="")
    files: Mapped[list] = mapped_column(JSON, default=list)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    optional: Mapped[bool] = mapped_column(default=False)
    deadline_notified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)


class HomeworkGroup(Base):
    __tablename__ = "homework_groups"
    homework_id: Mapped[int] = mapped_column(ForeignKey("homework.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("homework_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homework.id"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text, default="")
    files: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED")
    feedback: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime] = mapped_column(default=now)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (CheckConstraint("points BETWEEN 1 AND 30"), CheckConstraint("min_participants > 0 AND max_participants >= min_participants"))
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(20), default="OTHER")
    points: Mapped[int] = mapped_column(Integer)
    min_participants: Mapped[int] = mapped_column(Integer)
    max_participants: Mapped[int] = mapped_column(Integer)
    closes_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(default=now)


class EventGroup(Base):
    __tablename__ = "event_groups"
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)


class EventParticipant(Base):
    __tablename__ = "event_participants"
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="JOINED")
    blacklisted: Mapped[bool] = mapped_column(default=False)


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("low_id", "high_id"), CheckConstraint("low_id < high_id"))
    id: Mapped[int] = mapped_column(primary_key=True)
    low_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    high_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")


class Duel(Base):
    __tablename__ = "duels"
    __table_args__ = (
        Index("uq_live_duel_pair", "low_id", "high_id", unique=True, sqlite_where=text("status IN ('PENDING', 'ACTIVE')")),
        CheckConstraint("low_id < high_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    challenger_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    opponent_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    low_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    high_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id"))
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    duration: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    initial_challenger: Mapped[int] = mapped_column(default=0)
    initial_opponent: Mapped[int] = mapped_column(default=0)
    challenger_score: Mapped[int] = mapped_column(default=0)
    opponent_score: Mapped[int] = mapped_column(default=0)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=now)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(200), default="/")
    read: Mapped[bool] = mapped_column(default=False)
    toasted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)
