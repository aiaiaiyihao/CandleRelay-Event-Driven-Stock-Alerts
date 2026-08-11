import pytest
from pydantic import ValidationError

from app.schemas.poll import PollRequest


def test_poll_request_has_safe_defaults_and_bounds():
    request = PollRequest(symbols=["NVDA"], interval=60)

    assert request.provider == "yfinance"


@pytest.mark.parametrize(
    "payload",
    [
        {"symbols": [], "interval": 60},
        {"symbols": ["NVDA"], "interval": 0},
        {"symbols": ["NVDA"], "interval": 86_401},
        {"symbols": ["NVDA"], "interval": 60, "provider": "unknown"},
    ],
)
def test_rejects_invalid_poll_configuration(payload):
    with pytest.raises(ValidationError):
        PollRequest.model_validate(payload)
