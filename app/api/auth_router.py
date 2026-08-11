from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_db
from app.models.User import User
from app.schemas.auth import AuthRequest, UserResponse
from app.services.auth_service import (
    SESSION_DAYS,
    create_session,
    delete_session,
    find_session_user,
    hash_password,
    identifier_type,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE_NAME = "signalforge_session"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: AuthRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.execute(select(User).where(User.identifier == request.identifier)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account already exists for this identifier")
    user = User(
        identifier=request.identifier,
        identifier_type=identifier_type(request.identifier),
        password_hash=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, create_session(db, user))
    return user


@router.post("/login", response_model=UserResponse)
def login(request: AuthRequest, response: Response, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.identifier == request.identifier)).scalar_one_or_none()
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email, phone number, or password")
    set_session_cookie(response, create_session(db, user))
    return user


@router.get("/me", response_model=UserResponse)
def current_user(
    signalforge_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = find_session_user(db, signalforge_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_current_user(
    signalforge_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    user = find_session_user(db, signalforge_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    return user


def optional_current_user(
    signalforge_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    return find_session_user(db, signalforge_session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    signalforge_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    delete_session(db, signalforge_session)
    response.delete_cookie(COOKIE_NAME, httponly=True, samesite="lax")
