from datetime import datetime

from pydantic import BaseModel


class StockChartPoint(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None


class StockChartResponse(BaseModel):
    symbol: str
    range: str
    interval: str
    points: list[StockChartPoint]

