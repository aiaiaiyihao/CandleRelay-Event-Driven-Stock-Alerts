from zoneinfo import ZoneInfo

from sqlalchemy import Column, String, Float, DateTime, Index
from datetime import datetime, timezone
from app.core.config import Base

#table for saving MA data
class MovingAverage(Base):
    __tablename__ = "symbol_averages"

    symbol = Column(String, primary_key=True)
    ma_5 = Column(Float)
    california_time = datetime.now(ZoneInfo("America/Los_Angeles"))
    timestamp = Column(DateTime, default=california_time)
    provider = Column(String)

    # Create a composite index on (symbol, timestamp) to speed up queries
    __table_args__ = (
        Index("ix_movingAverage_symbol_timestamp", "symbol", "timestamp"),
    )