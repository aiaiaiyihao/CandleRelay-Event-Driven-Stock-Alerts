from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.watchlist_router import router
from app.core.config import Base, get_db
from app.models.WatchlistItem import WatchlistItem


def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    app = FastAPI()
    app.include_router(router)

    def test_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    return TestClient(app)


def test_add_list_and_remove_tracked_symbol():
    web = client()

    created = web.post("/watchlist", json={"symbol": "nvda"})
    assert created.status_code == 201
    assert created.json()["symbol"] == "NVDA"

    duplicate = web.post("/watchlist", json={"symbol": "NVDA"})
    assert duplicate.status_code == 201
    assert len(web.get("/watchlist").json()) == 1

    assert web.delete("/watchlist/NVDA").status_code == 204
    assert web.get("/watchlist").json() == []


def test_rejects_invalid_symbol_and_missing_delete():
    web = client()

    assert web.post("/watchlist", json={"symbol": "NVDA;DROP"}).status_code == 422
    assert web.delete("/watchlist/MISSING").status_code == 404
