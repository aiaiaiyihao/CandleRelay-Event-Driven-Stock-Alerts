from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from app.core.config import Base


def utc_now():
    return datetime.now(timezone.utc)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    symbol = Column(String(32), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

