from fastapi import APIRouter, Query, HTTPException, status, Depends

from app.services.pollService import start_job
from app.schemas.poll import PollAccepted, PollRequest
from app.services.provider import fetch_price_by_provider
from sqlalchemy.orm import Session
from app.core.config import get_db

router = APIRouter()

@router.get("/prices/latest")
async def get_latest_price(symbol: str = Query(...), provider: str = "yfinance"):
    try:
        price_data = await fetch_price_by_provider(provider,symbol,False)
        return price_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unexpected internal error")



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


