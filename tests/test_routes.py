import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}

def test_latest_price_endpoint():
    response = client.get("/prices/latest?symbol=AAPL")
    assert response.status_code == 200
    assert "symbol" in response.json()
