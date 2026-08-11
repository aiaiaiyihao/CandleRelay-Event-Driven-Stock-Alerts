from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth_router import router as auth_router
from app.api.favorite_router import router as favorite_router
from app.core.config import Base, get_db
from app.models.Favorite import Favorite
from app.models.User import User, UserSession


def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(favorite_router)

    def test_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    return TestClient(app)


def register(web, identifier):
    return web.post("/auth/register", json={"identifier": identifier, "password": "strongpass123"})


def test_favorites_are_private_to_each_user():
    first = client()
    second = client()
    register(first, "first@example.com")
    register(second, "second@example.com")

    assert first.post("/favorites", json={"symbol": "nvda"}).status_code == 201
    assert first.get("/favorites").json()[0]["symbol"] == "NVDA"
    assert second.get("/favorites").json() == []


def test_favorites_require_login_and_can_be_removed():
    web = client()
    assert web.get("/favorites").status_code == 401
    register(web, "user@example.com")
    web.post("/favorites", json={"symbol": "AAPL"})
    assert web.delete("/favorites/AAPL").status_code == 204
    assert web.get("/favorites").json() == []
