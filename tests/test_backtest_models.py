from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Base
from app.models.BacktestRun import BacktestRun
from app.models.Rule import Rule, RuleVersion


def test_persists_reproducible_backtest_snapshot():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    dsl = {
        "dsl_version": "1.0",
        "symbol": "NVDA",
        "timeframe": "1d",
        "conditions": {"all": []},
    }
    rule = Rule(name="NVDA rule", symbol="NVDA", timeframe="1d")
    rule.versions.append(RuleVersion(version=1, dsl=dsl))
    session.add(rule)
    session.flush()

    run = BacktestRun(
        rule_id=rule.id,
        rule_version=1,
        dsl_snapshot=dsl,
        engine_version="1.0",
    )
    session.add(run)
    session.commit()

    stored = session.get(BacktestRun, run.id)
    assert stored.rule_version == 1
    assert stored.dsl_snapshot == dsl
    assert stored.status == "pending"
    assert stored.bars_processed == 0
    session.close()
