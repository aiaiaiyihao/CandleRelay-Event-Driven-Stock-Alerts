from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.rules import Timeframe


class MarketEvent(BaseModel):
    """A normalized, immutable OHLCV event used by live and replay sources."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=True)

    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9.\-]+$")
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: int = Field(ge=0)
    source: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def normalize_and_validate_bar(self):
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close, and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close, and high")
        object.__setattr__(self, "symbol", self.symbol.upper())
        return self

    @property
    def price(self) -> Decimal:
        return self.close

