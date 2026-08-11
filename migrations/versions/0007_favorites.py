"""Add user-owned favorite symbols."""

from alembic import op
import sqlalchemy as sa


revision = "0007_favorites"
down_revision = "0006_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "symbol"),
    )


def downgrade() -> None:
    op.drop_table("favorites")
