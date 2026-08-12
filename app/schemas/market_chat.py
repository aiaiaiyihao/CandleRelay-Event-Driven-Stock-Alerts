from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MarketChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    context_symbol: str | None = Field(default=None, pattern=r"^[A-Za-z]{1,5}(?:\.[A-Za-z])?$")


class MarketChatSource(BaseModel):
    symbol: str
    title: str
    url: str


class MarketChatResponse(BaseModel):
    intent: Literal["price", "news", "strong", "weak", "help"]
    answer: str
    updated_at: datetime | None = None
    sources: list[MarketChatSource] = Field(default_factory=list)
