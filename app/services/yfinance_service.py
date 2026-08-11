import yfinance as yf
from datetime import datetime
import asyncio


CHART_RANGES = {"1mo", "3mo", "6mo", "1y"}
CHART_POINT_LIMITS = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}
CHART_HISTORY_PERIOD = "2y"

#call remote api to fetch price
async def fetch_price_yfinance(symbol: str):
    try:
        data = yf.Ticker(symbol)
        price = data.info.get("regularMarketPrice")
    except Exception as e:
        raise ValueError(f"yfinance error for symbol '{symbol}': {e}")

    if price is None:
        raise ValueError(f"Stock not found for symbol: {symbol}")

    return {
        "symbol": symbol,
        "price": price,
        "timestamp": datetime.now(),
        "provider": "yfinance"
    }


async def search_stocks_yfinance(query: str, limit: int = 6) -> list[dict]:
    def load_results():
        return yf.Search(
            query,
            max_results=limit,
            news_count=0,
            lists_count=0,
            include_cb=False,
            recommended=0,
        ).quotes

    try:
        quotes = await asyncio.to_thread(load_results)
    except Exception as exc:
        raise ValueError(f"yfinance search error for '{query}': {exc}") from exc

    supported_types = {"EQUITY", "ETF"}
    return [
        {
            "symbol": quote["symbol"].upper(),
            "name": quote.get("longname") or quote.get("shortname") or quote["symbol"],
            "exchange": quote.get("exchDisp") or quote.get("exchange") or "Market",
            "type": quote.get("quoteType", "EQUITY"),
        }
        for quote in quotes
        if quote.get("quoteType") in supported_types
    ][:limit]


async def fetch_chart_yfinance(symbol: str, chart_range: str) -> dict:
    if chart_range not in CHART_RANGES:
        raise ValueError(f"Unsupported chart range: {chart_range}")

    def load_history():
        return yf.Ticker(symbol).history(
            period=CHART_HISTORY_PERIOD,
            interval="1d",
            auto_adjust=False,
        )

    try:
        history = await asyncio.to_thread(load_history)
    except Exception as exc:
        raise ValueError(f"yfinance chart error for symbol '{symbol}': {exc}") from exc
    if history.empty:
        raise ValueError(f"No chart data found for symbol: {symbol}")

    points = build_chart_points(history)
    points = points[-CHART_POINT_LIMITS[chart_range]:]
    return {
        "symbol": symbol.upper(),
        "range": chart_range,
        "interval": "1d",
        "points": points,
    }


def build_chart_points(history) -> list[dict]:
    closes = [float(value) for value in history["Close"].tolist()]
    averages = {
        period: moving_average(closes, period)
        for period in (20, 50, 200)
    }
    points = []
    for index, (timestamp, row) in enumerate(history.iterrows()):
        points.append(
            {
                "timestamp": timestamp.to_pydatetime(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": closes[index],
                "volume": int(row["Volume"]),
                "sma_20": averages[20][index],
                "sma_50": averages[50][index],
                "sma_200": averages[200][index],
            }
        )
    return points


def moving_average(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    running_total = 0.0
    for index, value in enumerate(values):
        running_total += value
        if index >= period:
            running_total -= values[index - period]
        result.append(running_total / period if index >= period - 1 else None)
    return result
