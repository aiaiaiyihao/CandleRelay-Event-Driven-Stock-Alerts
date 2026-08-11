import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
import asyncio
import time


CHART_RANGES = {"1mo", "3mo", "6mo", "1y"}
CHART_INTERVALS = {
    "1d": {"history_period": "2y", "points": {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252}},
    "30m": {"history_period": "60d", "points": {"1mo": 286, "3mo": 780, "6mo": 780, "1y": 780}},
    "60m": {"history_period": "730d", "points": {"1mo": 154, "3mo": 462, "6mo": 924, "1y": 1764}},
    "1wk": {"history_period": "10y", "points": {"1mo": 4, "3mo": 13, "6mo": 26, "1y": 52}},
    "1mo": {"history_period": "max", "points": {"1mo": 1, "3mo": 3, "6mo": 6, "1y": 12}},
}
CHART_PRESETS = {
    "30m": {"history_period": "5d", "source_interval": "1m", "interval": "1m", "points": 30},
    "60m": {"history_period": "5d", "source_interval": "1m", "interval": "1m", "points": 60},
    "1d": {"history_period": "5d", "source_interval": "1m", "interval": "1m", "points": 390},
    "1wk": {"history_period": "60d", "source_interval": "5m", "interval": "10m", "aggregate": "10min", "points": 195},
    "1mo": {"history_period": "730d", "source_interval": "60m", "interval": "4h", "aggregate": "4h", "points": 44},
    "3mo": {"history_period": "2y", "source_interval": "1d", "interval": "1d", "points": 66},
    "1y": {"history_period": "5y", "source_interval": "1d", "interval": "2d", "aggregate_rows": 2, "points": 126},
    "5y": {"history_period": "max", "source_interval": "1wk", "interval": "1wk", "points": 260},
    "max": {"history_period": "max", "source_interval": "1mo", "interval": "1mo", "points": None},
}
MARKET_INDEXES = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq Composite",
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
}
SECTOR_ETFS = {
    "technology": ("Technology", "XLK"),
    "financial-services": ("Financial Services", "XLF"),
    "healthcare": ("Healthcare", "XLV"),
    "consumer-cyclical": ("Consumer Cyclical", "XLY"),
    "communication-services": ("Communication Services", "XLC"),
    "industrials": ("Industrials", "XLI"),
    "consumer-defensive": ("Consumer Defensive", "XLP"),
    "energy": ("Energy", "XLE"),
    "basic-materials": ("Basic Materials", "XLB"),
    "real-estate": ("Real Estate", "XLRE"),
    "utilities": ("Utilities", "XLU"),
}
MARKET_OVERVIEW_CACHE_SECONDS = 60
_market_overview_cache: tuple[float, dict] | None = None

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


async def fetch_stock_detail_yfinance(symbol: str) -> dict:
    def load_detail():
        return yf.Ticker(symbol).info

    try:
        info = await asyncio.to_thread(load_detail)
    except Exception as exc:
        raise ValueError(f"yfinance detail error for symbol '{symbol}': {exc}") from exc
    price = info.get("regularMarketPrice") or info.get("currentPrice")
    if price is None:
        raise ValueError(f"Stock not found for symbol: {symbol}")
    previous = info.get("regularMarketPreviousClose") or info.get("previousClose")
    change = float(price) - float(previous) if previous else None
    timestamp = info.get("regularMarketTime")
    return {
        "symbol": symbol.upper(),
        "name": info.get("longName") or info.get("shortName") or symbol.upper(),
        "exchange": info.get("fullExchangeName") or info.get("exchange"),
        "currency": info.get("currency"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "price": float(price),
        "previous_close": float(previous) if previous else None,
        "change": change,
        "change_percent": (change / float(previous)) * 100 if previous else None,
        "open": info.get("regularMarketOpen") or info.get("open"),
        "day_high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
        "day_low": info.get("regularMarketDayLow") or info.get("dayLow"),
        "volume": info.get("regularMarketVolume") or info.get("volume"),
        "market_cap": info.get("marketCap"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "market_state": info.get("marketState"),
        "updated_at": datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else datetime.now(timezone.utc),
    }


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
            interval=config["source_interval"],
            auto_adjust=False,
        )

    try:
        history = await asyncio.to_thread(load_history)
    except Exception as exc:
        raise ValueError(f"yfinance chart error for symbol '{symbol}': {exc}") from exc
    if history.empty:
        raise ValueError(f"No chart data found for symbol: {symbol}")

    history = aggregate_chart_history(
        history,
        frequency=config.get("aggregate"),
        rows=config.get("aggregate_rows"),
    )
    points = build_chart_points(history)
    if config["points"] is not None:
        points = points[-config["points"]:]
    return {
        "symbol": symbol.upper(),
        "range": period,
        "interval": config["interval"],
        "points": points,
    }


def aggregate_chart_history(history, frequency: str | None = None, rows: int | None = None):
    aggregations = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }
    if frequency:
        offset = "9h30min" if frequency in {"10min", "4h"} else None
        return (
            history.resample(frequency, origin="start_day", offset=offset)
            .agg(aggregations)
            .dropna(subset=["Close"])
        )
    if rows:
        records = []
        timestamps = []
        for start in range(0, len(history), rows):
            chunk = history.iloc[start:start + rows]
            if chunk.empty:
                continue
            records.append(
                {
                    "Open": chunk["Open"].iloc[0],
                    "High": chunk["High"].max(),
                    "Low": chunk["Low"].min(),
                    "Close": chunk["Close"].iloc[-1],
                    "Volume": chunk["Volume"].sum(),
                }
            )
            timestamps.append(chunk.index[-1])
        return pd.DataFrame(records, index=pd.DatetimeIndex(timestamps))
    return history


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


