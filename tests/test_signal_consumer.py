from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.events import MarketEvent
from app.kafka.SignalConsumer import SignalConsumerWorker
from app.kafka.market_events import encode_market_event


class FakeMessage:
    def __init__(self, payload):
        self._payload = payload

    def value(self):
        return self._payload

    def error(self):
        return None

    def partition(self):
        return 0

    def offset(self):
        return 42


class FakeConsumer:
    def __init__(self, message):
        self.message = message
        self.committed = []

    def poll(self, timeout):
        message, self.message = self.message, None
        return message

    def commit(self, message, asynchronous):
        self.committed.append((message, asynchronous))


class FakeProcessor:
    def __init__(self, should_fail=False):
        self.events = []
        self.should_fail = should_fail

    def process(self, event, session):
        self.events.append(event)
        if self.should_fail:
            raise RuntimeError("database failed")
        return [object()]


def payload():
    event = MarketEvent.model_validate(
        {
            "symbol": "NVDA",
            "timeframe": "1d",
            "timestamp": "2026-08-10T20:00:00Z",
            "open": 100,
            "high": 100,
            "low": 100,
            "close": 100,
            "volume": 100,
            "source": "test",
        }
    )
    return encode_market_event(event)


def worker(processor):
    consumer = FakeConsumer(FakeMessage(payload()))
    factory = sessionmaker(bind=create_engine("sqlite:///:memory:"))
    return SignalConsumerWorker(consumer, factory, processor), consumer


def test_commits_offset_only_after_successful_processing():
    processor = FakeProcessor()
    signal_worker, consumer = worker(processor)

    assert signal_worker.run_once() is True
    assert processor.events[0].symbol == "NVDA"
    assert len(consumer.committed) == 1
    assert consumer.committed[0][1] is False


def test_does_not_commit_offset_when_processing_fails():
    signal_worker, consumer = worker(FakeProcessor(should_fail=True))

    try:
        signal_worker.run_once()
    except RuntimeError as exc:
        assert str(exc) == "database failed"
    else:
        raise AssertionError("expected processing failure")

    assert consumer.committed == []
