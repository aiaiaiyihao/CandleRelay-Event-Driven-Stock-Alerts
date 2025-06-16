from typing import List
from pydantic import BaseModel, Field

class PollRequest(BaseModel):
    symbols: List[str] = Field(..., example=["AAPL", "MSFT"])
    interval: int = Field(..., example=60, description="Polling interval in seconds")
    provider: str = Field(..., example="alpha_vantage")

class PollAccepted(BaseModel):
    job_id: str
    status: str
    config: PollRequest