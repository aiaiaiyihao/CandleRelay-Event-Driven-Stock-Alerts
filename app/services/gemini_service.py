import hashlib
import json

import httpx

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from app.services.cache import get_cached_json, set_cached_json


GEMINI_ANALYSIS_TTL_SECONDS = 300


def _retrieval_context(movers: list[dict], news_groups: list[list[dict]]) -> str:
    documents = []
    for mover, stories in zip(movers, news_groups):
        for story in stories[:3]:
            documents.append({
                "symbol": mover["symbol"],
                "daily_change_percent": mover["change_percent"],
                "headline": story["title"],
                "summary": story.get("summary") or "No summary supplied by the news provider.",
                "publisher": story.get("publisher"),
                "published_at": story.get("published_at"),
            })
    return json.dumps(documents, ensure_ascii=False, default=str)


async def analyze_movers_with_gemini(question: str, movers: list[dict], news_groups: list[list[dict]]) -> str | None:
    if not GEMINI_API_KEY:
        return None
    context = _retrieval_context(movers, news_groups)
    if context == "[]":
        return None
    fingerprint = hashlib.sha256(f"{question}\n{context}".encode()).hexdigest()[:24]
    cache_key = f"candlerelay:market-chat:gemini:{fingerprint}"
    cached = await get_cached_json(cache_key)
    if cached:
        return cached.get("answer")

    prompt = f"""You are CandleRelay's market news analyst.
Answer the user's question using ONLY the retrieved news documents below.
For each relevant ticker, explain the most plausible news-linked driver in one concise sentence.
Separate facts reported by the source from inference. Never claim that a headline proves price causation.
If evidence is missing or unrelated, say so. Do not give investment advice.

User question: {question}

Retrieved documents:
{context}
"""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 500},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers={"x-goog-api-key": GEMINI_API_KEY}, json=payload)
            response.raise_for_status()
            body = response.json()
        answer = body["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None
    if not answer:
        return None
    await set_cached_json(cache_key, {"answer": answer}, ttl_seconds=GEMINI_ANALYSIS_TTL_SECONDS)
    return answer
