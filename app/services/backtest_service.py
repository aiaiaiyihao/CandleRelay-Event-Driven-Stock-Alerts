from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.backtesting.engine import BacktestEngine
from app.domain.rules import RuleDefinition
from app.models.BacktestRun import BacktestRun
from app.models.MarketBar import MarketBar
from app.models.Rule import Rule
from app.schemas.backtest import BacktestCreate, BacktestRangeCreate, BacktestResponse
from app.domain.events import MarketEvent


class RuleNotFoundError(Exception):
    pass


class BacktestInputError(Exception):
    pass


def execute_backtest(request: BacktestCreate, session: Session) -> BacktestResponse:
    rule = session.execute(
        select(Rule)
        .where(Rule.id == request.rule_id)
        .options(selectinload(Rule.versions))
    ).scalar_one_or_none()
    if rule is None:
        raise RuleNotFoundError(request.rule_id)

    version = next(
        item for item in rule.versions if item.version == rule.current_version
    )
    definition = RuleDefinition.model_validate(version.dsl)
    _validate_events(definition, request)

    run = BacktestRun(
        rule_id=rule.id,
        rule_version=version.version,
        dsl_snapshot=version.dsl,
        engine_version="1.0",
        status="running",
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        result = BacktestEngine().run(run.id, definition, request.events)
        run.status = "completed"
        run.bars_processed = result.bars_processed
        run.trigger_count = len(result.triggers)
        run.result_summary = {
            "triggers": [
                {
                    "evaluated_at": outcome.evaluation.evaluated_at.isoformat(),
                    "entry_price": _json_number(outcome.entry_price),
                    "forward_returns": {
                        str(horizon): _json_number(value)
                        for horizon, value in outcome.forward_returns.items()
                    },
                    "conditions": [
                        {
                            "matched": condition.matched,
                            "left_value": _json_number(condition.left_value),
                            "operator": condition.operator,
                            "right_value": _json_number(condition.right_value),
                            "reason": condition.reason,
                        }
                        for condition in outcome.evaluation.conditions
                    ],
                }
                for outcome in result.outcomes
            ],
            "average_forward_returns": {
                str(horizon): _json_number(value)
                for horizon, value in result.average_forward_returns.items()
            },
        }
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        raise

    return _to_response(run)


def execute_backtest_range(
    request: BacktestRangeCreate,
    session: Session,
) -> BacktestResponse:
    rule = session.get(Rule, request.rule_id)
    if rule is None:
        raise RuleNotFoundError(request.rule_id)
    bars = session.execute(
        select(MarketBar)
        .where(
            MarketBar.symbol == rule.symbol,
            MarketBar.timeframe == rule.timeframe,
            MarketBar.timestamp >= request.start,
            MarketBar.timestamp <= request.end,
        )
        .order_by(MarketBar.timestamp)
    ).scalars().all()
    if not bars:
        raise BacktestInputError("no market bars found for the requested range")
    events = [
        MarketEvent(
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            timestamp=_as_utc(bar.timestamp),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            source=bar.source,
        )
        for bar in bars
    ]
    return execute_backtest(
        BacktestCreate(rule_id=request.rule_id, events=events),
        session,
    )


def get_backtest(run_id: str, session: Session) -> BacktestResponse | None:
    run = session.get(BacktestRun, run_id)
    return _to_response(run) if run else None


def _validate_events(definition: RuleDefinition, request: BacktestCreate) -> None:
    mismatched = [
        event
        for event in request.events
        if event.symbol != definition.symbol or event.timeframe != definition.timeframe
    ]
    if mismatched:
        raise BacktestInputError(
            "all events must match the rule symbol and timeframe"
        )


def _json_number(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _to_response(run: BacktestRun) -> BacktestResponse:
    return BacktestResponse(
        id=run.id,
        rule_id=run.rule_id,
        rule_version=run.rule_version,
        engine_version=run.engine_version,
        status=run.status,
        bars_processed=run.bars_processed,
        trigger_count=run.trigger_count,
        result_summary=run.result_summary,
        error=run.error,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )
