import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import Base
from app.models.Alert import Alert
from app.models.Rule import Rule, RuleVersion


def setup_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    rule = Rule(name="NVDA rule", symbol="NVDA", timeframe="1d")
    rule.versions.append(RuleVersion(version=1, dsl={"dsl_version": "1.0"}))
    session.add(rule)
    session.commit()
    return session, rule.id


def alert(rule_id, dedupe_key):
    return Alert(
        rule_id=rule_id,
        rule_version=1,
        symbol="NVDA",
        timeframe="1d",
        market_timestamp=datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc),
        dedupe_key=dedupe_key,
        explanation={"conditions": []},
    )


def test_persists_explainable_alert():
    session, rule_id = setup_session()
    record = alert(rule_id, "rule-1:2026-08-10T20:00:00Z")
    session.add(record)
    session.commit()

    stored = session.get(Alert, record.id)
    assert stored.rule_version == 1
    assert stored.explanation == {"conditions": []}
    assert stored.acknowledged is False
    session.close()


def test_rejects_duplicate_delivery_key():
    session, rule_id = setup_session()
    session.add_all([alert(rule_id, "same-event"), alert(rule_id, "same-event")])

    with pytest.raises(IntegrityError):
        session.commit()
    session.close()
