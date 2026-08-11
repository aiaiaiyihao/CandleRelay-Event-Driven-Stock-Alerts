from datetime import datetime, timezone

import httpx

from app.core.config import ALPHA_VANTAGE_API_KEY


def build_alpha_vantage_movers(payload: dict) -> dict:
    if payload.get("Error Message") or payload.get("Information") or payload.get("Note"):
        message = payload.get("Error Message") or payload.get("Information") or payload.get("Note")
        raise ValueError(f"Alpha Vantage market movers error: {message}")

    def normalize(items: list[dict], descending: bool) -> list[dict]:
        snapshots = []
        for item in items:
            try:
                price = float(item["price"])
                change = float(item["change_amount"])
                change_percent = float(str(item["change_percentage"]).rstrip("%"))
            except (KeyError, TypeError, ValueError):
                continue
            previous = price - change
            snapshots.append({
                "symbol": item["ticker"].upper(),
                "name": item["ticker"].upper(),
                "price": price,
                "change": change,
                "change_percent": change_percent,
                "sparkline": [previous, price],
            })
        return sorted(snapshots, key=lambda snapshot: snapshot["change_percent"], reverse=descending)[:20]

    return {
        "gainers": normalize(payload.get("top_gainers", []), descending=True),
        "losers": normalize(payload.get("top_losers", []), descending=False),
        "market_state": "CLOSED",
        "updated_at": datetime.now(timezone.utc),
        "data_source": "alpha_vantage",
    }


async def fetch_market_movers_alpha_vantage() -> dict:
    if not ALPHA_VANTAGE_API_KEY:
        raise ValueError("Alpha Vantage fallback is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://www.alphavantage.co/query",
            params={"function": "TOP_GAINERS_LOSERS", "apikey": ALPHA_VANTAGE_API_KEY},
        )
        response.raise_for_status()
    movers = build_alpha_vantage_movers(response.json())
    if not movers["gainers"] or not movers["losers"]:
        raise ValueError("Alpha Vantage fallback returned no market movers")
    return movers
