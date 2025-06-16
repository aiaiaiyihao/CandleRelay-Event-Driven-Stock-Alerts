from zoneinfo import ZoneInfo

from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from app.core.config import Base
from datetime import datetime, timezone


class RawPrice(Base):
    __tablename__ = "raw_market_data"

    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    provider = Column(String)

    # Create a composite index on (symbol, timestamp) to speed up queries
    __table_args__ = (
        Index("ix_raw_symbol_timestamp", "symbol", "timestamp"),
    )