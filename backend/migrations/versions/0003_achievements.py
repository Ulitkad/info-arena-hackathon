"""Move badges out of Battlepass into condition-based achievements."""
import json

from alembic import op
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, inspect, text

revision = "0003_achievements"
down_revision = "0002_frame_styles"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = inspect(bind).get_table_names()
    if "achievements" not in tables:
        op.create_table(
            "achievements",
            Column("id", Integer, primary_key=True),
            Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True),
            Column("code", String(50), nullable=False),
            Column("threshold", Integer, nullable=False, server_default="1"),
            Column("name", String(100), nullable=False),
            Column("description", String(240), nullable=False, server_default=""),
            Column("icon", String(30), nullable=False, server_default="award"),
            Column("hidden", Boolean, nullable=False, server_default=text("0")),
            Column("created_at", DateTime, nullable=True),
        )
    if "user_achievements" not in tables:
        op.create_table(
            "user_achievements",
            Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            Column("achievement_id", Integer, ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True),
            Column("unlocked_at", DateTime, nullable=True),
        )
    if "revision_count" not in {column["name"] for column in inspect(bind).get_columns("submissions")}:
        op.add_column("submissions", Column("revision_count", Integer, nullable=False, server_default="0"))
    # Preserve badges already earned in the old Battlepass as historical,
    # permanently unlocked achievements. New badges are no longer editable
    # rewards and are created by the condition catalogue in application code.
    legacy = bind.execute(text(
        "SELECT id, organization_id, subject_id, name, icon FROM rewards WHERE kind = 'BADGE'"
    )).mappings().all()
    legacy_ids = {}
    for badge in legacy:
        result = bind.execute(text(
            "INSERT INTO achievements (organization_id, subject_id, code, threshold, name, description, icon, hidden) "
            "VALUES (:organization_id, :subject_id, :code, 1, :name, :description, :icon, 0)"
        ), {
            "organization_id": badge["organization_id"], "subject_id": badge["subject_id"],
            "code": f"LEGACY_BADGE_{badge['id']}", "name": badge["name"],
            "description": "Ранее открытое достижение", "icon": badge["icon"] or "award",
        })
        legacy_ids[badge["id"]] = result.lastrowid
    if legacy_ids:
        earned = bind.execute(text(
            "SELECT user_id, reward_id, unlocked_at FROM inventory WHERE reward_id IN "
            f"({','.join(str(value) for value in legacy_ids)})"
        )).mappings().all()
        for item in earned:
            achievement_id = legacy_ids[item["reward_id"]]
            bind.execute(text(
                "INSERT INTO user_achievements (user_id, achievement_id, unlocked_at) VALUES (:user_id, :achievement_id, :unlocked_at)"
            ), {"user_id": item["user_id"], "achievement_id": achievement_id, "unlocked_at": item["unlocked_at"]})
        showcases = bind.execute(text("SELECT id, showcase FROM users")).mappings().all()
        for user in showcases:
            try:
                values = json.loads(user["showcase"] or "[]")
            except (TypeError, json.JSONDecodeError):
                values = []
            converted = [legacy_ids.get(value, value) for value in values if value not in legacy_ids or legacy_ids.get(value)]
            if converted != values:
                bind.execute(text("UPDATE users SET showcase = :showcase WHERE id = :id"), {
                    "id": user["id"], "showcase": json.dumps(converted),
                })
    op.execute(text("DELETE FROM inventory WHERE reward_id IN (SELECT id FROM rewards WHERE kind = 'BADGE')"))
    op.execute(text("DELETE FROM rewards WHERE kind = 'BADGE'"))


def downgrade():
    bind = op.get_bind()
    if "user_achievements" in inspect(bind).get_table_names():
        op.drop_table("user_achievements")
    if "achievements" in inspect(bind).get_table_names():
        op.drop_table("achievements")
    if "revision_count" in {column["name"] for column in inspect(bind).get_columns("submissions")}:
        op.drop_column("submissions", "revision_count")
