from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.events import MarketEvent
from app.domain.rules import (
    Condition,
    IndicatorOperand,
    MetricOperand,
    Operator,
    RuleDefinition,
    TriggerMode,
    ValueOperand,
)
from app.indicators.engine import IndicatorSnapshot


@dataclass(frozen=True)
class ConditionEvaluation:
    matched: bool
    left_value: Decimal | None
    operator: str
    right_value: Decimal | None
    reason: str | None = None


@dataclass(frozen=True)
class RuleEvaluation:
    rule_key: str
    symbol: str
    evaluated_at: datetime
    matched: bool
    triggered: bool
    conditions: tuple[ConditionEvaluation, ...]


class RuleEvaluator:
    def __init__(self):
        self._previous_values: dict[tuple[str, int], tuple[Decimal, Decimal]] = {}
        self._previous_matches: dict[str, bool] = {}
        self._last_triggered_at: dict[str, datetime] = {}

    def evaluate(
        self,
        rule_key: str,
        rule: RuleDefinition,
        event: MarketEvent,
        indicators: IndicatorSnapshot,
    ) -> RuleEvaluation:
        if rule.symbol != event.symbol or rule.timeframe != event.timeframe:
            raise ValueError("rule and market event must have the same symbol and timeframe")

        conditions = rule.conditions.all or rule.conditions.any or []
        evaluations = tuple(
            self._evaluate_condition(rule_key, index, condition, event, indicators)
            for index, condition in enumerate(conditions)
        )
        matched = (
            all(result.matched for result in evaluations)
            if rule.conditions.all
            else any(result.matched for result in evaluations)
        )
        triggered = self._should_trigger(rule_key, rule, matched, event.timestamp)
        self._previous_matches[rule_key] = matched

        return RuleEvaluation(
            rule_key=rule_key,
            symbol=event.symbol,
            evaluated_at=event.timestamp,
            matched=matched,
            triggered=triggered,
            conditions=evaluations,
        )

    def _evaluate_condition(
        self,
        rule_key: str,
        index: int,
        condition: Condition,
        event: MarketEvent,
        indicators: IndicatorSnapshot,
    ) -> ConditionEvaluation:
        left = self._resolve(condition.left, event, indicators)
        right = self._resolve(condition.right, event, indicators)
        operator = Operator(condition.operator)

        if left is None or right is None:
            return ConditionEvaluation(
                matched=False,
                left_value=left,
                operator=operator.value,
                right_value=right,
                reason="insufficient_data",
            )

        state_key = (rule_key, index)
        previous = self._previous_values.get(state_key)
        if operator == Operator.CROSSES_ABOVE:
            matched = previous is not None and previous[0] <= previous[1] and left > right
        elif operator == Operator.CROSSES_BELOW:
            matched = previous is not None and previous[0] >= previous[1] and left < right
        else:
            matched = {
                Operator.LT: left < right,
                Operator.LTE: left <= right,
                Operator.EQ: left == right,
                Operator.GTE: left >= right,
                Operator.GT: left > right,
            }[operator]

        self._previous_values[state_key] = (left, right)
        return ConditionEvaluation(
            matched=matched,
            left_value=left,
            operator=operator.value,
            right_value=right,
        )

    @staticmethod
    def _resolve(operand, event: MarketEvent, indicators: IndicatorSnapshot):
        if isinstance(operand, ValueOperand):
            return Decimal(str(operand.value))
        if isinstance(operand, IndicatorOperand):
            return indicators.get(operand.indicator.value, operand.period)
        if isinstance(operand, MetricOperand):
            if operand.metric.value == "price":
                return event.close
            return Decimal(getattr(event, operand.metric.value))
        raise TypeError(f"unsupported operand: {type(operand).__name__}")

    def _should_trigger(
        self,
        rule_key: str,
        rule: RuleDefinition,
        matched: bool,
        evaluated_at: datetime,
    ) -> bool:
        previous_match = self._previous_matches.get(rule_key, False)
        trigger_mode = TriggerMode(rule.trigger)
        candidate = matched and (
            trigger_mode == TriggerMode.WHILE_TRUE or not previous_match
        )
        last_triggered = self._last_triggered_at.get(rule_key)
        cooldown_elapsed = (
            last_triggered is None
            or evaluated_at >= last_triggered + timedelta(seconds=rule.cooldown_seconds)
        )
        triggered = candidate and cooldown_elapsed
        if triggered:
            self._last_triggered_at[rule_key] = evaluated_at
        return triggered

