from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth_router import router
from app.core.config import Base, get_db
from app.models.User import User, UserSession


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


def test_registers_with_email_and_keeps_authenticated_session():
    web = client()

    registered = web.post(
        "/auth/register",
        json={"identifier": "Trader@Example.com", "password": "strongpass123"},
    )

    assert registered.status_code == 201
    assert registered.json()["identifier"] == "trader@example.com"
    assert registered.json()["identifier_type"] == "email"
    assert "signalforge_session" in registered.cookies
    assert web.get("/auth/me").status_code == 200


def test_registers_with_normalized_phone_number():
    web = client()

    response = web.post(
        "/auth/register",
        json={"identifier": "+1 (415) 555-0100", "password": "strongpass123"},
    )

    assert response.status_code == 201
    assert response.json()["identifier"] == "+14155550100"
    assert response.json()["identifier_type"] == "phone"


def test_login_rejects_wrong_password_and_logout_ends_session():
    web = client()
    credentials = {"identifier": "user@example.com", "password": "strongpass123"}
    web.post("/auth/register", json=credentials)
    web.post("/auth/logout")

    assert web.get("/auth/me").status_code == 401
    assert web.post("/auth/login", json={**credentials, "password": "wrongpass"}).status_code == 401
    assert web.post("/auth/login", json=credentials).status_code == 200
    assert web.get("/auth/me").status_code == 200


def test_rejects_duplicate_identifier_and_invalid_input():
    web = client()
    credentials = {"identifier": "user@example.com", "password": "strongpass123"}

    assert web.post("/auth/register", json=credentials).status_code == 201
    assert web.post("/auth/register", json=credentials).status_code == 409
    assert web.post(
        "/auth/register",
        json={"identifier": "not-an-email", "password": "strongpass123"},
    ).status_code == 422
    assert web.post(
        "/auth/register",
        json={"identifier": "other@example.com", "password": "short"},
    ).status_code == 422
