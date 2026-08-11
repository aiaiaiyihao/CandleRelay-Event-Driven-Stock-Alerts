import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.alert_router import router as alerts_router
from app.api.backtest_router import router as backtests_router
from app.api.health_router import router as health_router
from app.api.priceRouter import router as prices_router
from app.api.ruleRouter import router as rules_router
from app.api.watchlist_router import router as watchlist_router
from app.api.auth_router import router as auth_router
from app.core.config import APP_DEBUG, APP_NAME, APP_VERSION, CORS_ORIGINS, redis
from app.kafka.Producer import producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Application starting…")
    yield
    logging.info("Shutting down application…")

    try:
        await redis.aclose()
        await redis.connection_pool.disconnect()
        logging.info("Redis connection closed.")
    except Exception as exc:
        logging.error("Redis shutdown error: %s", exc)

    try:
        producer.flush()
        logging.info("Kafka producer flushed.")
    except Exception as exc:
        logging.error("Kafka flush error: %s", exc)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    debug=APP_DEBUG,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app.include_router(prices_router)
app.include_router(rules_router)
app.include_router(backtests_router)
app.include_router(alerts_router)
app.include_router(health_router)
app.include_router(watchlist_router)
app.include_router(auth_router)
