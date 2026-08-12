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


def test_market_chat_uses_context_symbol_for_follow_up_news_question():
    detail = {
        "symbol": "NVDA",
        "name": "NVIDIA",
        "price": 190.0,
        "change_percent": 2.5,
        "updated_at": "2026-08-11T18:00:00Z",
        "news": [{"title": "NVIDIA announces new AI platform", "url": "https://example.com/nvda"}],
    }
    with (
        patch("app.services.market_chat_service.fetch_stock_detail_yfinance", new=AsyncMock(return_value=detail)),
        patch("app.services.market_chat_service.summarize_stock_news_with_gemini", new=AsyncMock(return_value="• NVIDIA announced a new AI platform.")),
    ):
        response = client().post("/market/chat", json={"question": "What are the news for it today?", "context_symbol": "nvda"})
    assert response.status_code == 200
    assert response.json()["intent"] == "news"
    assert "Recent news for NVIDIA (NVDA)" in response.json()["answer"]
    assert "announced a new AI platform" in response.json()["answer"]
    assert response.json()["sources"][0]["symbol"] == "NVDA"


def test_market_chat_returns_price_and_news_for_a_simple_ticker_status_question():
    detail = {
        "symbol": "NIQ",
        "name": "NIQ Global Intelligence",
        "price": 15.5,
        "change_percent": -1.2,
        "updated_at": "2026-08-11T18:00:00Z",
        "news": [{"title": "NIQ releases new consumer outlook", "url": "https://example.com/niq"}],
    }
    with (
        patch("app.services.market_chat_service.fetch_stock_detail_yfinance", new=AsyncMock(return_value=detail)),
        patch("app.services.market_chat_service.summarize_stock_news_with_gemini", new=AsyncMock(return_value="• NIQ released a new consumer outlook.")),
    ):
        response = client().post("/market/chat", json={"question": "How is NIQ?"})
    assert response.status_code == 200
    assert response.json()["intent"] == "stock"
    assert "NIQ Global Intelligence (NIQ) is $15.50, down 1.20% today." in response.json()["answer"]
    assert "Recent news:" in response.json()["answer"]


def test_market_chat_skips_question_words_when_extracting_a_ticker():
    detail = {
        "symbol": "SE",
        "name": "Sea Limited",
        "price": 150.0,
        "change_percent": 1.0,
        "updated_at": "2026-08-11T18:00:00Z",
        "news": [{"title": "Sea Limited reports results", "url": "https://example.com/se"}],
    }
    with (
        patch("app.services.market_chat_service.fetch_stock_detail_yfinance", new=AsyncMock(return_value=detail)) as fetch_detail,
        patch("app.services.market_chat_service.summarize_stock_news_with_gemini", new=AsyncMock(return_value="• Sea Limited reported results.")),
    ):
        response = client().post("/market/chat", json={"question": "HOW is SE?"})
    assert response.status_code == 200
    assert response.json()["intent"] == "stock"
    fetch_detail.assert_awaited_once_with("SE")


def test_market_chat_returns_top_ten_gainers_and_losers_for_market_status_question():
    overview = {
        "gainers": [{"symbol": f"GAIN{index}", "price": 10.0 + index, "change_percent": 10.0 - index} for index in range(10)],
        "losers": [{"symbol": f"LOSE{index}", "price": 10.0 + index, "change_percent": -1.0 - index} for index in range(10)],
        "updated_at": "2026-08-11T18:00:00Z",
    }
    with patch("app.services.market_chat_service.fetch_market_overview", new=AsyncMock(return_value=overview)):
        response = client().post("/market/chat", json={"question": "How is the market?"})
    assert response.status_code == 200
    assert response.json()["intent"] == "market"
    assert "Today's Top 10 Gainers:" in response.json()["answer"]
    assert "Today's Top 10 Losers:" in response.json()["answer"]
    assert "GAIN9" in response.json()["answer"]
    assert "LOSE9" in response.json()["answer"]


def test_market_chat_combines_gainers_with_news_context():
    overview = {"gainers": [{"symbol": "NVDA", "name": "NVIDIA", "price": 190.0, "change_percent": 5.0}], "losers": [], "updated_at": "2026-08-11T18:00:00Z"}
    news = [{"title": "NVIDIA announces new AI platform", "publisher": "Reuters", "url": "https://example.com/nvda"}]
    with (
        patch("app.services.market_chat_service.fetch_market_overview", new=AsyncMock(return_value=overview)),
        patch("app.services.market_chat_service.fetch_stock_news_yfinance", new=AsyncMock(return_value=news)),
        patch("app.services.market_chat_service.analyze_movers_with_gemini", new=AsyncMock(return_value={"NVDA": "Its reported AI platform announcement may have supported buying interest."})),
    ):
        response = client().post("/market/chat", json={"question": "Why are the strongest stocks rising?"})
    body = response.json()
    assert body["intent"] == "strong"
    assert "Gemini" not in body["answer"]
    assert "NVDA rose 5.00% to $190.00 —" in body["answer"]
    assert "AI platform announcement" in body["answer"]
    assert body["sources"][0]["symbol"] == "NVDA"


def test_market_chat_returns_help_for_unsupported_question():
    response = client().post("/market/chat", json={"question": "Tell me something interesting"})
    assert response.status_code == 200
    assert response.json()["intent"] == "help"


def test_market_chat_refreshes_only_one_stock_when_cached_news_has_no_url():
    detail = {"symbol": "NVDA", "name": "NVIDIA", "price": 190.0, "change_percent": 5.0, "updated_at": "2026-08-11T18:00:00Z", "news": [{"title": "Cached title", "url": ""}]}
    refreshed = [{"title": "NVIDIA launches an AI platform", "url": "https://example.com/nvda", "summary": "New products", "publisher": "Reuters"}]
    with (
        patch("app.services.market_chat_service.fetch_stock_detail_yfinance", new=AsyncMock(return_value=detail)),
        patch("app.services.market_chat_service.fetch_stock_news_yfinance", new=AsyncMock(return_value=refreshed)) as fetch_news,
        patch("app.services.market_chat_service.analyze_movers_with_gemini", new=AsyncMock(return_value={"NVDA": "Its platform launch may have supported buying interest."})),
    ):
        response = client().post("/market/chat", json={"question": "Why is NVDA rising?"})
    assert response.status_code == 200
    assert "NVDA rose 5.00%" in response.json()["answer"]
    fetch_news.assert_awaited_once_with("NVDA", force_refresh=True)
