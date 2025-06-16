import json
import logging
from datetime import datetime
from fastapi import HTTPException
from redis.asyncio import Redis
from app.kafka.Producer import send_price_event
from app.core.config import SessionLocal, redis
from app.models.RawPrice import RawPrice
from app.services.yfinance_service import fetch_price_yfinance


async def fetch_price_by_provider(provider: str, symbol: str, poll: bool):
    """Fetch price from a provider, store to DB & cache, and optionally send to Kafka."""

    cache_key = f"{provider}:{symbol}:latest"

    # 1 Check Redis cache first
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        logging.info(
            f"Cache hit: {symbol} | price={data['price']} | ts={data['timestamp']} (provider={provider})"
        )
        return data

    # 2 Fetch from external provider
    try:
        if provider == "yfinance":
            data = await fetch_price_yfinance(symbol)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

        logging.info(
            f"Fetched price: {symbol} | price={data['price']} | ts={data['timestamp']} (provider={provider})"
        )

    except ValueError as v:
        logging.error(f"[ERROR] Failed fetch {symbol} from {provider}: {v}")
        raise HTTPException(status_code=404, detail=str(v))

    # 3 Persist to PostgreSQL
    with SessionLocal() as db:
        db_price = RawPrice(
            symbol=data["symbol"],
            price=data["price"],
            provider=data["provider"],
            timestamp=data["timestamp"],
        )
        db.add(db_price)
        db.commit()
        logging.info(
            f"Saved to DB: {symbol} | price={data['price']} | ts={data['timestamp']}"
        )

    # Convert datetime to ISO string for JSON safety
    if isinstance(data.get("timestamp"), datetime):
        data["timestamp"] = data["timestamp"].isoformat()

    # 4 Cache the result in Redis (10 s)
    await redis.set(cache_key, json.dumps(data), ex=100)
    logging.info(
        f"Cached result: {symbol} | price={data['price']} | ts={data['timestamp']} (TTL=10s)"
    )

    # 5 Optionally publish to Kafka for downstream processing
    if not poll:
        send_price_event(data)
        logging.info(
            f"Kafka event produced for {symbol} | price={data['price']} | ts={data['timestamp']}"
        )

    return data
