import logging

from confluent_kafka import Consumer

from app.core.config import SessionLocal, consumer_config
from app.kafka.market_events import decode_market_event
from app.services.live_rule_processor import LiveRuleProcessor


class SignalConsumerWorker:
    def __init__(self, consumer, session_factory, processor=None):
        self.consumer = consumer
        self.session_factory = session_factory
        self.processor = processor or LiveRuleProcessor()

    def process_payload(self, payload: bytes) -> int:
        event = decode_market_event(payload)
        with self.session_factory() as session:
            alerts = self.processor.process(event, session)
        return len(alerts)

    def run_once(self, timeout: float = 1.0) -> bool:
        message = self.consumer.poll(timeout)
        if message is None:
            return False
        if message.error():
            raise RuntimeError(str(message.error()))

        alert_count = self.process_payload(message.value())
        self.consumer.commit(message=message, asynchronous=False)
        logging.info(
            "Processed market event from partition=%s offset=%s alerts=%s",
            message.partition(),
            message.offset(),
            alert_count,
        )
        return True

    def run(self) -> None:
        try:
            while True:
                self.run_once()
        finally:
            self.consumer.close()


def build_worker() -> SignalConsumerWorker:
    consumer = Consumer(consumer_config)
    consumer.subscribe(["market-events"])
    return SignalConsumerWorker(consumer, SessionLocal)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    build_worker().run()

