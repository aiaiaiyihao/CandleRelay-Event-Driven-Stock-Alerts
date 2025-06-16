from datetime import datetime

async def fetch_price_alpha(symbol: str):
    # TODO: Replace with real API call
    return {
        "symbol": symbol,
        "price": 234.56,
        "timestamp": datetime.utcnow().isoformat(),
        "provider": "alpha_vantage"
    }
