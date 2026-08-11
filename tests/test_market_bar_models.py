from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import Base
from app.models.MarketBar import MarketBar


def make_bar():
    return MarketBar(
        symbol="NVDA",
        timeframe="1d",
        timestamp=datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc),
        open=Decimal("180.10"),
        high=Decimal("185.20"),
        low=Decimal("175.30"),
        close=Decimal("176.42"),
        volume=50_000_000,
        source="fixture",
    )


def test_persists_decimal_ohlcv_bar():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    bar = make_bar()
    session.add(bar)
    session.commit()

    stored = session.get(MarketBar, bar.id)
    assert stored.close == Decimal("176.42000000")
    assert stored.volume == 50_000_000
    session.close()


def test_rejects_duplicate_symbol_timeframe_timestamp():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add_all([make_bar(), make_bar()])

    with pytest.raises(IntegrityError):
        session.commit()
    session.close()
