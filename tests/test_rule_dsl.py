import pytest
from pydantic import ValidationError

from app.domain.rules import RuleDefinition


def test_parses_and_normalizes_rule_definition():
    rule = RuleDefinition.model_validate(
        {
            "dsl_version": "1.0",
            "symbol": "nvda",
            "timeframe": "1d",
            "conditions": {
                "all": [
                    {
                        "left": {"type": "metric", "metric": "price"},
                        "operator": "crosses_below",
                        "right": {"type": "indicator", "indicator": "sma", "period": 20},
                    },
                    {
                        "left": {
                            "type": "indicator",
                            "indicator": "volume_ratio",
                            "period": 20,
                        },
                        "operator": ">",
                        "right": {"type": "value", "value": 2},
                    },
                ]
            },
            "cooldown_seconds": 3600,
        }
    )

    assert rule.symbol == "NVDA"
    assert rule.dsl_version == "1.0"
    assert len(rule.conditions.all) == 2


@pytest.mark.parametrize(
    "invalid_conditions",
    [
        {},
        {"all": [], "any": []},
        {
            "all": [
                {
                    "left": {"type": "value", "value": 1},
                    "operator": ">",
                    "right": {"type": "metric", "metric": "price"},
                }
            ]
        },
        {
            "all": [
                {
                    "left": {"type": "metric", "metric": "price"},
                    "operator": "crosses_below",
                    "right": {"type": "value", "value": 100},
                }
            ]
        },
    ],
)
def test_rejects_invalid_condition_shapes(invalid_conditions):
    with pytest.raises(ValidationError):
        RuleDefinition.model_validate(
            {
                "symbol": "NVDA",
                "timeframe": "1d",
                "conditions": invalid_conditions,
            }
        )


def test_rejects_unknown_dsl_version_and_fields():
    with pytest.raises(ValidationError):
        RuleDefinition.model_validate(
            {
                "dsl_version": "2.0",
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
                "execute_python": "print('unsafe')",
            }
        )
