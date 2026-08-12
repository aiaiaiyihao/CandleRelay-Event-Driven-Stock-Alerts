import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.yfinance_service import fetch_stock_news_yfinance, stock_news_cache_seconds


def test_stock_news_normalizes_and_caches_latest_items():
    ticker = MagicMock()
    ticker.news = [{
        "content": {
            "title": "NVIDIA expands its AI platform",
            "provider": {"displayName": "Reuters"},
            "pubDate": "2026-08-11T18:00:00Z",
            "canonicalUrl": {"url": "https://example.com/nvidia"},
        }
    }]

    with (
        patch("app.services.yfinance_service.get_cached_json", new=AsyncMock(return_value=None)),
        patch("app.services.yfinance_service.set_cached_json", new=AsyncMock()) as set_cache,
        patch("app.services.yfinance_service.yf.Ticker", return_value=ticker),
    ):
        news = asyncio.run(fetch_stock_news_yfinance("nvda"))

    assert news == [{
        "title": "NVIDIA expands its AI platform",
        "publisher": "Reuters",
        "published_at": "2026-08-11T18:00:00Z",
        "url": "https://example.com/nvidia",
    }]
    set_cache.assert_awaited_once()
    assert set_cache.await_args.kwargs["ttl_seconds"] in {300, 900, 3600}


def test_stock_news_cache_ttl_follows_us_market_session():
    assert stock_news_cache_seconds(datetime.fromisoformat("2026-08-11T14:00:00+00:00")) == 300
    assert stock_news_cache_seconds(datetime.fromisoformat("2026-08-11T21:00:00+00:00")) == 900
    assert stock_news_cache_seconds(datetime.fromisoformat("2026-08-09T18:00:00+00:00")) == 3600
