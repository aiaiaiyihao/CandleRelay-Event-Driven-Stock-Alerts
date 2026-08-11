"""Associate rules and their alerts with users."""

from alembic import op
import sqlalchemy as sa


revision = "0008_rule_ownership"
down_revision = "0007_favorites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rules", sa.Column("user_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_rules_user_id_users",
        "rules",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_rules_user_id", "rules", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_rules_user_id", table_name="rules")
    op.drop_constraint("fk_rules_user_id_users", "rules", type_="foreignkey")
    op.drop_column("rules", "user_id")
