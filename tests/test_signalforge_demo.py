from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.compilers.base import ValidatedRuleCompiler
from app.compilers.heuristic import HeuristicCompilerProvider
from app.core.config import Base
from app.schemas.backtest import BacktestRangeCreate
from app.schemas.rule import RuleCreate
from app.services.backtest_service import execute_backtest_range
from app.services.market_bar_service import import_market_bars_csv
from app.services.ruleService import create_rule


def test_resume_demo_flow_from_natural_language_to_backtest_trigger():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    text = "当 NVDA 跌破 SMA20，并且成交量超过过去 20 天平均值的两倍时提醒我。"

    compilation = ValidatedRuleCompiler(HeuristicCompilerProvider()).compile(text)
    rule = create_rule(
        RuleCreate(name="NVDA high-volume breakdown", definition=compilation.definition),
        session,
    )
    fixture = Path(__file__).parents[1] / "examples" / "nvda_daily.csv"
    imported = import_market_bars_csv(fixture, "NVDA", "1d", "demo", session)
    result = execute_backtest_range(
        BacktestRangeCreate(
            rule_id=rule.id,
            start=datetime(2026, 7, 1, tzinfo=timezone.utc),
            end=datetime(2026, 7, 23, tzinfo=timezone.utc),
        ),
        session,
    )

    assert imported.imported == 22
    assert result.status == "completed"
    assert result.bars_processed == 22
    assert result.trigger_count == 1
    trigger = result.result_summary["triggers"][0]
    assert trigger["evaluated_at"].startswith("2026-07-22")
    assert all(condition["matched"] for condition in trigger["conditions"])
    session.close()
