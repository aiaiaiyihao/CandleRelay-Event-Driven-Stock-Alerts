"""Add normalized historical market bars."""

from alembic import op
import sqlalchemy as sa


revision = "0004_market_bars"
down_revision = "0003_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_bars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "symbol",
            "timeframe",
            "timestamp",
            name="uq_market_bars_symbol_timeframe_timestamp",
        ),
    )
    op.create_index("ix_market_bars_symbol", "market_bars", ["symbol"])
    op.create_index("ix_market_bars_timestamp", "market_bars", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_market_bars_timestamp", table_name="market_bars")
    op.drop_index("ix_market_bars_symbol", table_name="market_bars")
    op.drop_table("market_bars")

