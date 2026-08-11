from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health_router import router


def test_health_endpoint_identifies_signalforge():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "signalforge"}
