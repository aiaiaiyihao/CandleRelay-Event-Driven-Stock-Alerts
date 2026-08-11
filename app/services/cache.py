import json

from app.core.config import redis


async def get_cached_json(key: str):
    try:
        value = await redis.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


async def set_cached_json(key: str, value, ttl_seconds: int) -> None:
    try:
        await redis.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        pass
