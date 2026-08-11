from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.events import MarketEvent
from app.kafka.market_events import decode_market_event, encode_market_event


def event():
    return MarketEvent.model_validate(
        {
            "symbol": "NVDA",
            "timeframe": "1d",
            "timestamp": "2026-08-10T20:00:00Z",
            "open": "180.10",
            "high": "185.20",
            "low": "175.30",
            "close": "176.42",
            "volume": 50_000_000,
            "source": "provider",
        }
    )


def test_market_event_round_trips_without_losing_price_precision():
    restored = decode_market_event(encode_market_event(event()))

    assert restored == event()
    assert restored.close == Decimal("176.42")


def test_decoder_validates_untrusted_kafka_payload():
    with pytest.raises(ValidationError):
        decode_market_event(
            {
                "symbol": "NVDA",
                "timeframe": "1d",
                "timestamp": "not-a-date",
                "close": -1,
            }
        )
