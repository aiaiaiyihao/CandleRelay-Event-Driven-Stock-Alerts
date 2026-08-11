from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.ruleRouter import router
from app.core.config import Base, get_db
from app.models.Rule import Rule, RuleVersion


def create_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def test_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = test_db
    return TestClient(app)


def rule_payload():
    return {
        "name": "NVDA high-volume weakness",
        "definition": {
            "symbol": "nvda",
            "timeframe": "1d",
            "conditions": {
                "all": [
                    {
                        "left": {"type": "metric", "metric": "price"},
                        "operator": "<",
                        "right": {"type": "indicator", "indicator": "sma", "period": 20},
                    }
                ]
            },
            "cooldown_seconds": 3600,
        },
    }


def test_create_and_query_rule():
    client = create_client()

    created = client.post("/rules", json=rule_payload())
    assert created.status_code == 201
    body = created.json()
    assert body["definition"]["symbol"] == "NVDA"
    assert body["version"] == 1

    listed = client.get("/rules")
    assert listed.status_code == 200
    assert [rule["id"] for rule in listed.json()] == [body["id"]]

    fetched = client.get(f"/rules/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_rejects_invalid_rule_before_persisting():
    client = create_client()
    payload = rule_payload()
    payload["definition"]["conditions"] = {"all": []}

    response = client.post("/rules", json=payload)

    assert response.status_code == 422
    assert client.get("/rules").json() == []


def test_returns_404_for_unknown_rule():
    client = create_client()

    response = client.get("/rules/missing")

    assert response.status_code == 404
