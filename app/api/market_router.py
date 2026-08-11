from fastapi import APIRouter, HTTPException, Query

from app.schemas.market import MarketOverview
from app.services.yfinance_service import fetch_market_overview, fetch_market_snapshots


router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview", response_model=MarketOverview)
async def market_overview(refresh: bool = Query(default=False)):
    try:
        return await fetch_market_overview(force_refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/quotes")
async def market_quotes(symbols: str = Query(..., min_length=1, max_length=400)):
    requested = list(dict.fromkeys(symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()))
    if len(requested) > 50:
        raise HTTPException(status_code=422, detail="A maximum of 50 symbols is supported")
    try:
        return await fetch_market_snapshots(requested)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
