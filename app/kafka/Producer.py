from confluent_kafka import Producer
import json
import uuid
import logging
from app.core.config import producer_config
from app.domain.events import MarketEvent
from app.kafka.market_events import encode_market_event

# Initialize Kafka producer
# config includes retry settings
producer = Producer(producer_config)

def delivery_report(err, msg):
    if err is not None:
        logging.error(f"[KAFKA] Failed to deliver message: {err}")
    else:
        logging.info(f"[KAFKA] Message delivered to {msg.topic()} [partition {msg.partition()}] at offset {msg.offset()}")

def send_price_event(data: dict):
    """
    Produces a price event to the 'price-events' Kafka topic.
    """
    try:
        event = {
            "symbol": data["symbol"],
            "price": data["price"],
            "timestamp": data["timestamp"],
            "provider": data["provider"],
            "raw_response_id": str(uuid.uuid4())
        }

        producer.produce(
            topic="price-events",
            value=json.dumps(event),
            callback=delivery_report
        )

        producer.flush()  # Ensure delivery before continuing
        logging.info(f"[KAFKA] Produced event: {event}")

    #exception handling for kafka errors
    except Exception as e:
        logging.exception(f"[KAFKA] Exception while sending event: {e}")


def send_market_event(event: MarketEvent) -> None:
    """Publish a validated OHLCV event for SignalForge rule evaluation."""
    producer.produce(
        topic="market-events",
        key=f"{event.symbol}:{event.timeframe}",
        value=encode_market_event(event),
        callback=delivery_report,
    )
    producer.poll(0)
