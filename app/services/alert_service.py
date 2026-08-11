from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.Alert import Alert
from app.models.Rule import Rule
from app.schemas.alert import AlertResponse


def list_alerts(
    session: Session,
    rule_id: str | None = None,
    acknowledged: bool | None = None,
    user_id: str | None = None,
) -> list[AlertResponse]:
    statement = select(Alert).order_by(Alert.market_timestamp.desc())
    if user_id is not None:
        statement = statement.join(Rule, Alert.rule_id == Rule.id).where(Rule.user_id == user_id)
    if rule_id is not None:
        statement = statement.where(Alert.rule_id == rule_id)
    if acknowledged is not None:
        statement = statement.where(Alert.acknowledged.is_(acknowledged))
    return [_to_response(alert) for alert in session.execute(statement).scalars()]


def acknowledge_alert(alert_id: str, session: Session, user_id: str | None = None) -> AlertResponse | None:
    alert = session.get(Alert, alert_id)
    if alert is None:
        return None
    if user_id is not None:
        owner_id = session.execute(select(Rule.user_id).where(Rule.id == alert.rule_id)).scalar_one_or_none()
        if owner_id != user_id:
            return None
    if not alert.acknowledged:
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(alert)
    return _to_response(alert)


def _to_response(alert: Alert) -> AlertResponse:
    return AlertResponse(
        id=alert.id,
        rule_id=alert.rule_id,
        rule_version=alert.rule_version,
        symbol=alert.symbol,
        timeframe=alert.timeframe,
        market_timestamp=alert.market_timestamp,
        explanation=alert.explanation,
        acknowledged=alert.acknowledged,
        created_at=alert.created_at,
        acknowledged_at=alert.acknowledged_at,
    )
