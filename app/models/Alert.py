from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint

from app.core.config import Base


def utc_now():
    return datetime.now(timezone.utc)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    rule_id = Column(
        String,
        ForeignKey("rules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rule_version = Column(Integer, nullable=False)
    symbol = Column(String(32), nullable=False, index=True)
    timeframe = Column(String(16), nullable=False)
    market_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    dedupe_key = Column(String(200), nullable=False)
    explanation = Column(JSON, nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

