from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.events import MarketEvent


class BacktestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    events: list[MarketEvent] = Field(min_length=1, max_length=10_000)


class BacktestResponse(BaseModel):
    id: str
    rule_id: str
    rule_version: int
    engine_version: str
    status: str
    bars_processed: int
    trigger_count: int
    result_summary: dict | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None

