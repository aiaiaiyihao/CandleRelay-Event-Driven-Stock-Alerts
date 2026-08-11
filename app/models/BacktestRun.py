from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String

from app.core.config import Base


def utc_now():
    return datetime.now(timezone.utc)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    rule_id = Column(
        String,
        ForeignKey("rules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rule_version = Column(Integer, nullable=False)
    dsl_snapshot = Column(JSON, nullable=False)
    engine_version = Column(String(20), nullable=False, default="1.0")
    status = Column(String(20), nullable=False, default="pending", index=True)
    bars_processed = Column(Integer, nullable=False, default=0)
    trigger_count = Column(Integer, nullable=False, default=0)
    result_summary = Column(JSON, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

