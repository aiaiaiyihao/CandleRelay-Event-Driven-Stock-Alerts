from datetime import datetime

async def fetch_price_iex(symbol: str):
    # TODO: Replace with real API call
    return {
        "symbol": symbol,
        "price": 123.45,
        "timestamp": datetime.utcnow().isoformat(),
        "provider": "iex"
    }
