from typing import Literal

from pydantic import BaseModel, Field


class PollRequest(BaseModel):
    symbols: list[str] = Field(
        min_length=1,
        json_schema_extra={"example": ["AAPL", "MSFT"]},
    )
    interval: int = Field(
        ge=1,
        le=86_400,
        description="Polling interval in seconds",
        json_schema_extra={"example": 60},
    )
    provider: Literal["yfinance"] = "yfinance"


class PollAccepted(BaseModel):
    job_id: str
    status: str
    config: PollRequest
