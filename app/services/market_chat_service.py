import asyncio
import re

from app.services.gemini_service import analyze_movers_with_gemini
from app.services.yfinance_service import (
    fetch_market_overview,
    fetch_stock_detail_yfinance,
    fetch_stock_news_yfinance,
)


IGNORED_TOKENS = {"WHAT", "WHICH", "WHY", "SHOW", "STOCK", "STOCKS", "PRICE", "TODAY", "STRONG", "STRONGEST", "WEAK", "WEAKEST"}


def _symbol(question: str) -> str | None:
    for token in re.findall(r"\b[A-Z]{1,5}(?:\.[A-Z])?\b", question):
        if token not in IGNORED_TOKENS:
            return token
    return None


def _mover_line(item: dict, reason: str | None = None) -> str:
    direction = "rose" if item["change_percent"] >= 0 else "fell"
    line = f'{item["symbol"]} {direction} {abs(item["change_percent"]):.2f}% to ${item["price"]:.2f}'
    return f"{line} — {reason}" if reason else line


async def answer_market_question(question: str) -> dict:
    normalized = question.strip()
    lowered = normalized.lower()
    symbol = _symbol(normalized)
    if symbol and any(term in lowered for term in ("price", "trading", "quote", "how much")):
        detail = await fetch_stock_detail_yfinance(symbol)
        direction = "up" if (detail.get("change_percent") or 0) >= 0 else "down"
        change = detail.get("change_percent")
        change_text = f", {direction} {abs(change):.2f}% today" if change is not None else ""
        return {
            "intent": "price",
            "answer": f'{detail["name"]} ({symbol}) is ${detail["price"]:.2f}{change_text}.',
            "updated_at": detail.get("updated_at"),
            "sources": [],
        }

    if any(term in lowered for term in ("strong", "strongest", "gainer", "gainers", "rising", "up today")):
        intent = "strong"
        key = "gainers"
        heading = "Strongest stocks in the current Top 50"
    elif any(term in lowered for term in ("weak", "weakest", "loser", "losers", "falling", "down today")):
        intent = "weak"
        key = "losers"
        heading = "Weakest stocks in the current Top 50"
    else:
        return {
            "intent": "help",
            "answer": "Ask for a ticker price, today's strongest stocks, today's weakest stocks, or the news behind those moves.",
            "updated_at": None,
            "sources": [],
        }

    overview = await fetch_market_overview()
    movers = overview[key][:5]
    answer = f'{heading}:\n' + "\n".join(_mover_line(item) for item in movers)
    sources = []
    if any(term in lowered for term in ("why", "reason", "news", "because")) and movers:
        news_groups = await asyncio.gather(*(fetch_stock_news_yfinance(item["symbol"]) for item in movers))
        fallback_reasons = {}
        for item, news in zip(movers, news_groups):
            if not news:
                fallback_reasons[item["symbol"]] = "No recent news evidence clearly explains the move."
                continue
            story = news[0]
            fallback_reasons[item["symbol"]] = f'Recent coverage reports “{story["title"]}”; this provides context but does not prove causation.'
            sources.append({"symbol": item["symbol"], "title": story["title"], "url": story["url"]})
        reasons = await analyze_movers_with_gemini(normalized, movers, news_groups) or fallback_reasons
        answer = f'{heading}:\n' + "\n".join(_mover_line(item, reasons.get(item["symbol"], "No recent news evidence clearly explains the move.")) for item in movers)
    return {"intent": intent, "answer": answer, "updated_at": overview.get("updated_at"), "sources": sources}
