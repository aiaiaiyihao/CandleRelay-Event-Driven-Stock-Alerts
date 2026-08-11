import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import Base
from app.models.Rule import Rule, RuleVersion


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        yield db
    finally:
        db.close()


def rule_dsl():
    return {
        "dsl_version": "1.0",
        "symbol": "NVDA",
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
    }


def test_persists_rule_with_immutable_version_snapshot(session):
    rule = Rule(name="NVDA weakness", symbol="NVDA", timeframe="1d")
    rule.versions.append(RuleVersion(version=1, dsl=rule_dsl()))
    session.add(rule)
    session.commit()

    stored = session.get(Rule, rule.id)
    assert stored.enabled is True
    assert stored.current_version == 1
    assert stored.versions[0].dsl["symbol"] == "NVDA"


def test_rejects_duplicate_version_number_for_a_rule(session):
    rule = Rule(name="NVDA weakness", symbol="NVDA", timeframe="1d")
    rule.versions.extend(
        [
            RuleVersion(version=1, dsl=rule_dsl()),
            RuleVersion(version=1, dsl=rule_dsl()),
        ]
    )
    session.add(rule)

    with pytest.raises(IntegrityError):
        session.commit()
