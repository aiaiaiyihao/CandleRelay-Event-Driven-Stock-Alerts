from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.events import MarketEvent


def event_data(**overrides):
    data = {
        "symbol": "nvda",
        "timeframe": "1d",
        "timestamp": "2026-08-10T20:00:00Z",
        "open": "180.00",
        "high": "185.00",
        "low": "175.00",
        "close": "176.42",
        "volume": 50_000_000,
        "source": "historical-test",
    }
    data.update(overrides)
    return data


def test_normalizes_market_event_and_preserves_decimal_prices():
    event = MarketEvent.model_validate(event_data())

    assert event.symbol == "NVDA"
    assert event.price == Decimal("176.42")
    assert event.timestamp == datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "overrides",
    [
        {"timestamp": "2026-08-10T20:00:00"},
        {"high": "170.00"},
        {"low": "190.00"},
        {"volume": -1},
        {"close": 0},
    ],
)
def test_rejects_invalid_market_events(overrides):
    with pytest.raises(ValidationError):
        MarketEvent.model_validate(event_data(**overrides))


def test_market_events_are_immutable():
    event = MarketEvent.model_validate(event_data())

    with pytest.raises(ValidationError):
        event.close = Decimal("200")
