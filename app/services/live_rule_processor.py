from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.events import MarketEvent
from app.domain.rules import RuleDefinition
from app.indicators.engine import IndicatorEngine
from app.models.Alert import Alert
from app.models.Rule import Rule
from app.rules.evaluator import RuleEvaluation, RuleEvaluator
from app.rules.requirements import required_indicator_periods


class LiveRuleProcessor:
    """Processes normalized live bars through the shared SignalForge engines."""

    def __init__(self):
        self._indicators = IndicatorEngine()
        self._evaluator = RuleEvaluator()
        self._last_event_at: dict[tuple[str, str], datetime] = {}

    def process(self, event: MarketEvent, session: Session) -> list[Alert]:
        event_key = (event.symbol, event.timeframe)
        last_event_at = self._last_event_at.get(event_key)
        if last_event_at is not None and event.timestamp <= last_event_at:
            return []

        rules = list(
            session.execute(
                select(Rule)
                .where(
                    Rule.enabled.is_(True),
                    Rule.symbol == event.symbol,
                    Rule.timeframe == event.timeframe,
                )
                .options(selectinload(Rule.versions))
            ).scalars()
        )
        definitions = [
            (rule, self._current_definition(rule))
            for rule in rules
        ]
        periods = set().union(
            *(required_indicator_periods(definition) for _, definition in definitions)
        ) if definitions else set()

        snapshot = self._indicators.update(event, periods)
        self._last_event_at[event_key] = event.timestamp
        alerts = []
        for rule, definition in definitions:
            evaluation_key = f"{rule.id}:v{rule.current_version}"
            evaluation = self._evaluator.evaluate(
                evaluation_key,
                definition,
                event,
                snapshot,
            )
            if (
                evaluation.triggered
                and not self._already_alerted(rule, event, session)
                and self._cooldown_elapsed(rule, definition, event, session)
            ):
                alerts.append(self._persist_alert(rule, event, evaluation, session))
        session.commit()
        return alerts

    @staticmethod
    def _current_definition(rule: Rule) -> RuleDefinition:
        version = next(
            version
            for version in rule.versions
            if version.version == rule.current_version
        )
        return RuleDefinition.model_validate(version.dsl)

    @staticmethod
    def _persist_alert(
        rule: Rule,
        event: MarketEvent,
        evaluation: RuleEvaluation,
        session: Session,
    ) -> Alert:
        alert = Alert(
            rule_id=rule.id,
            rule_version=rule.current_version,
            symbol=event.symbol,
            timeframe=event.timeframe,
            market_timestamp=event.timestamp,
            dedupe_key=f"{rule.id}:v{rule.current_version}:{event.timestamp.isoformat()}",
            explanation={
                "conditions": [
                    {
                        "matched": condition.matched,
                        "left_value": _json_number(condition.left_value),
                        "operator": condition.operator,
                        "right_value": _json_number(condition.right_value),
                        "reason": condition.reason,
                    }
                    for condition in evaluation.conditions
                ]
            },
        )
        session.add(alert)
        return alert

    @staticmethod
    def _already_alerted(rule: Rule, event: MarketEvent, session: Session) -> bool:
        dedupe_key = f"{rule.id}:v{rule.current_version}:{event.timestamp.isoformat()}"
        return session.execute(
            select(Alert.id).where(Alert.dedupe_key == dedupe_key)
        ).scalar_one_or_none() is not None

    @staticmethod
    def _cooldown_elapsed(
        rule: Rule,
        definition: RuleDefinition,
        event: MarketEvent,
        session: Session,
    ) -> bool:
        if definition.cooldown_seconds == 0:
            return True
        latest_alert_at = session.execute(
            select(Alert.market_timestamp)
            .where(Alert.rule_id == rule.id)
            .order_by(Alert.market_timestamp.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest_alert_at is not None and latest_alert_at.tzinfo is None:
            latest_alert_at = latest_alert_at.replace(tzinfo=timezone.utc)
        return (
            latest_alert_at is None
            or event.timestamp
            >= latest_alert_at + timedelta(seconds=definition.cooldown_seconds)
        )


def _json_number(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
