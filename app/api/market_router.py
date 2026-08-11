from fastapi import APIRouter, HTTPException

from app.schemas.market import MarketOverview
from app.services.yfinance_service import fetch_market_overview


router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview", response_model=MarketOverview)
async def market_overview():
    try:
        return await fetch_market_overview()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
