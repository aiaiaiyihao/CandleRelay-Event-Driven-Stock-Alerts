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
            "text": "当 NVDA 跌破 SMA20，并且成交量超过过去 20 天平均值的两倍时提醒我。",
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
        json={"text": "当 NVDA RSI14 低于 30 时提醒我"},
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
