from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth_router import require_current_user
from app.core.config import get_db
from app.models.Favorite import Favorite
from app.models.User import User
from app.schemas.favorite import FavoriteCreate, FavoriteResponse


router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteResponse])
def get_favorites(
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    return db.execute(
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at)
    ).scalars().all()


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(
    request: FavoriteCreate,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    key = {"user_id": user.id, "symbol": request.symbol}
    existing = db.get(Favorite, key)
    if existing is not None:
        return existing
    favorite = Favorite(**key)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    symbol: str,
    user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    favorite = db.get(Favorite, {"user_id": user.id, "symbol": symbol.upper()})
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite symbol not found")
    db.delete(favorite)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
