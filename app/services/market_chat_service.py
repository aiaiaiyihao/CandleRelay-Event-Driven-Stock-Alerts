import asyncio
import re

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


def _mover_line(item: dict) -> str:
    sign = "+" if item["change_percent"] >= 0 else ""
    return f'{item["symbol"]} {sign}{item["change_percent"]:.2f}% (${item["price"]:.2f})'


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
    answer = f'{heading}: ' + "; ".join(_mover_line(item) for item in movers) + "."
    sources = []
    if any(term in lowered for term in ("why", "reason", "news", "because")) and movers:
        news_groups = await asyncio.gather(*(fetch_stock_news_yfinance(item["symbol"]) for item in movers))
        contexts = []
        for item, news in zip(movers, news_groups):
            if not news:
                continue
            story = news[0]
            contexts.append(f'{item["symbol"]}: {story["title"]}')
            sources.append({"symbol": item["symbol"], "title": story["title"], "url": story["url"]})
        if contexts:
            answer += " Recent news context: " + "; ".join(contexts) + ". Headlines provide context, not proof of causation."
        else:
            answer += " No recent company headlines were available to explain the moves; price action alone does not establish a cause."
    return {"intent": intent, "answer": answer, "updated_at": overview.get("updated_at"), "sources": sources}