async def fetch_market_overview(force_refresh: bool = False) -> dict:
    global _market_overview_cache
    now = time.monotonic()
    if not force_refresh and _market_overview_cache and now - _market_overview_cache[0] < MARKET_OVERVIEW_CACHE_SECONDS:
        return _market_overview_cache[1]

    indexes, movers, sectors = await asyncio.gather(
        fetch_market_snapshots(list(MARKET_INDEXES)),
        fetch_market_movers(),
        fetch_sector_performance(),
    )
    overview = {
        "indexes": indexes,
        "gainers": movers["gainers"],
        "losers": movers["losers"],
        "sectors": sectors,
        "scope": "Active US-listed stocks (Nasdaq, NYSE, NYSE American; price $1+, volume 100K+)",
        "market_state": movers["market_state"],
        "updated_at": movers["updated_at"],
    }
    _market_overview_cache = (now, overview)
    return overview


async def fetch_market_movers() -> dict:
    def load_screens():
        query = active_us_equity_query()
        return (
            yf.screen(query, size=50, sortField="percentchange", sortAsc=False),
            yf.screen(query, size=50, sortField="percentchange", sortAsc=True),
        )

    try:
        gainers_screen, losers_screen = await asyncio.to_thread(load_screens)
    except Exception as exc:
        raise ValueError(f"yfinance market screener error: {exc}") from exc

    gainers = build_screener_snapshots(gainers_screen.get("quotes", []), descending=True)
    losers = build_screener_snapshots(losers_screen.get("quotes", []), descending=False)
    quotes = [*gainers_screen.get("quotes", []), *losers_screen.get("quotes", [])]
    timestamps = [quote.get("regularMarketTime") for quote in quotes if quote.get("regularMarketTime")]
    return {
        "gainers": gainers[:50],
        "losers": losers[:50],
        "market_state": "OPEN" if any(quote.get("marketState") == "REGULAR" for quote in quotes) else "CLOSED",
        "updated_at": datetime.fromtimestamp(max(timestamps), tz=timezone.utc) if timestamps else datetime.now(timezone.utc),
    }


def active_us_equity_query(*extra_conditions):
    return yf.EquityQuery(
        "and",
        [
            yf.EquityQuery("eq", ["region", "us"]),
            yf.EquityQuery("is-in", ["exchange", "NMS", "NGM", "NCM", "NYQ", "ASE"]),
            yf.EquityQuery("gte", ["intradayprice", 1]),
            yf.EquityQuery("gte", ["dayvolume", 100_000]),
            *extra_conditions,
        ],
    )


async def fetch_sector_performance() -> list[dict]:
    by_symbol = {symbol: (slug, name) for slug, (name, symbol) in SECTOR_ETFS.items()}
    snapshots = await fetch_market_snapshots(list(by_symbol))
    sectors = [
        {**snapshot, "slug": by_symbol[snapshot["symbol"]][0], "name": by_symbol[snapshot["symbol"]][1]}
        for snapshot in snapshots
        if snapshot["symbol"] in by_symbol
    ]
    return sorted(sectors, key=lambda item: item["change_percent"], reverse=True)


async def fetch_sector_stocks(sector_slug: str, page: int, page_size: int) -> dict:
    sector_name, _ = SECTOR_ETFS[sector_slug]
    query = active_us_equity_query(yf.EquityQuery("eq", ["sector", sector_name]))

    def load_screen():
        return yf.screen(
            query,
            offset=(page - 1) * page_size,
            size=page_size,
            sortField="percentchange",
            sortAsc=False,
        )

    try:
        screen = await asyncio.to_thread(load_screen)
    except Exception as exc:
        raise ValueError(f"yfinance sector screener error: {exc}") from exc
    quotes = screen.get("quotes", [])
    timestamps = [quote.get("regularMarketTime") for quote in quotes if quote.get("regularMarketTime")]
    return {
        "sector": sector_name,
        "slug": sector_slug,
        "page": page,
        "page_size": page_size,
        "total": screen.get("total", 0),
        "stocks": build_screener_snapshots(quotes, descending=True),
        "updated_at": datetime.fromtimestamp(max(timestamps), tz=timezone.utc) if timestamps else None,
    }


def build_screener_snapshots(quotes: list[dict], descending: bool) -> list[dict]:
    snapshots = []
    for quote in quotes:
        price = quote.get("regularMarketPrice")
        previous = quote.get("regularMarketPreviousClose")
        symbol = quote.get("symbol")
        if not symbol or price is None or not previous:
            continue
        change = float(price) - float(previous)
        snapshots.append(
            {
                "symbol": symbol,
                "name": quote.get("longName") or quote.get("shortName") or symbol,
                "price": float(price),
                "change": change,
                "change_percent": (change / float(previous)) * 100,
                "sparkline": [float(previous), float(price)],
            }
        )
    return sorted(snapshots, key=lambda item: item["change_percent"], reverse=descending)


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
