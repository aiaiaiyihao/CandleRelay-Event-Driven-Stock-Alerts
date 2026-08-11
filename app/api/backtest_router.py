from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.schemas.backtest import BacktestCreate, BacktestRangeCreate, BacktestResponse
from app.services.backtest_service import (
    BacktestInputError,
    RuleNotFoundError,
    execute_backtest,
    execute_backtest_range,
    get_backtest,
)


router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("/range", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
def post_backtest_range(
    request: BacktestRangeCreate,
    db: Session = Depends(get_db),
):
    try:
        return execute_backtest_range(request, db)
    except RuleNotFoundError:
        raise HTTPException(status_code=404, detail="Rule not found")
    except BacktestInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("", response_model=BacktestResponse, status_code=status.HTTP_201_CREATED)
def post_backtest(request: BacktestCreate, db: Session = Depends(get_db)):
    try:
        return execute_backtest(request, db)
    except RuleNotFoundError:
        raise HTTPException(status_code=404, detail="Rule not found")
    except BacktestInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{run_id}", response_model=BacktestResponse)
def get_backtest_by_id(run_id: str, db: Session = Depends(get_db)):
    run = get_backtest(run_id, db)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return run
