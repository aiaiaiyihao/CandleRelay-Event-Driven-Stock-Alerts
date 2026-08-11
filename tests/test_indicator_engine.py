from app.domain.events import MarketEvent
from app.indicators.engine import IndicatorEngine


def market_event(day: int, close: int, volume: int, symbol: str = "NVDA"):
    return MarketEvent.model_validate(
        {
            "symbol": symbol,
            "timeframe": "1d",
            "timestamp": f"2026-08-{day:02d}T20:00:00Z",
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": volume,
            "source": "test",
        }
    )


def test_computes_sma_with_current_bar_and_volume_ratio_against_prior_bars():
    engine = IndicatorEngine()

    assert engine.update(market_event(1, 10, 100), [2]).get("sma", 2) is None
    second = engine.update(market_event(2, 20, 100), [2])
    third = engine.update(market_event(3, 30, 300), [2])

    assert second.get("sma", 2) == 15
    assert second.get("volume_ratio", 2) is None
    assert third.get("sma", 2) == 25
    assert third.get("volume_ratio", 2) == 3


def test_keeps_symbol_state_isolated():
    engine = IndicatorEngine()

    engine.update(market_event(1, 10, 100, "NVDA"), [2])
    result = engine.update(market_event(2, 50, 100, "AAPL"), [2])

    assert result.get("sma", 2) is None


def test_rejects_period_beyond_configured_history():
    engine = IndicatorEngine(max_period=20)

    try:
        engine.update(market_event(1, 10, 100), [21])
    except ValueError as exc:
        assert "between 1 and 20" in str(exc)
    else:
        raise AssertionError("expected invalid period to be rejected")
