from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FavoriteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9.^\-]+$")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.upper()


class FavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    created_at: datetime


class FavoriteNewsItem(BaseModel):
    symbol: str
    title: str
    publisher: str
    published_at: datetime | None = None
    url: str
    summary: str | None = None
