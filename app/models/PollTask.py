from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Integer, DateTime, JSON, Interval,Index
from app.core.config import Base

class PollTask(Base):
    __tablename__ = "poll_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    symbols = Column(JSON, nullable=False)
    provider = Column(String, nullable=False)
    interval = Column(Integer, nullable=False)
    status = Column(String, default="running")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_run_at = Column(DateTime)