from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.models.WatchlistItem import WatchlistItem
from app.schemas.watchlist import WatchlistCreate, WatchlistResponse


router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistResponse])
def get_watchlist(db: Session = Depends(get_db)):
    return db.execute(
        select(WatchlistItem).order_by(WatchlistItem.created_at)
    ).scalars().all()


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def post_watchlist_item(request: WatchlistCreate, db: Session = Depends(get_db)):
    existing = db.get(WatchlistItem, request.symbol)
    if existing is not None:
        return existing
    item = WatchlistItem(symbol=request.symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist_item(symbol: str, db: Session = Depends(get_db)):
    item = db.get(WatchlistItem, symbol.upper())
    if item is None:
        raise HTTPException(status_code=404, detail="Tracked symbol not found")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

