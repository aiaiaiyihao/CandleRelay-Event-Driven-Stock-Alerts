import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.yfinance_service import fetch_stock_news_yfinance


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
    set_cache.assert_awaited_once_with("candlerelay:stock-news:NVDA", news, ttl_seconds=300)
