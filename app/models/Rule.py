from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.config import Base


def utc_now():
    return datetime.now(timezone.utc)


class Rule(Base):
    __tablename__ = "rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    symbol = Column(String(32), nullable=False, index=True)
    timeframe = Column(String(16), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    current_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    versions = relationship(
        "RuleVersion",
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="RuleVersion.version",
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (
        UniqueConstraint("rule_id", "version", name="uq_rule_versions_rule_version"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    rule_id = Column(String, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    dsl = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    rule = relationship("Rule", back_populates="versions")
