from fastapi import FastAPI
from app.api.priceRouter import router as prices_router
from app.api.ruleRouter import router as rules_router
import logging
from app.core.config import redis
from app.kafka.Producer import producer
from contextlib import asynccontextmanager

#graceful shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application starting…")
    # (Put any startup init here, e.g. warm-up caches)

    yield  # ←—— FastAPI serves requests here ———————————

    # ── Shutdown section (after `yield`) ───────────────
    logging.info("Shutting down application…")

    # Close Redis
    try:
        await redis.close()
        await redis.connection_pool.disconnect()
        logging.info("Redis connection closed.")
    except Exception as e:
        logging.error(f"Redis shutdown error: {e}")

    # Flush & close Kafka producer
    try:
        producer.flush()
        logging.info("Kafka producer flushed.")
    except Exception as e:
        logging.error(f"Kafka flush error: {e}")
app = FastAPI(debug=True, lifespan=lifespan)

logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more detail
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# @app.get("/")
# def check():
#     return {"message": "Hello World"}

app.include_router(prices_router)
app.include_router(rules_router)
