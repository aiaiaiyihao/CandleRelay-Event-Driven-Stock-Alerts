from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.priceRouter import router


def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_stock_search_returns_ticker_suggestions():
    suggestions = [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NasdaqGS",
            "type": "EQUITY",
        }
    ]
    with patch(
        "app.api.priceRouter.search_stocks_yfinance",
        new=AsyncMock(return_value=suggestions),
    ):
        response = client().get("/stocks/search", params={"q": "app"})

    assert response.status_code == 200
    assert response.json() == suggestions


def test_stock_search_rejects_empty_queries():
    response = client().get("/stocks/search", params={"q": ""})

    assert response.status_code == 422


def test_stock_detail_returns_market_statistics():
    detail = {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "price": 190,
        "previous_close": 185,
        "change": 5,
        "change_percent": 2.7,
        "market_cap": 4_000_000_000_000,
    }
    with patch("app.api.priceRouter.fetch_stock_detail_yfinance", new=AsyncMock(return_value=detail)):
        response = client().get("/stocks/nvda/detail")

    assert response.status_code == 200
    assert response.json()["symbol"] == "NVDA"
    assert response.json()["market_cap"] == 4_000_000_000_000
