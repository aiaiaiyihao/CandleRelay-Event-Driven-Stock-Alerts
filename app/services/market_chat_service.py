import asyncio
import re

from app.services.gemini_service import analyze_movers_with_gemini, summarize_stock_news_with_gemini
from app.services.yfinance_service import (
    fetch_market_overview,
    fetch_stock_detail_yfinance,
    fetch_stock_news_yfinance,
)


IGNORED_TOKENS = {
    "WHAT", "WHICH", "WHY", "HOW", "IS", "ARE", "SHOW", "TELL", "ME", "ABOUT", "THE", "A", "AN", "FOR", "OF", "ON",
    "IT", "ITS", "THIS", "THAT", "WITH", "AND", "TO", "IN", "STOCK", "STOCKS", "PRICE", "TODAY", "STRONG", "STRONGEST",
    "WEAK", "WEAKEST",
}
RANKED_MOVER_TERMS = ("strongest", "weakest", "gainer", "gainers", "loser", "losers", "market leaders", "market laggards")
MARKET_STATUS_TERMS = ("how is the market", "how's the market", "market overview", "market today", "market doing")


def _symbol(question: str) -> str | None:
    for token in re.findall(r"\b[A-Z]{1,5}(?:\.[A-Z])?\b", question):
        if token not in IGNORED_TOKENS:
            return token
    return None


def _mover_line(item: dict, reason: str | None = None) -> str:
    direction = "rose" if item["change_percent"] >= 0 else "fell"
    line = f'{item["symbol"]} {direction} {abs(item["change_percent"]):.2f}% to ${item["price"]:.2f}'
    return f"{line} — {reason}" if reason else line


def _has_public_url(stories: list[dict]) -> bool:
    return any(isinstance(story.get("url"), str) and story["url"].startswith(("https://", "http://")) for story in stories)


async def _news_with_urls(symbol: str, initial_stories: list[dict] | None = None) -> list[dict]:
    stories = initial_stories if initial_stories is not None else await fetch_stock_news_yfinance(symbol)
    if not _has_public_url(stories):
        stories = await fetch_stock_news_yfinance(symbol, force_refresh=True)
    return stories[:3]


async def _answer_single_stock_reason(symbol: str, question: str) -> dict:
    detail = await fetch_stock_detail_yfinance(symbol)
    mover = {
        "symbol": symbol,
        "price": detail["price"],
        "change_percent": detail.get("change_percent") or 0,
    }
    news = await _news_with_urls(symbol, detail.get("news", []))
    fallback = (
        f'Recent coverage reports “{news[0]["title"]}”; this provides context but does not prove causation.'
        if news else "No recent news evidence clearly explains the move."
    )
    reasons = await analyze_movers_with_gemini(question, [mover], [news]) or {symbol: fallback}
    return {
        "intent": "strong" if mover["change_percent"] >= 0 else "weak",
        "answer": _mover_line(mover, reasons[symbol]),
        "updated_at": detail.get("updated_at"),
        "sources": [{"symbol": symbol, "title": story["title"], "url": story["url"]} for story in news if _has_public_url([story])],
    }


def _news_fallback(stories: list[dict]) -> str:
    if not stories:
        return "No recent published news was found for this ticker."
    lines = []
    for story in stories:
        title = story.get("title", "Untitled coverage")
        summary = story.get("summary")
        lines.append(f"• {title}{': ' + summary if summary else ''}")
    return "\n".join(lines)


async def _answer_single_stock_news(symbol: str) -> dict:
    detail = await fetch_stock_detail_yfinance(symbol)
    news = await _news_with_urls(symbol, detail.get("news", []))
    summary = await summarize_stock_news_with_gemini(symbol, news) or _news_fallback(news)
    return {
        "intent": "news",
        "answer": f'Recent news for {detail["name"]} ({symbol}):\n{summary}',
        "updated_at": detail.get("updated_at"),
        "sources": [{"symbol": symbol, "title": story["title"], "url": story["url"]} for story in news if _has_public_url([story])],
    }


async def _answer_single_stock_overview(symbol: str) -> dict:
    detail = await fetch_stock_detail_yfinance(symbol)
    change = detail.get("change_percent")
    direction = "up" if (change or 0) >= 0 else "down"
    change_text = f", {direction} {abs(change):.2f}% today" if change is not None else ""
    news = await _news_with_urls(symbol, detail.get("news", []))
    summary = await summarize_stock_news_with_gemini(symbol, news) or _news_fallback(news)
    return {
        "intent": "stock",
        "answer": f'{detail["name"]} ({symbol}) is ${detail["price"]:.2f}{change_text}.\n\nRecent news:\n{summary}',
        "updated_at": detail.get("updated_at"),
        "sources": [{"symbol": symbol, "title": story["title"], "url": story["url"]} for story in news if _has_public_url([story])],
    }


async def answer_market_question(question: str, context_symbol: str | None = None) -> dict:
    normalized = question.strip()
    lowered = normalized.lower()
    explicit_symbol = _symbol(normalized)
    is_ranked_mover_question = any(term in lowered for term in RANKED_MOVER_TERMS)
    symbol = explicit_symbol or (context_symbol.upper() if context_symbol and not is_ranked_mover_question else None)
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

    news_question = any(term in lowered for term in ("news", "headline", "headlines", "latest", "updates"))
    causal_question = any(term in lowered for term in ("why", "reason", "rising", "falling", "up", "down", "because"))
    if symbol and news_question and not causal_question:
        return await _answer_single_stock_news(symbol)

    if symbol and causal_question:
        return await _answer_single_stock_reason(symbol, normalized)

    if symbol:
        return await _answer_single_stock_overview(symbol)

    if any(term in lowered for term in MARKET_STATUS_TERMS):
        overview = await fetch_market_overview()
        gainers = overview["gainers"][:10]
        losers = overview["losers"][:10]
        answer = "Today's Top 10 Gainers:\n" + "\n".join(_mover_line(item) for item in gainers)
        answer += "\n\nToday's Top 10 Losers:\n" + "\n".join(_mover_line(item) for item in losers)
        return {"intent": "market", "answer": answer, "updated_at": overview.get("updated_at"), "sources": []}

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
        news_groups = await asyncio.gather(*(_news_with_urls(item["symbol"]) for item in movers))
        fallback_reasons = {}
        for item, news in zip(movers, news_groups):
            if not news:
                fallback_reasons[item["symbol"]] = "No recent news evidence clearly explains the move."
                continue
            story = news[0]
            fallback_reasons[item["symbol"]] = f'Recent coverage reports “{story["title"]}”; this provides context but does not prove causation.'
            sources.extend(
                {"symbol": item["symbol"], "title": source["title"], "url": source["url"]}
                for source in news
                if _has_public_url([source])
            )
        reasons = await analyze_movers_with_gemini(normalized, movers, news_groups) or fallback_reasons
        answer = f'{heading}:\n' + "\n".join(_mover_line(item, reasons.get(item["symbol"], "No recent news evidence clearly explains the move.")) for item in movers)
    return {"intent": intent, "answer": answer, "updated_at": overview.get("updated_at"), "sources": sources}
