"""Add the tracked-symbol watchlist."""

from alembic import op
import sqlalchemy as sa


revision = "0005_watchlist"
down_revision = "0004_market_bars"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("symbol"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")

