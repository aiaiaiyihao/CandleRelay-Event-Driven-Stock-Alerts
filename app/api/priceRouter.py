from fastapi import APIRouter, Query, HTTPException, status, Depends

from app.services.pollService import start_job
from app.schemas.poll import PollAccepted, PollRequest
from app.services.provider import fetch_price_by_provider
from app.services.yfinance_service import (
    CHART_RANGES,
    fetch_chart_yfinance,
    search_stocks_yfinance,
)
from app.schemas.stock_chart import StockChartResponse
from app.schemas.stock_search import StockSearchResult
from sqlalchemy.orm import Session
from app.core.config import get_db

router = APIRouter()


@router.get("/stocks/search", response_model=list[StockSearchResult])
async def search_stocks(q: str = Query(..., min_length=1, max_length=80)):
    try:
        return await search_stocks_yfinance(q.strip())
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/stocks/{symbol}/chart", response_model=StockChartResponse)
async def get_stock_chart(
    symbol: str,
    chart_range: str = Query(default="3mo", alias="range"),
):
    if chart_range not in CHART_RANGES:
        raise HTTPException(
            status_code=422,
            detail=f"range must be one of {sorted(CHART_RANGES)}",
        )
    try:
        return await fetch_chart_yfinance(symbol.upper(), chart_range)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

#get the latest price get request by symbol and provider
@router.get("/prices/latest")
async def get_latest_price(symbol: str = Query(...), provider: str = "yfinance"):
    try:
        price_data = await fetch_price_by_provider(provider,symbol,False)
        return price_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unexpected internal error")


#start a polling job by a list of symbols post request
@router.post("/prices/poll", response_model=PollAccepted, status_code=status.HTTP_202_ACCEPTED)
async def poll_prices(req: PollRequest, db: Session = Depends(get_db)):
    """
    Start a background polling job that fetches latest prices
    for the given symbols and stores them in PostgreSQL every interval seconds.
    """
    job = await start_job(req, db)
    return PollAccepted(
        job_id=job.id,
        status="accepted",
        config=req
    )
