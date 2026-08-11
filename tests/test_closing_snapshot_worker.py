import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from app.workers.closing_snapshot import (
    POPULAR_SYMBOLS,
    create_closing_snapshot,
    should_run_closing_snapshot,
)


NEW_YORK = ZoneInfo("America/New_York")


def test_scheduler_runs_after_405_et_on_weekdays_only():
    assert not should_run_closing_snapshot(datetime(2026, 8, 14, 16, 4, tzinfo=NEW_YORK))
    assert should_run_closing_snapshot(datetime(2026, 8, 14, 16, 5, tzinfo=NEW_YORK))
    assert not should_run_closing_snapshot(datetime(2026, 8, 15, 16, 5, tzinfo=NEW_YORK))


def test_closing_snapshot_refreshes_dashboard_and_deduplicated_stocks():
    overview = {"gainers": [], "losers": []}
    with (
        patch("app.workers.closing_snapshot.fetch_market_overview", new=AsyncMock(return_value=overview)) as dashboard,
        patch("app.workers.closing_snapshot.load_favorite_symbols", return_value={"NVDA", "IBM"}),
        patch("app.workers.closing_snapshot.refresh_stock_details", new=AsyncMock()) as details,
    ):
        asyncio.run(create_closing_snapshot())

    dashboard.assert_awaited_once_with(force_refresh=True, refresh_closed_snapshot=True)
    details.assert_awaited_once_with(POPULAR_SYMBOLS | {"IBM"})
