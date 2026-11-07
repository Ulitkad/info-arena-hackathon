"""Add a selectable visual style to profile frame rewards."""
from alembic import op
from sqlalchemy import Column, String, inspect, text

revision = "0002_frame_styles"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    if not any(column["name"] == "frame_style" for column in inspect(op.get_bind()).get_columns("rewards")):
        op.add_column("rewards", Column("frame_style", String(30), nullable=True))
    if not any(column["name"] == "active_frame_style" for column in inspect(op.get_bind()).get_columns("users")):
        op.add_column("users", Column("active_frame_style", String(30), nullable=True))
    op.execute(text("UPDATE rewards SET frame_style = 'skyline' WHERE kind = 'FRAME' AND frame_style IS NULL"))
    op.execute(text("UPDATE users SET active_frame_style = (SELECT frame_style FROM rewards WHERE rewards.id = users.active_frame_id) WHERE active_frame_id IS NOT NULL"))


def downgrade():
    if any(column["name"] == "frame_style" for column in inspect(op.get_bind()).get_columns("rewards")):
        op.drop_column("rewards", "frame_style")
    if any(column["name"] == "active_frame_style" for column in inspect(op.get_bind()).get_columns("users")):
        op.drop_column("users", "active_frame_style")
