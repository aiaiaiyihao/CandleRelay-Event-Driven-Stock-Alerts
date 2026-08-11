from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.market_router import router


def test_market_overview_returns_indexes_and_rankings():
    overview = {
        "indexes": [{"symbol": "^GSPC", "name": "S&P 500", "price": 6400, "change": 20, "change_percent": 0.31, "sparkline": [6380, 6400]}],
        "gainers": [{"symbol": "NVDA", "name": "NVDA", "price": 190, "change": 5, "change_percent": 2.7, "sparkline": [185, 190]}],
        "losers": [{"symbol": "AAPL", "name": "AAPL", "price": 220, "change": -3, "change_percent": -1.35, "sparkline": [223, 220]}],
    }
    app = FastAPI()
    app.include_router(router)
    with patch("app.api.market_router.fetch_market_overview", new=AsyncMock(return_value=overview)):
        response = TestClient(app).get("/market/overview")

    assert response.status_code == 200
    assert response.json()["indexes"][0]["symbol"] == "^GSPC"
    assert response.json()["gainers"][0]["change_percent"] == 2.7
    assert response.json()["losers"][0]["change_percent"] == -1.35
