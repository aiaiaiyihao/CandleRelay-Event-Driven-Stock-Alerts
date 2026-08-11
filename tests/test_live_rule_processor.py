from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Base
from app.domain.events import MarketEvent
from app.models.Alert import Alert
from app.models.Rule import Rule, RuleVersion
from app.services.live_rule_processor import LiveRuleProcessor


def definition(cooldown_seconds=0):
    return {
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
        "trigger": "while_true",
        "cooldown_seconds": cooldown_seconds,
    }


def bar(day, close, volume):
    return MarketEvent.model_validate(
        {
            "symbol": "NVDA",
            "timeframe": "1d",
            "timestamp": f"2026-08-{day:02d}T20:00:00Z",
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
            "source": "live-test",
        }
    )


def setup_session(enabled=True, cooldown_seconds=0):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    rule = Rule(
        name="NVDA weakness",
        symbol="NVDA",
        timeframe="1d",
        enabled=enabled,
    )
    rule.versions.append(
        RuleVersion(version=1, dsl=definition(cooldown_seconds=cooldown_seconds))
    )
    session.add(rule)
    session.commit()
    return session


def test_processes_live_bars_and_persists_explainable_alert():
    session = setup_session()
    processor = LiveRuleProcessor()

    assert processor.process(bar(1, 100, 100), session) == []
    assert processor.process(bar(2, 100, 100), session) == []
    alerts = processor.process(bar(3, 80, 300), session)

    assert len(alerts) == 1
    stored = session.execute(select(Alert)).scalar_one()
    assert stored.rule_version == 1
    assert stored.explanation["conditions"][0]["left_value"] == "80"


def test_ignores_duplicate_or_out_of_order_events():
    session = setup_session()
    processor = LiveRuleProcessor()
    third = bar(3, 80, 300)

    processor.process(bar(1, 100, 100), session)
    processor.process(bar(2, 100, 100), session)
    processor.process(third, session)

    assert processor.process(third, session) == []
    assert processor.process(bar(2, 100, 100), session) == []
    assert len(session.execute(select(Alert)).scalars().all()) == 1


def test_does_not_evaluate_disabled_rules():
    session = setup_session(enabled=False)
    processor = LiveRuleProcessor()

    processor.process(bar(1, 100, 100), session)
    processor.process(bar(2, 100, 100), session)
    alerts = processor.process(bar(3, 80, 300), session)

    assert alerts == []


def test_database_cooldown_survives_processor_restart():
    session = setup_session(cooldown_seconds=172800)
    first_processor = LiveRuleProcessor()
    for item in [bar(1, 100, 100), bar(2, 100, 100), bar(3, 80, 300)]:
        first_processor.process(item, session)

    restarted_processor = LiveRuleProcessor()
    for item in [bar(1, 100, 100), bar(2, 100, 100)]:
        restarted_processor.process(item, session)
    alerts = restarted_processor.process(bar(4, 70, 300), session)

    assert alerts == []
    assert len(session.execute(select(Alert)).scalars().all()) == 1
