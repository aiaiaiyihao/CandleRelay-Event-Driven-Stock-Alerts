from datetime import datetime

from pydantic import BaseModel, Field


class StockNewsItem(BaseModel):
    title: str
    publisher: str
    published_at: datetime | None = None
    url: str
    summary: str | None = None


class StockDetailResponse(BaseModel):
    symbol: str
    name: str
    exchange: str | None = None
    currency: str | None = None
    sector: str | None = None
    industry: str | None = None
    price: float
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    volume: int | None = None
    market_cap: int | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    market_state: str | None = None
    updated_at: datetime | None = None
    news: list[StockNewsItem] = Field(default_factory=list)
