from dataclasses import dataclass
from typing import Iterable

from app.domain.events import MarketEvent
from app.domain.rules import RuleDefinition
from app.indicators.engine import IndicatorEngine
from app.rules.evaluator import RuleEvaluation, RuleEvaluator
from app.rules.requirements import required_indicator_periods


@dataclass(frozen=True)
class BacktestResult:
    rule_key: str
    bars_processed: int
    evaluations: tuple[RuleEvaluation, ...]

    @property
    def triggers(self) -> tuple[RuleEvaluation, ...]:
        return tuple(result for result in self.evaluations if result.triggered)


class BacktestEngine:
    """Chronologically replays bars through the same engines used in real time."""

    def run(
        self,
        rule_key: str,
        rule: RuleDefinition,
        events: Iterable[MarketEvent],
    ) -> BacktestResult:
        ordered_events = sorted(events, key=lambda event: event.timestamp)
        indicator_engine = IndicatorEngine()
        rule_evaluator = RuleEvaluator()
        periods = required_indicator_periods(rule)
        evaluations = []

        for event in ordered_events:
            indicators = indicator_engine.update(event, periods)
            evaluations.append(
                rule_evaluator.evaluate(rule_key, rule, event, indicators)
            )

        return BacktestResult(
            rule_key=rule_key,
            bars_processed=len(ordered_events),
            evaluations=tuple(evaluations),
        )

