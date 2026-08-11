import os

from redis.asyncio import Redis
from sqlalchemy.engine.create import create_engine
from sqlalchemy.orm.decl_api import declarative_base
from sqlalchemy.orm.session import sessionmaker


APP_NAME = os.getenv("APP_NAME", "CandleRelay")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() in {"1", "true", "yes"}
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

producer_config = {
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"),
    "retries": 5,
    "retry.backoff.ms": 100,
    "message.timeout.ms": 10000,
    "enable.idempotence": True,
}

consumer_config = {
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"),
    "group.id": os.getenv("KAFKA_SIGNAL_GROUP", "signalforge-live-rules"),
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis = Redis.from_url(REDIS_URL, decode_responses=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@localhost:5432/marketdb",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
