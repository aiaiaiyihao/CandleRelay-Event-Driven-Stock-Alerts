"""Create the legacy market tables and versioned SignalForge rules."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "poll_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("symbols", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "raw_market_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_raw_symbol_timestamp",
        "raw_market_data",
        ["symbol", "timestamp"],
    )
    op.create_table(
        "symbol_averages",
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("ma_5", sa.Float(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("symbol"),
    )
    op.create_index(
        "ix_movingAverage_symbol_timestamp",
        "symbol_averages",
        ["symbol", "timestamp"],
    )
    op.create_table(
        "rules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rules_symbol", "rules", ["symbol"])
    op.create_table(
        "rule_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("dsl", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id",
            "version",
            name="uq_rule_versions_rule_version",
        ),
    )
    op.create_index("ix_rule_versions_rule_id", "rule_versions", ["rule_id"])


def downgrade() -> None:
    op.drop_index("ix_rule_versions_rule_id", table_name="rule_versions")
    op.drop_table("rule_versions")
    op.drop_index("ix_rules_symbol", table_name="rules")
    op.drop_table("rules")
    op.drop_index("ix_movingAverage_symbol_timestamp", table_name="symbol_averages")
    op.drop_table("symbol_averages")
    op.drop_index("ix_raw_symbol_timestamp", table_name="raw_market_data")
    op.drop_table("raw_market_data")
    op.drop_table("poll_jobs")
