from dataclasses import dataclass
from decimal import Decimal
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
    outcomes: tuple["TriggerOutcome", ...]

    @property
    def triggers(self) -> tuple[RuleEvaluation, ...]:
        return tuple(result for result in self.evaluations if result.triggered)

    @property
    def average_forward_returns(self) -> dict[int, Decimal | None]:
        horizons = sorted(
            {horizon for outcome in self.outcomes for horizon in outcome.forward_returns}
        )
        averages = {}
        for horizon in horizons:
            values = [
                outcome.forward_returns[horizon]
                for outcome in self.outcomes
                if outcome.forward_returns[horizon] is not None
            ]
            averages[horizon] = (
                sum(values, Decimal(0)) / Decimal(len(values)) if values else None
            )
        return averages


@dataclass(frozen=True)
class TriggerOutcome:
    evaluation: RuleEvaluation
    entry_price: Decimal
    forward_returns: dict[int, Decimal | None]


class BacktestEngine:
    """Chronologically replays bars through the same engines used in real time."""

    def run(
        self,
        rule_key: str,
        rule: RuleDefinition,
        events: Iterable[MarketEvent],
        forward_horizons: tuple[int, ...] = (1, 5, 20),
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

        outcomes = tuple(
            TriggerOutcome(
                evaluation=evaluation,
                entry_price=event.close,
                forward_returns={
                    horizon: self._forward_return(ordered_events, index, horizon)
                    for horizon in forward_horizons
                },
            )
            for index, (event, evaluation) in enumerate(zip(ordered_events, evaluations))
            if evaluation.triggered
        )
        return BacktestResult(
            rule_key=rule_key,
            bars_processed=len(ordered_events),
            evaluations=tuple(evaluations),
            outcomes=outcomes,
        )

    @staticmethod
    def _forward_return(
        events: list[MarketEvent],
        trigger_index: int,
        horizon: int,
    ) -> Decimal | None:
        if horizon < 1:
            raise ValueError("forward return horizons must be positive")
        future_index = trigger_index + horizon
        if future_index >= len(events):
            return None
        entry = events[trigger_index].close
        return events[future_index].close / entry - Decimal(1)
