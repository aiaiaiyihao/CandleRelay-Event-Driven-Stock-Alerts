from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.schemas.market import MarketOverview, SectorStocksResponse
from app.schemas.market_chat import MarketChatRequest, MarketChatResponse
from app.services.market_chat_service import answer_market_question
from app.services.yfinance_service import fetch_market_overview, fetch_market_snapshots, fetch_sector_stocks


router = APIRouter(prefix="/market", tags=["market"])


@router.post("/chat", response_model=MarketChatResponse)
async def market_chat(request: MarketChatRequest):
    try:
        return await answer_market_question(request.question, request.context_symbol)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/overview", response_model=MarketOverview)
async def market_overview(refresh: bool = Query(default=False)):
    try:
        return await fetch_market_overview(force_refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/sectors/{sector_slug}/stocks", response_model=SectorStocksResponse)
async def sector_stocks(
    sector_slug: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    sort_order: Literal["desc", "asc"] = Query(default="desc"),
):
    try:
        return await fetch_sector_stocks(sector_slug, page, page_size, sort_order)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown sector: {sector_slug}")
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
