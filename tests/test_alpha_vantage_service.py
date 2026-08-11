import pytest

from app.services.alpha_vantage_service import build_alpha_vantage_movers


def test_alpha_vantage_movers_are_normalized_and_ranked():
    payload = {
        "top_gainers": [
            {"ticker": "BBB", "price": "11", "change_amount": "1", "change_percentage": "10%"},
            {"ticker": "AAA", "price": "12", "change_amount": "2", "change_percentage": "20%"},
        ],
        "top_losers": [
            {"ticker": "CCC", "price": "9", "change_amount": "-1", "change_percentage": "-10%"},
            {"ticker": "DDD", "price": "8", "change_amount": "-2", "change_percentage": "-20%"},
        ],
    }

    result = build_alpha_vantage_movers(payload)

    assert [item["symbol"] for item in result["gainers"]] == ["AAA", "BBB"]
    assert [item["symbol"] for item in result["losers"]] == ["DDD", "CCC"]
    assert result["gainers"][0]["sparkline"] == [10, 12]
    assert result["data_source"] == "alpha_vantage"


def test_alpha_vantage_limit_messages_are_errors():
    with pytest.raises(ValueError, match="rate limit"):
        build_alpha_vantage_movers({"Note": "rate limit reached"})
