from datetime import datetime

from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    sparkline: list[float]


class MarketOverview(BaseModel):
    indexes: list[MarketSnapshot]
    gainers: list[MarketSnapshot]
    losers: list[MarketSnapshot]
    scope: str = "US large-cap stocks"
    market_state: str = "CLOSED"
    updated_at: datetime | None = None
