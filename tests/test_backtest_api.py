from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.backtest_router import router
from app.core.config import Base, get_db
from app.models.BacktestRun import BacktestRun
from app.models.Rule import Rule, RuleVersion
from app.models.MarketBar import MarketBar
from datetime import datetime, timezone


def create_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        definition = {
            "dsl_version": "1.0",
            "symbol": "NVDA",
            "timeframe": "1d",
            "conditions": {
                "all": [
                    {
                        "left": {"type": "metric", "metric": "price"},
                        "operator": "<",
                        "right": {"type": "indicator", "indicator": "sma", "period": 2},
                    },
                    {
                        "left": {"type": "indicator", "indicator": "volume_ratio", "period": 2},
                        "operator": ">",
                        "right": {"type": "value", "value": 2},
                    },
                ]
            },
        }
        rule = Rule(name="NVDA weakness", symbol="NVDA", timeframe="1d")
        rule.versions.append(RuleVersion(version=1, dsl=definition))
        session.add(rule)
        session.flush()
        for day, close, volume in [(1, 100, 100), (2, 100, 100), (3, 80, 300)]:
            session.add(
                MarketBar(
                    symbol="NVDA",
                    timeframe="1d",
                    timestamp=datetime(2026, 8, day, 20, 0, tzinfo=timezone.utc),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=volume,
                    source="fixture",
                )
            )
        session.commit()
        rule_id = rule.id

    app = FastAPI()
    app.include_router(router)

    def test_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = test_db
    return TestClient(app), rule_id


def event(day, close, volume, symbol="NVDA"):
    return {
        "symbol": symbol,
        "timeframe": "1d",
        "timestamp": f"2026-08-{day:02d}T20:00:00Z",
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": volume,
        "source": "test",
    }


def test_runs_and_persists_explainable_backtest():
    client, rule_id = create_client()
    response = client.post(
        "/backtests",
        json={
            "rule_id": rule_id,
            "events": [
                event(1, 100, 100),
                event(2, 100, 100),
                event(3, 80, 300),
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["bars_processed"] == 3
    assert body["trigger_count"] == 1
    assert body["result_summary"]["triggers"][0]["conditions"][0]["left_value"] == "80"
    assert body["result_summary"]["triggers"][0]["entry_price"] == "80"
    assert body["result_summary"]["average_forward_returns"] == {
        "1": None,
        "5": None,
        "20": None,
    }

    fetched = client.get(f"/backtests/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_rejects_events_for_another_symbol():
    client, rule_id = create_client()

    response = client.post(
        "/backtests",
        json={"rule_id": rule_id, "events": [event(1, 100, 100, "AAPL")]},
    )

    assert response.status_code == 422


def test_returns_404_for_unknown_rule_and_run():
    client, _ = create_client()

    create_response = client.post(
        "/backtests",
        json={"rule_id": "missing", "events": [event(1, 100, 100)]},
    )

    assert create_response.status_code == 404
    assert client.get("/backtests/missing").status_code == 404


def test_runs_backtest_from_stored_market_bar_range():
    client, rule_id = create_client()

    response = client.post(
        "/backtests/range",
        json={
            "rule_id": rule_id,
            "start": "2026-08-01T00:00:00Z",
            "end": "2026-08-04T00:00:00Z",
        },
    )

    assert response.status_code == 201
    assert response.json()["bars_processed"] == 3
    assert response.json()["trigger_count"] == 1


def test_range_backtest_rejects_empty_or_invalid_range():
    client, rule_id = create_client()

    empty = client.post(
        "/backtests/range",
        json={
            "rule_id": rule_id,
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-02-01T00:00:00Z",
        },
    )
    reversed_range = client.post(
        "/backtests/range",
        json={
            "rule_id": rule_id,
            "start": "2026-08-04T00:00:00Z",
            "end": "2026-08-01T00:00:00Z",
        },
    )

    assert empty.status_code == 422
    assert reversed_range.status_code == 422
