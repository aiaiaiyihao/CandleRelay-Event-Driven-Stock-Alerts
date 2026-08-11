from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, UniqueConstraint

from app.core.config import Base


def utc_now():
    return datetime.now(timezone.utc)


class MarketBar(Base):
    __tablename__ = "market_bars"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "timeframe",
            "timestamp",
            name="uq_market_bars_symbol_timeframe_timestamp",
        ),
    )

    id = Column(Integer, primary_key=True)
    symbol = Column(String(32), nullable=False, index=True)
    timeframe = Column(String(16), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(BigInteger, nullable=False)
    source = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

