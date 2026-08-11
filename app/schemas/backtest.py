from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.events import MarketEvent


class BacktestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    events: list[MarketEvent] = Field(min_length=1, max_length=10_000)


class BacktestRangeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=1)
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_range(self):
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("start and end must include timezone information")
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


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
