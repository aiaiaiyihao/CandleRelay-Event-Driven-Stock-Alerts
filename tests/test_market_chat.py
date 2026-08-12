from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.market_router import router


def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_market_chat_answers_ticker_price_from_stock_detail():
    detail = {"symbol": "NVDA", "name": "NVIDIA", "price": 190.0, "change_percent": 2.5, "updated_at": "2026-08-11T18:00:00Z"}
    with patch("app.services.market_chat_service.fetch_stock_detail_yfinance", new=AsyncMock(return_value=detail)):
        response = client().post("/market/chat", json={"question": "What is NVDA price?"})
    assert response.status_code == 200
    assert response.json()["intent"] == "price"
    assert "$190.00" in response.json()["answer"]


def test_market_chat_combines_gainers_with_news_context():
    overview = {"gainers": [{"symbol": "NVDA", "name": "NVIDIA", "price": 190.0, "change_percent": 5.0}], "losers": [], "updated_at": "2026-08-11T18:00:00Z"}
    news = [{"title": "NVIDIA announces new AI platform", "publisher": "Reuters", "url": "https://example.com/nvda"}]
    with (
        patch("app.services.market_chat_service.fetch_market_overview", new=AsyncMock(return_value=overview)),
        patch("app.services.market_chat_service.fetch_stock_news_yfinance", new=AsyncMock(return_value=news)),
        patch("app.services.market_chat_service.analyze_movers_with_gemini", new=AsyncMock(return_value="NVDA's move may be linked to its reported AI platform announcement.")),
    ):
        response = client().post("/market/chat", json={"question": "Why are the strongest stocks rising?"})
    body = response.json()
    assert body["intent"] == "strong"
    assert "Gemini RAG analysis" in body["answer"]
    assert "AI platform announcement" in body["answer"]
    assert body["sources"][0]["symbol"] == "NVDA"


def test_market_chat_returns_help_for_unsupported_question():
    response = client().post("/market/chat", json={"question": "Tell me something interesting"})
    assert response.status_code == 200
    assert response.json()["intent"] == "help"
