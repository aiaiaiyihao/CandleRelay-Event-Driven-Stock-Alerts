import json
from typing import Any

from app.domain.events import MarketEvent


def encode_market_event(event: MarketEvent) -> bytes:
    return event.model_dump_json().encode("utf-8")


def decode_market_event(payload: bytes | str | dict[str, Any]) -> MarketEvent:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        payload = json.loads(payload)
    return MarketEvent.model_validate(payload)

