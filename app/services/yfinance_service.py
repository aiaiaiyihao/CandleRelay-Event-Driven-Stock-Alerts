import yfinance as yf
from datetime import datetime
import asyncio


CHART_RANGES = {"1mo", "3mo", "6mo", "1y"}
CHART_INTERVALS = {
    "1d": {"history_period": "2y", "points": {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}},
    "30m": {"history_period": "60d", "points": {"1mo": 286, "3mo": 780, "6mo": 780, "1y": 780}},
    "60m": {"history_period": "730d", "points": {"1mo": 154, "3mo": 462, "6mo": 924, "1y": 1764}},
    "1wk": {"history_period": "10y", "points": {"1mo": 4, "3mo": 13, "6mo": 26, "1y": 52}},
    "1mo": {"history_period": "max", "points": {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12}},
}
CHART_PRESETS = {
    "30m": {"history_period": "5d", "interval": "5m", "points": 6},
    "60m": {"history_period": "5d", "interval": "5m", "points": 12},
    "1d": {"history_period": "5d", "interval": "5m", "points": 78},
    "1wk": {"history_period": "60d", "interval": "30m", "points": 65},
    "1mo": {"history_period": "60d", "interval": "60m", "points": 154},
    "3mo": {"history_period": "2y", "interval": "1d", "points": 66},
    "1y": {"history_period": "5y", "interval": "1wk", "points": 52},
    "5y": {"history_period": "max", "interval": "1mo", "points": 60},
    "max": {"history_period": "max", "interval": "1mo", "points": None},
}
MARKET_INDEXES = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq Composite",
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
}
LARGE_CAP_UNIVERSE = (
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "BRK-B", "JPM",
    "LLY", "V", "WMT", "XOM", "MA", "COST", "ORCL", "NFLX", "HD", "PG",
    "JNJ", "ABBV", "BAC", "KO", "CRM", "AMD", "PEP", "TMO", "CSCO", "ACN",
    "MCD", "IBM", "GE", "CAT", "GS", "AXP", "UBER", "DIS", "QCOM", "INTC",
)

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


async def fetch_chart_yfinance(symbol: str, chart_range: str, chart_interval: str = "1d") -> dict:
    if chart_range not in CHART_RANGES:
        raise ValueError(f"Unsupported chart range: {chart_range}")
    if chart_interval not in CHART_INTERVALS:
        raise ValueError(f"Unsupported chart interval: {chart_interval}")

    interval_config = CHART_INTERVALS[chart_interval]

    def load_history():
        return yf.Ticker(symbol).history(
            period=interval_config["history_period"],
            interval=chart_interval,
            auto_adjust=False,
        )

    try:
        history = await asyncio.to_thread(load_history)
    except Exception as exc:
        raise ValueError(f"yfinance chart error for symbol '{symbol}': {exc}") from exc
    if history.empty:
        raise ValueError(f"No chart data found for symbol: {symbol}")

    points = build_chart_points(history)
    points = points[-interval_config["points"][chart_range]:]
    return {
        "symbol": symbol.upper(),
        "range": chart_range,
        "interval": chart_interval,
        "points": points,
    }


async def fetch_chart_preset_yfinance(symbol: str, period: str) -> dict:
    if period not in CHART_PRESETS:
        raise ValueError(f"Unsupported chart period: {period}")
    config = CHART_PRESETS[period]

    def load_history():
        return yf.Ticker(symbol).history(
            period=config["history_period"],
            interval=config["interval"],
            auto_adjust=False,
        )

    try:
        history = await asyncio.to_thread(load_history)
    except Exception as exc:
        raise ValueError(f"yfinance chart error for symbol '{symbol}': {exc}") from exc
    if history.empty:
        raise ValueError(f"No chart data found for symbol: {symbol}")

    points = build_chart_points(history)
    if config["points"] is not None:
        points = points[-config["points"]:]
    return {
        "symbol": symbol.upper(),
        "range": period,
        "interval": config["interval"],
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


async def fetch_market_overview() -> dict:
    symbols = [*MARKET_INDEXES, *LARGE_CAP_UNIVERSE]

    snapshots = await fetch_market_snapshots(symbols)
    indexes = [item for item in snapshots if item["symbol"] in MARKET_INDEXES]
    stocks = [item for item in snapshots if item["symbol"] not in MARKET_INDEXES]
    return {
        "indexes": indexes,
        "gainers": sorted(stocks, key=lambda item: item["change_percent"], reverse=True)[:10],
        "losers": sorted(stocks, key=lambda item: item["change_percent"])[:10],
    }


async def fetch_market_snapshots(symbols: list[str]) -> list[dict]:
    if not symbols:
        return []

    def load_market_data():
        return yf.download(
            tickers=symbols,
            period="5d",
            interval="1d",
            auto_adjust=False,
            group_by="ticker",
            progress=False,
            threads=True,
        )

    try:
        history = await asyncio.to_thread(load_market_data)
    except Exception as exc:
        raise ValueError(f"yfinance market overview error: {exc}") from exc

    snapshots = []
    for symbol in symbols:
        try:
            frame = history[symbol]
            closes = [float(value) for value in frame["Close"].dropna().tolist()]
            if len(closes) < 2:
                continue
            previous, price = closes[-2:]
            snapshots.append(
                {
                    "symbol": symbol,
                    "name": MARKET_INDEXES.get(symbol, symbol),
                    "price": price,
                    "change": price - previous,
                    "change_percent": ((price / previous) - 1) * 100,
                    "sparkline": closes,
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    return snapshots
