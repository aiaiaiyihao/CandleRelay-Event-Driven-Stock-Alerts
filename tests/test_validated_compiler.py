import pytest

from app.compilers.base import CompilerOutputError, ValidatedRuleCompiler


class FakeProvider:
    def __init__(self, candidate):
        self.candidate = candidate

    def generate_candidate(self, text):
        return self.candidate


def valid_candidate():
    return {
        "definition": {
            "dsl_version": "1.0",
            "symbol": "NVDA",
            "timeframe": "1d",
            "conditions": {
                "all": [
                    {
                        "left": {"type": "metric", "metric": "price"},
                        "operator": "crosses_below",
                        "right": {"type": "indicator", "indicator": "sma", "period": 20},
                    }
                ]
            },
        },
        "explanation": "Alert when NVDA crosses below its 20-day SMA.",
        "warnings": [],
    }


def test_accepts_only_candidates_that_pass_rule_dsl_validation():
    result = ValidatedRuleCompiler(FakeProvider(valid_candidate())).compile("rule")

    assert result.definition.symbol == "NVDA"
    assert result.definition.dsl_version == "1.0"


def test_rejects_provider_attempt_to_add_executable_fields():
    candidate = valid_candidate()
    candidate["definition"]["execute_python"] = "import os"

    with pytest.raises(CompilerOutputError):
        ValidatedRuleCompiler(FakeProvider(candidate)).compile("unsafe output")


def test_rejects_semantically_invalid_provider_output():
    candidate = valid_candidate()
    candidate["definition"]["conditions"] = {"all": []}

    with pytest.raises(CompilerOutputError):
        ValidatedRuleCompiler(FakeProvider(candidate)).compile("bad output")


def test_rejects_empty_input_before_calling_provider():
    with pytest.raises(ValueError, match="must not be empty"):
        ValidatedRuleCompiler(FakeProvider(valid_candidate())).compile("  ")
