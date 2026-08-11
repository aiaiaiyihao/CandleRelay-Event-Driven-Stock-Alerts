import os

from redis.asyncio import Redis
from sqlalchemy.engine.create import create_engine
from sqlalchemy.orm.decl_api import declarative_base
from sqlalchemy.orm.session import sessionmaker

# Configure kafka connection
producer_config = {
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"),
    "retries": 5,
    "retry.backoff.ms": 100,         # optional: wait 100ms between retries
    "message.timeout.ms": 10000,     # give up after 10s if not delivered
    "enable.idempotence": True       # avoid duplicates (safe retries)
}

#Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis = Redis.from_url(REDIS_URL, decode_responses=True)

#PostgreSQL DataBase
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@localhost:5432/marketdb",
)

# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


# FastAPI dependency that provides a DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
