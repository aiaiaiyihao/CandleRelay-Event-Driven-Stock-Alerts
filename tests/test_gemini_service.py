import asyncio
from unittest.mock import AsyncMock, patch

from app.services.gemini_service import analyze_movers_with_gemini


MOVERS = [{"symbol": "NVDA", "change_percent": 5.0}]
NEWS = [[{
    "title": "NVIDIA announces a new AI platform",
    "summary": "The company introduced new enterprise AI products.",
    "publisher": "Reuters",
    "published_at": "2026-08-11T18:00:00Z",
    "url": "https://example.com/nvda-news",
}]]


def test_gemini_analysis_is_disabled_without_api_key():
    with patch("app.services.gemini_service.GEMINI_API_KEY", ""):
        assert asyncio.run(analyze_movers_with_gemini("Why is NVDA rising?", MOVERS, NEWS)) is None


def test_gemini_analysis_reuses_cached_rag_answer():
    with (
        patch("app.services.gemini_service.GEMINI_API_KEY", "test-key"),
        patch("app.services.gemini_service.get_cached_json", new=AsyncMock(return_value={"reasons": {"NVDA": "Cached grounded analysis."}})),
    ):
        answer = asyncio.run(analyze_movers_with_gemini("Why is NVDA rising?", MOVERS, NEWS))
    assert answer == {"NVDA": "Cached grounded analysis."}


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "steps": [{
                "type": "model_output",
                "content": [{"type": "text", "text": '{"analyses":[{"symbol":"NVDA","reason":"Revenue news may have supported the move."}]}'}],
            }],
        }


class FakeClient:
    def __init__(self):
        self.payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def post(self, url, headers, json):
        assert url.endswith("/v1beta/interactions")
        assert headers["x-goog-api-key"] == "test-key"
        assert json["tools"] == [{"type": "url_context"}]
        assert "https://example.com/nvda-news" in json["input"]
        self.payload = json
        return FakeResponse()


def test_gemini_uses_cached_news_urls_with_url_context():
    cache_write = AsyncMock()
    with (
        patch("app.services.gemini_service.GEMINI_API_KEY", "test-key"),
        patch("app.services.gemini_service.get_cached_json", new=AsyncMock(return_value=None)),
        patch("app.services.gemini_service.set_cached_json", new=cache_write),
        patch("app.services.gemini_service.httpx.AsyncClient", return_value=FakeClient()),
    ):
        answer = asyncio.run(analyze_movers_with_gemini("Why is NVDA rising?", MOVERS, NEWS))
    assert answer == {"NVDA": "Revenue news may have supported the move."}
    assert cache_write.await_args.kwargs["ttl_seconds"] == 1800
