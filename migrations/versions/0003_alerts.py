"""Add explainable and deduplicated alerts."""

from alembic import op
import sqlalchemy as sa


revision = "0003_alerts"
down_revision = "0002_backtest_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("market_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),
    )
    op.create_index("ix_alerts_rule_id", "alerts", ["rule_id"])
    op.create_index("ix_alerts_symbol", "alerts", ["symbol"])
    op.create_index("ix_alerts_market_timestamp", "alerts", ["market_timestamp"])


def downgrade() -> None:
    op.drop_index("ix_alerts_market_timestamp", table_name="alerts")
    op.drop_index("ix_alerts_symbol", table_name="alerts")
    op.drop_index("ix_alerts_rule_id", table_name="alerts")
    op.drop_table("alerts")

