import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from app.services import yfinance_service
from app.services.yfinance_service import (
    fetch_market_overview,
    fetch_stock_detail_yfinance,
    seconds_until_next_us_market_open,
)


NEW_YORK = ZoneInfo("America/New_York")


def test_closed_cache_expires_at_next_weekday_open():
    friday_after_close = datetime(2026, 8, 14, 17, 0, tzinfo=NEW_YORK)

    seconds = seconds_until_next_us_market_open(friday_after_close)

    assert seconds == int((datetime(2026, 8, 17, 9, 30, tzinfo=NEW_YORK) - friday_after_close).total_seconds())


def test_market_overview_returns_closed_snapshot_before_upstream_call():
    snapshot = {
        "indexes": [], "gainers": [], "losers": [], "sectors": [],
        "scope": "Active US-listed stocks", "market_state": "CLOSED",
        "updated_at": "2026-08-14T20:00:00+00:00", "data_source": "yfinance", "data_status": "live",
    }
    yfinance_service._market_overview_cache = None
    with (
        patch("app.services.yfinance_service.get_cached_json", new=AsyncMock(return_value=snapshot)),
        patch("app.services.yfinance_service.fetch_market_snapshots", new=AsyncMock()) as indexes,
        patch("app.services.yfinance_service.fetch_market_movers", new=AsyncMock()) as movers,
    ):
        result = asyncio.run(fetch_market_overview(force_refresh=True))

    assert result == snapshot
    indexes.assert_not_awaited()
    movers.assert_not_awaited()


def test_market_overview_returns_shared_live_redis_snapshot():
    snapshot = {
        "indexes": [], "gainers": [], "losers": [], "sectors": [],
        "scope": "Active US-listed stocks", "market_state": "OPEN",
        "updated_at": "2026-08-14T15:00:00+00:00", "data_source": "yfinance", "data_status": "live",
    }
    yfinance_service._market_overview_cache = None
    with (
        patch("app.services.yfinance_service.get_cached_json", new=AsyncMock(side_effect=[None, snapshot])),
        patch("app.services.yfinance_service.fetch_market_snapshots", new=AsyncMock()) as indexes,
        patch("app.services.yfinance_service.fetch_market_movers", new=AsyncMock()) as movers,
    ):
        result = asyncio.run(fetch_market_overview())

    assert result == snapshot
    indexes.assert_not_awaited()
    movers.assert_not_awaited()


def test_stock_detail_returns_closed_snapshot_even_when_refresh_is_requested():
    snapshot = {
        "symbol": "NVDA", "name": "NVIDIA Corporation", "price": 180.0,
        "market_state": "CLOSED", "updated_at": "2026-08-14T20:00:00+00:00",
    }
    with (
        patch("app.services.yfinance_service.get_cached_json", new=AsyncMock(return_value=snapshot)),
        patch("app.services.yfinance_service.fetch_stock_news_yfinance", new=AsyncMock(return_value=[])),
        patch("app.services.yfinance_service.asyncio.to_thread", new=AsyncMock()) as upstream,
    ):
        result = asyncio.run(fetch_stock_detail_yfinance("NVDA", force_refresh=True))

    assert result["name"] == "NVIDIA Corporation"
    assert result["news"] == []
    upstream.assert_not_awaited()
