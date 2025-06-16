import json
import logging
from datetime import datetime

from confluent_kafka import Consumer
from sqlalchemy import desc

from app.core.config import SessionLocal
from app.models.MovingAverage import MovingAverage
from app.models.RawPrice import RawPrice

# Kafka consumer configuration
consumer_config = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "ma-consumer-group",
    "auto.offset.reset": "earliest",
}

consumer = Consumer(consumer_config)
consumer.subscribe(["price-events"])

# Helper: process one event
def process_event(event: dict) -> None:
    """Compute 5‑point moving average and upsert into DB."""
    symbol   = event["symbol"]
    provider = event["provider"]

    with SessionLocal() as session:
        try:
            recent = (
                session.query(RawPrice)
                .filter(RawPrice.symbol == symbol)
                .order_by(desc(RawPrice.timestamp))
                .limit(5)
                .all()
            )

            if not recent:
                logging.warning(f"⚠️ No data to calculate MA for {symbol}")
                return

            prices = [p.price for p in recent]
            ma     = sum(prices) / len(prices)

            existing = session.query(MovingAverage).filter(MovingAverage.symbol == symbol).first()
            if existing:
                existing.ma_5      = ma
                existing.timestamp = datetime.utcnow()
                logging.info(f"🔄 Updated MA for {symbol} → {ma:.2f}")
            else:
                session.add(
                    MovingAverage(
                        symbol=symbol,
                        ma_5=ma,
                        timestamp=datetime.utcnow(),
                        provider=provider,
                    )
                )
                logging.info(f"➕ Inserted MA for {symbol} → {ma:.2f}")

            session.commit()
        except Exception as exc:
            logging.exception(f"[DB] Error processing {symbol}: {exc}")

# Main polling loop
def run() -> None:
    logging.info("Starting MA Consumer… listening on 'price-events'")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logging.error(f"[Kafka] {msg.error()}")
            continue

        try:
            event = json.loads(msg.value())
            process_event(event)
        except Exception as exc:
            logging.exception(f"Failed to process message: {exc}")

# Entry point
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
