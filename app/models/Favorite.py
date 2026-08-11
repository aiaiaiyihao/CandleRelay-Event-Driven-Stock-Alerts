from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String

from app.core.config import Base


def utc_now():
    return datetime.now(timezone.utc)


class Favorite(Base):
    __tablename__ = "favorites"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    symbol = Column(String(32), primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
