from datetime import datetime

from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    sparkline: list[float]


class SectorSnapshot(MarketSnapshot):
    slug: str


class MarketOverview(BaseModel):
    indexes: list[MarketSnapshot]
    gainers: list[MarketSnapshot]
    losers: list[MarketSnapshot]
    sectors: list[SectorSnapshot] = []
    scope: str = "Active US-listed stocks"
    market_state: str = "CLOSED"
    updated_at: datetime | None = None
    data_source: str = "yfinance"
    data_status: str = "live"


class SectorStocksResponse(BaseModel):
    sector: str
    slug: str
    page: int
    page_size: int
    total: int
    stocks: list[MarketSnapshot]
    updated_at: datetime | None = None
