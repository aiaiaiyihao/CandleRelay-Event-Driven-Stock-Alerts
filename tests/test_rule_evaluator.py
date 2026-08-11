from app.domain.events import MarketEvent
from app.domain.rules import RuleDefinition
from app.indicators.engine import IndicatorSnapshot
from app.rules.evaluator import RuleEvaluator


def event(day: int, close: int):
    return MarketEvent.model_validate(
        {
            "symbol": "NVDA",
            "timeframe": "1d",
            "timestamp": f"2026-08-{day:02d}T20:00:00Z",
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 300,
            "source": "test",
        }
    )


def nvda_rule(operator="<", trigger="on_false_to_true", cooldown=0):
    return RuleDefinition.model_validate(
        {
            "symbol": "NVDA",
            "timeframe": "1d",
            "conditions": {
                "all": [
                    {
                        "left": {"type": "metric", "metric": "price"},
                        "operator": operator,
                        "right": {"type": "indicator", "indicator": "sma", "period": 20},
                    },
                    {
                        "left": {"type": "indicator", "indicator": "volume_ratio", "period": 20},
                        "operator": ">",
                        "right": {"type": "value", "value": 2},
                    },
                ]
            },
            "trigger": trigger,
            "cooldown_seconds": cooldown,
        }
    )


def indicators(sma=100, volume_ratio=3):
    return IndicatorSnapshot({"sma_20": sma, "volume_ratio_20": volume_ratio})


def test_returns_explainable_condition_values():
    result = RuleEvaluator().evaluate("rule-1", nvda_rule(), event(1, 90), indicators())

    assert result.matched is True
    assert result.triggered is True
    assert result.conditions[0].left_value == 90
    assert result.conditions[0].right_value == 100
    assert result.conditions[1].matched is True


def test_marks_missing_indicators_as_insufficient_data():
    result = RuleEvaluator().evaluate(
        "rule-1", nvda_rule(), event(1, 90), IndicatorSnapshot({})
    )

    assert result.matched is False
    assert result.conditions[0].reason == "insufficient_data"


def test_crosses_below_requires_a_previous_above_value():
    evaluator = RuleEvaluator()
    rule = nvda_rule(operator="crosses_below")

    before = evaluator.evaluate("rule-1", rule, event(1, 110), indicators())
    crossing = evaluator.evaluate("rule-1", rule, event(2, 90), indicators())

    assert before.matched is False
    assert crossing.matched is True
    assert crossing.triggered is True


def test_false_to_true_mode_does_not_repeat_trigger():
    evaluator = RuleEvaluator()
    rule = nvda_rule()

    first = evaluator.evaluate("rule-1", rule, event(1, 90), indicators())
    second = evaluator.evaluate("rule-1", rule, event(2, 80), indicators())

    assert first.triggered is True
    assert second.matched is True
    assert second.triggered is False


def test_cooldown_blocks_repeated_while_true_trigger():
    evaluator = RuleEvaluator()
    rule = nvda_rule(trigger="while_true", cooldown=172800)

    first = evaluator.evaluate("rule-1", rule, event(1, 90), indicators())
    second = evaluator.evaluate("rule-1", rule, event(2, 90), indicators())
    third = evaluator.evaluate("rule-1", rule, event(3, 90), indicators())

    assert first.triggered is True
    assert second.triggered is False
    assert third.triggered is True
