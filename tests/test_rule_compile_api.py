from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ruleRouter import router


def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_compiles_product_example_into_validated_rule_dsl():
    response = client().post(
        "/rules/compile",
        json={
            "text": "Alert me when NVDA crosses below SMA20 and volume is more than 2 times the average of the past 20 trading days.",
            "cooldown_seconds": 3600,
        },
    )

    assert response.status_code == 200
    body = response.json()
    definition = body["definition"]
    assert definition["symbol"] == "NVDA"
    assert definition["conditions"]["all"] == [
        {
            "left": {"type": "metric", "metric": "price"},
            "operator": "crosses_below",
            "right": {"type": "indicator", "indicator": "sma", "period": 20},
        },
        {
            "left": {"type": "indicator", "indicator": "volume_ratio", "period": 20},
            "operator": ">",
            "right": {"type": "value", "value": 2.0},
        },
    ]
    assert definition["cooldown_seconds"] == 3600
    assert "defaulted to daily" in body["warnings"][0]


def test_compiles_supported_english_expression_with_explicit_timeframe():
    response = client().post(
        "/rules/compile",
        json={"text": "When AAPL crosses below SMA50 on daily bars, alert me."},
    )

    assert response.status_code == 200
    assert response.json()["definition"]["symbol"] == "AAPL"
    assert response.json()["definition"]["timeframe"] == "1d"
    assert response.json()["warnings"] == []


def test_rejects_text_outside_supported_compiler_grammar():
    response = client().post(
        "/rules/compile",
        json={"text": "Tell me if the market looks interesting."},
    )

    assert response.status_code == 422


def test_compiles_rsi_threshold_rule():
    response = client().post(
        "/rules/compile",
        json={"text": "Alert me when NVDA RSI14 below 30."},
    )

    assert response.status_code == 200
    condition = response.json()["definition"]["conditions"]["all"][0]
    assert condition == {
        "left": {"type": "indicator", "indicator": "rsi", "period": 14},
        "operator": "<",
        "right": {"type": "value", "value": 30.0},
    }


def test_compiles_indicator_cross_rule():
    response = client().post(
        "/rules/compile",
        json={"text": "When NVDA EMA20 crosses above SMA50 on daily bars, alert me."},
    )

    assert response.status_code == 200
    condition = response.json()["definition"]["conditions"]["all"][0]
    assert condition == {
        "left": {"type": "indicator", "indicator": "ema", "period": 20},
        "operator": "crosses_above",
        "right": {"type": "indicator", "indicator": "sma", "period": 50},
    }


def test_compiles_each_condition_category_on_its_own():
    cases = [
        ("Alert when MSFT price is above SMA200.", "sma", 200),
        ("Alert when AAPL price is below $175.", "value", 175.0),
        ("Alert when TSLA volume is more than 1.5 times the past 30 days average.", "volume_ratio", 30),
    ]
    for text, operand_type, expected in cases:
        response = client().post("/rules/compile", json={"text": text})
        assert response.status_code == 200, response.json()
        conditions = response.json()["definition"]["conditions"]["all"]
        assert len(conditions) == 1
        condition = conditions[0]
        if operand_type == "sma":
            assert condition["right"] == {"type": "indicator", "indicator": "sma", "period": expected}
        elif operand_type == "value":
            assert condition["right"] == {"type": "value", "value": expected}
        else:
            assert condition["left"] == {"type": "indicator", "indicator": "volume_ratio", "period": expected}


def test_compiles_any_two_condition_categories():
    response = client().post(
        "/rules/compile",
        json={"text": "Alert when NVDA crosses below SMA50 and price is above $100."},
    )
    assert response.status_code == 200, response.json()
    conditions = response.json()["definition"]["conditions"]["all"]
    assert [condition["operator"] for condition in conditions] == ["crosses_below", ">"]


def test_compiles_moving_average_price_range_and_volume_together():
    response = client().post(
        "/rules/compile",
        json={"text": "Alert when NVDA crosses above SMA20, price is between $120 and $150, and volume is more than 2 times the past 50 trading days average."},
    )
    assert response.status_code == 200, response.json()
    conditions = response.json()["definition"]["conditions"]["all"]
    assert [condition["operator"] for condition in conditions] == ["crosses_above", ">=", "<=", ">"]
    assert conditions[1]["right"]["value"] == 120.0
    assert conditions[2]["right"]["value"] == 150.0
    assert conditions[3]["left"]["period"] == 50
