from decimal import Decimal

from app.backtesting.engine import BacktestEngine
from app.domain.events import MarketEvent
from app.domain.rules import RuleDefinition
from app.indicators.engine import IndicatorEngine
from app.rules.evaluator import RuleEvaluator


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
            "source": "fixture",
        }
    )


def rule():
    return RuleDefinition.model_validate(
        {
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
    )


def test_replay_sorts_events_and_reports_triggers():
    events = [bar(3, 80, 300), bar(1, 100, 100), bar(2, 100, 100)]

    result = BacktestEngine().run("rule-1", rule(), events)

    assert result.bars_processed == 3
    assert len(result.triggers) == 1
    assert result.triggers[0].evaluated_at == events[0].timestamp


def test_replay_matches_incremental_live_execution_exactly():
    events = [bar(1, 100, 100), bar(2, 100, 100), bar(3, 80, 300)]
    definition = rule()

    replay = BacktestEngine().run("rule-1", definition, events)

    indicators = IndicatorEngine()
    evaluator = RuleEvaluator()
    live = tuple(
        evaluator.evaluate(
            "rule-1",
            definition,
            event,
            indicators.update(event, [2]),
        )
        for event in events
    )

    assert replay.evaluations == live


def test_calculates_forward_returns_and_aggregates_trigger_outcomes():
    events = [
        bar(1, 100, 100),
        bar(2, 100, 100),
        bar(3, 80, 300),
        bar(4, 88, 100),
        bar(5, 96, 100),
    ]

    result = BacktestEngine().run(
        "rule-1",
        rule(),
        events,
        forward_horizons=(1, 2),
    )

    assert len(result.outcomes) == 1
    assert result.outcomes[0].entry_price == 80
    assert result.outcomes[0].forward_returns == {
        1: Decimal("0.1"),
        2: Decimal("0.2"),
    }
    assert result.average_forward_returns == {
        1: Decimal("0.1"),
        2: Decimal("0.2"),
    }
