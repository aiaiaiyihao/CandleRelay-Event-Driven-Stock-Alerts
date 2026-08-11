import asyncio
import logging
from datetime import datetime, time as datetime_time

from app.core.config import SessionLocal, redis
from app.models.Favorite import Favorite
from app.services.yfinance_service import (
    US_MARKET_TIMEZONE,
    fetch_market_overview,
    fetch_stock_detail_yfinance,
    seconds_until_next_us_market_open,
)


POPULAR_SYMBOLS = {"AAPL", "AMZN", "GOOGL", "META", "MSFT", "NVDA", "QCOM", "TSLA"}
CLOSING_SNAPSHOT_TIME = datetime_time(16, 5)


def should_run_closing_snapshot(now: datetime | None = None) -> bool:
    current = (now or datetime.now(US_MARKET_TIMEZONE)).astimezone(US_MARKET_TIMEZONE)
    return current.weekday() < 5 and current.time() >= CLOSING_SNAPSHOT_TIME


def load_favorite_symbols() -> set[str]:
    with SessionLocal() as session:
        return {symbol for (symbol,) in session.query(Favorite.symbol).distinct().all()}


async def refresh_stock_details(symbols: set[str], concurrency: int = 5) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def refresh(symbol: str) -> None:
        async with semaphore:
            try:
                await fetch_stock_detail_yfinance(
                    symbol,
                    force_refresh=True,
                    refresh_closed_snapshot=True,
                )
            except ValueError as exc:
                logging.warning("Closing detail snapshot skipped for %s: %s", symbol, exc)

    await asyncio.gather(*(refresh(symbol) for symbol in sorted(symbols)))


async def create_closing_snapshot() -> None:
    overview = await fetch_market_overview(
        force_refresh=True,
        refresh_closed_snapshot=True,
    )
    favorites = await asyncio.to_thread(load_favorite_symbols)
    await refresh_stock_details(POPULAR_SYMBOLS | favorites)
    logging.info(
        "Closing snapshot cached: %d gainers, %d losers, %d stock details",
        len(overview["gainers"]),
        len(overview["losers"]),
        len(POPULAR_SYMBOLS | favorites),
    )


async def run_scheduler() -> None:
    logging.info("Closing snapshot worker waiting for 4:05 PM ET")
    while True:
        current = datetime.now(US_MARKET_TIMEZONE)
        if should_run_closing_snapshot(current):
            lock_key = f"candlerelay:closing-snapshot-run:{current.date().isoformat()}"
            acquired = await redis.set(
                lock_key,
                current.isoformat(),
                ex=seconds_until_next_us_market_open(current),
                nx=True,
            )
            if acquired:
                try:
                    await create_closing_snapshot()
                except Exception:
                    await redis.delete(lock_key)
                    logging.exception("Closing snapshot failed; lock released for retry")
        await asyncio.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(run_scheduler())
