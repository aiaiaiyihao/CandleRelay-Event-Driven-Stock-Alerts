import asyncio
from unittest.mock import AsyncMock, patch

from app.services.cache import get_cached_json, set_cached_json


def test_json_cache_round_trip_contract():
    with patch("app.services.cache.redis.get", new=AsyncMock(return_value='{"symbol":"NVDA"}')):
        assert asyncio.run(get_cached_json("detail")) == {"symbol": "NVDA"}

    setter = AsyncMock()
    with patch("app.services.cache.redis.setex", new=setter):
        asyncio.run(set_cached_json("detail", {"symbol": "NVDA"}, 60))

    setter.assert_awaited_once_with("detail", 60, '{"symbol": "NVDA"}')


def test_json_cache_failure_falls_back_without_raising():
    with patch("app.services.cache.redis.get", new=AsyncMock(side_effect=ConnectionError)):
        assert asyncio.run(get_cached_json("detail")) is None
