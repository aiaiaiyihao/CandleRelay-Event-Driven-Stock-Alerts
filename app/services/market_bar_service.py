import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.events import MarketEvent
from app.models.MarketBar import MarketBar


@dataclass(frozen=True)
class ImportResult:
    imported: int
    skipped: int


def import_market_bars_csv(
    path: str | Path,
    symbol: str,
    timeframe: str,
    source: str,
    session: Session,
) -> ImportResult:
    imported = 0
    skipped = 0
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            event = MarketEvent.model_validate(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": row["timestamp"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                    "source": source,
                }
            )
            exists = session.execute(
                select(MarketBar.id).where(
                    MarketBar.symbol == event.symbol,
                    MarketBar.timeframe == event.timeframe,
                    MarketBar.timestamp == event.timestamp,
                )
            ).scalar_one_or_none()
            if exists is not None:
                skipped += 1
                continue
            session.add(
                MarketBar(
                    symbol=event.symbol,
                    timeframe=event.timeframe,
                    timestamp=event.timestamp,
                    open=event.open,
                    high=event.high,
                    low=event.low,
                    close=event.close,
                    volume=event.volume,
                    source=event.source,
                )
            )
            session.flush()
            imported += 1
    session.commit()
    return ImportResult(imported=imported, skipped=skipped)

