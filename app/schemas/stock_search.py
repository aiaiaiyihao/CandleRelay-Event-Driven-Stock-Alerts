from pydantic import BaseModel


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str
