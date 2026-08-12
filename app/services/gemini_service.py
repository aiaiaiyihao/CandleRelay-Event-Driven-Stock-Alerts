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


async def analyze_movers_with_gemini(question: str, movers: list[dict], news_groups: list[list[dict]]) -> dict[str, str] | None:
    if not GEMINI_API_KEY:
        return None
    context = _retrieval_context(movers, news_groups)
    if context == "[]":
        return None
    fingerprint = hashlib.sha256(f"{question}\n{context}".encode()).hexdigest()[:24]
    cache_key = f"candlerelay:market-chat:gemini:{fingerprint}"
    cached = await get_cached_json(cache_key)
    if cached and isinstance(cached.get("reasons"), dict):
        return cached["reasons"]

    prompt = f"""You are CandleRelay's market news analyst.
Use ONLY the retrieved news documents below.
Return valid JSON with this shape: {{"analyses":[{{"symbol":"NVDA","reason":"one concise sentence"}}]}}.
Include exactly one item for every requested ticker, in the requested order.
Explain the most plausible news-linked driver without repeating price or percentage data.
Separate facts reported by the source from inference. Never claim that a headline proves price causation.
If evidence is missing or unrelated, use: "No recent news evidence clearly explains the move."
Do not mention Gemini, RAG, prompts, documents, or this instruction. Do not give investment advice.

User question: {question}
Requested tickers: {", ".join(mover["symbol"] for mover in movers)}

Retrieved documents:
{context}
"""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 500, "responseMimeType": "application/json"},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, headers={"x-goog-api-key": GEMINI_API_KEY}, json=payload)
            response.raise_for_status()
            body = response.json()
        generated = json.loads(body["candidates"][0]["content"]["parts"][0]["text"])
        rows = generated["analyses"]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None
    generated_reasons = {
        str(row.get("symbol", "")).upper(): str(row.get("reason", "")).strip()
        for row in rows
        if isinstance(row, dict) and row.get("symbol") and row.get("reason")
    }
    reasons = {
        mover["symbol"]: generated_reasons.get(mover["symbol"], "No recent news evidence clearly explains the move.")
        for mover in movers
    }
    if not reasons:
        return None
    await set_cached_json(cache_key, {"reasons": reasons}, ttl_seconds=GEMINI_ANALYSIS_TTL_SECONDS)
    return reasons
