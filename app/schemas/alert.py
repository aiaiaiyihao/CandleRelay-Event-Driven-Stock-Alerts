from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: str
    rule_id: str
    rule_version: int
    symbol: str
    timeframe: str
    market_timestamp: datetime
    explanation: dict
    acknowledged: bool
    created_at: datetime
    acknowledged_at: datetime | None

