from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.alert_router import router
from app.core.config import Base, get_db
from app.models.Alert import Alert
from app.models.Rule import Rule, RuleVersion


def create_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as session:
        rule = Rule(name="NVDA", symbol="NVDA", timeframe="1d")
        rule.versions.append(RuleVersion(version=1, dsl={"dsl_version": "1.0"}))
        session.add(rule)
        session.flush()
        alert = Alert(
            rule_id=rule.id,
            rule_version=1,
            symbol="NVDA",
            timeframe="1d",
            market_timestamp=datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc),
            dedupe_key="one",
            explanation={"conditions": []},
        )
        session.add(alert)
        session.commit()
        alert_id = alert.id
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
    return TestClient(app), alert_id, rule_id


def test_lists_filters_and_acknowledges_alerts():
    client, alert_id, rule_id = create_client()

    alerts = client.get(f"/alerts?rule_id={rule_id}&acknowledged=false")
    assert alerts.status_code == 200
    assert [alert["id"] for alert in alerts.json()] == [alert_id]

    acknowledged = client.post(f"/alerts/{alert_id}/acknowledge")
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged"] is True
    assert acknowledged.json()["acknowledged_at"] is not None

    assert client.get("/alerts?acknowledged=false").json() == []
    assert len(client.get("/alerts?acknowledged=true").json()) == 1


def test_acknowledge_is_idempotent_and_unknown_alert_is_404():
    client, alert_id, _ = create_client()

    first = client.post(f"/alerts/{alert_id}/acknowledge").json()
    second = client.post(f"/alerts/{alert_id}/acknowledge").json()

    assert second["acknowledged_at"] == first["acknowledged_at"]
    assert client.post("/alerts/missing/acknowledge").status_code == 404
