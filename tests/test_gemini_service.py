import asyncio
from unittest.mock import AsyncMock, patch

from app.services.gemini_service import analyze_movers_with_gemini


MOVERS = [{"symbol": "NVDA", "change_percent": 5.0}]
NEWS = [[{
    "title": "NVIDIA announces a new AI platform",
    "summary": "The company introduced new enterprise AI products.",
    "publisher": "Reuters",
    "published_at": "2026-08-11T18:00:00Z",
}]]


def test_gemini_analysis_is_disabled_without_api_key():
    with patch("app.services.gemini_service.GEMINI_API_KEY", ""):
        assert asyncio.run(analyze_movers_with_gemini("Why is NVDA rising?", MOVERS, NEWS)) is None


def test_gemini_analysis_reuses_cached_rag_answer():
    with (
        patch("app.services.gemini_service.GEMINI_API_KEY", "test-key"),
        patch("app.services.gemini_service.get_cached_json", new=AsyncMock(return_value={"answer": "Cached grounded analysis."})),
    ):
        answer = asyncio.run(analyze_movers_with_gemini("Why is NVDA rising?", MOVERS, NEWS))
    assert answer == "Cached grounded analysis."
