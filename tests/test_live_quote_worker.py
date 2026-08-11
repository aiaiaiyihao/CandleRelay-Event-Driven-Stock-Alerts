from datetime import datetime, timezone

from app.workers.live_quotes import BarAggregator, bucket_start, stream_timestamp


def test_stream_timestamp_accepts_yahoo_milliseconds():
    timestamp = stream_timestamp(1_786_466_700_000)
    assert timestamp == datetime.fromtimestamp(1_786_466_700, tz=timezone.utc)


def test_bucket_start_floors_intraday_intervals():
    timestamp = datetime(2026, 8, 11, 18, 7, 42, tzinfo=timezone.utc)
    assert bucket_start(timestamp, "5m") == datetime(2026, 8, 11, 18, 5, tzinfo=timezone.utc)


def test_aggregator_emits_completed_bar_at_next_bucket():
    aggregator = BarAggregator()
    first = datetime(2026, 8, 11, 18, 5, 10, tzinfo=timezone.utc)
    second = datetime(2026, 8, 11, 18, 5, 40, tzinfo=timezone.utc)
    next_bucket = datetime(2026, 8, 11, 18, 6, 1, tzinfo=timezone.utc)

    assert aggregator.update("NVDA", "1m", 180, first, 1000) is None
    assert aggregator.update("NVDA", "1m", 182, second, 1200) is None
    event = aggregator.update("NVDA", "1m", 181, next_bucket, 1300)

    assert event.open == 180
    assert event.high == 182
    assert event.close == 182
    assert event.volume == 200
