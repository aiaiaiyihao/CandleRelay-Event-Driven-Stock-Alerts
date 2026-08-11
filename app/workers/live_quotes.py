import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, time as datetime_time, timezone

import yfinance as yf
from sqlalchemy import select

from app.core.config import SessionLocal, redis
from app.domain.events import MarketEvent
from app.kafka.Producer import send_market_event
from app.models.Rule import Rule
from app.services.yfinance_service import US_MARKET_TIMEZONE


SUBSCRIPTION_REFRESH_SECONDS = 15
CURRENT_PRICE_TTL_SECONDS = 120
INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}


def load_active_rule_targets() -> set[tuple[str, str]]:
    with SessionLocal() as session:
        return {
            (symbol, timeframe)
            for symbol, timeframe in session.execute(
                select(Rule.symbol, Rule.timeframe).where(Rule.enabled.is_(True)).distinct()
            )
        }


def stream_timestamp(value: int | float | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    seconds = float(value) / 1000 if float(value) > 10_000_000_000 else float(value)
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def bucket_start(timestamp: datetime, timeframe: str) -> datetime:
    if timeframe == "1d":
        local = timestamp.astimezone(US_MARKET_TIMEZONE)
        return datetime.combine(local.date(), datetime_time(), tzinfo=US_MARKET_TIMEZONE).astimezone(timezone.utc)
    interval = INTERVAL_SECONDS[timeframe]
    epoch = int(timestamp.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % interval), tz=timezone.utc)


@dataclass
class PendingBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    initial_volume: int
    latest_volume: int

    def update(self, price: float, cumulative_volume: int) -> None:
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.latest_volume = max(self.latest_volume, cumulative_volume)

    def event(self, symbol: str, timeframe: str) -> MarketEvent:
        return MarketEvent(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=self.timestamp,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=max(0, self.latest_volume - self.initial_volume),
            source="yahoo-websocket",
        )


class BarAggregator:
    def __init__(self):
        self._bars: dict[tuple[str, str], PendingBar] = {}

    def update(
        self,
        symbol: str,
        timeframe: str,
        price: float,
        timestamp: datetime,
        cumulative_volume: int,
    ) -> MarketEvent | None:
        key = (symbol, timeframe)
        start = bucket_start(timestamp, timeframe)
        current = self._bars.get(key)
        if current is None:
            self._bars[key] = PendingBar(start, price, price, price, price, cumulative_volume, cumulative_volume)
            return None
        if current.timestamp == start:
            current.update(price, cumulative_volume)
            return None
        completed = current.event(symbol, timeframe)
        self._bars[key] = PendingBar(start, price, price, price, price, cumulative_volume, cumulative_volume)
        return completed


class LiveQuoteWorker:
    def __init__(self):
        self.targets: set[tuple[str, str]] = set()
        self.aggregator = BarAggregator()

    async def handle_message(self, message: dict) -> None:
        symbol = str(message.get("id") or message.get("symbol") or "").upper()
        price = message.get("price")
        if not symbol or price is None:
            return
        timestamp = stream_timestamp(message.get("time"))
        volume = int(message.get("day_volume") or message.get("dayVolume") or 0)
        await redis.set(
            f"candlerelay:live-price:{symbol}",
            json.dumps({"symbol": symbol, "price": float(price), "timestamp": timestamp.isoformat()}),
            ex=CURRENT_PRICE_TTL_SECONDS,
        )
        for target_symbol, timeframe in self.targets:
            if target_symbol != symbol:
                continue
            event = self.aggregator.update(symbol, timeframe, float(price), timestamp, volume)
            if event is not None:
                send_market_event(event)

    async def sync_subscriptions(self, socket) -> None:
        while True:
            latest = await asyncio.to_thread(load_active_rule_targets)
            current_symbols = {symbol for symbol, _ in self.targets}
            latest_symbols = {symbol for symbol, _ in latest}
            additions = sorted(latest_symbols - current_symbols)
            removals = sorted(current_symbols - latest_symbols)
            if additions:
                await socket.subscribe(additions)
            if removals:
                await socket.unsubscribe(removals)
            if additions or removals:
                logging.info("Live alert subscriptions: +%s -%s", additions, removals)
            self.targets = latest
            await asyncio.sleep(SUBSCRIPTION_REFRESH_SECONDS)

    async def run(self) -> None:
        while True:
            try:
                async with yf.AsyncWebSocket(verbose=False) as socket:
                    updater = asyncio.create_task(self.sync_subscriptions(socket))
                    try:
                        await socket.listen(self.handle_message)
                    finally:
                        updater.cancel()
            except Exception:
                logging.exception("Yahoo WebSocket disconnected; retrying")
                await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(LiveQuoteWorker().run())
