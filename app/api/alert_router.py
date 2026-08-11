from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.schemas.alert import AlertResponse
from app.services.alert_service import acknowledge_alert, list_alerts


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertResponse])
def get_alerts(
    rule_id: str | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return list_alerts(db, rule_id=rule_id, acknowledged=acknowledged)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def post_acknowledge(alert_id: str, db: Session = Depends(get_db)):
    alert = acknowledge_alert(alert_id, db)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

