import pandas as pd

from app.services.yfinance_service import (
    CHART_INTERVALS,
    CHART_PRESETS,
    aggregate_chart_history,
    build_chart_points,
    moving_average,
)


def test_moving_average_waits_for_complete_window():
    values = [10.0, 20.0, 30.0, 40.0]

    assert moving_average(values, 3) == [None, None, 20.0, 30.0]


def test_moving_average_supports_common_long_periods():
    values = [float(value) for value in range(1, 201)]

    result = moving_average(values, 200)

    assert result[198] is None
    assert result[199] == 100.5


def test_chart_averages_are_calculated_before_display_range_is_trimmed():
    dates = pd.date_range("2025-01-01", periods=222, freq="B", tz="UTC")
    history = pd.DataFrame(
        {
            "Open": range(1, 223),
            "High": range(2, 224),
            "Low": range(0, 222),
            "Close": range(1, 223),
            "Volume": [1_000] * 222,
        },
        index=dates,
    )

    displayed = build_chart_points(history)[-22:]

    assert len(displayed) == 22
    assert displayed[0]["sma_20"] is not None
    assert displayed[0]["sma_50"] is not None
    assert displayed[0]["sma_200"] is not None


def test_chart_supports_intraday_weekly_and_monthly_intervals():
    assert set(CHART_INTERVALS) == {"1d", "30m", "60m", "1wk", "1mo"}
    assert CHART_INTERVALS["30m"]["history_period"] == "60d"
    assert CHART_INTERVALS["1wk"]["history_period"] == "10y"
    assert CHART_INTERVALS["1mo"]["history_period"] == "max"


def test_chart_presets_use_requested_points_for_each_range():
    assert CHART_PRESETS["1d"]["interval"] == "5m"
    assert CHART_PRESETS["1wk"]["interval"] == "30m"
    assert CHART_PRESETS["1mo"]["interval"] == "60m"
    assert CHART_PRESETS["3mo"]["interval"] == "1d"
    assert CHART_PRESETS["1y"]["interval"] == "1d"
    assert CHART_PRESETS["5y"]["interval"] == "1wk"
    assert CHART_PRESETS["max"]["points"] is None


def test_chart_presets_fetch_warmup_sessions_before_clipping_display_points():
    assert CHART_PRESETS["1d"]["history_period"] == "5d"
    assert CHART_PRESETS["1wk"]["history_period"] == "60d"
    assert CHART_PRESETS["3mo"]["history_period"] == "2y"
    assert CHART_PRESETS["1y"]["history_period"] == "5y"
    assert CHART_PRESETS["1d"]["points"] == 78
    assert CHART_PRESETS["3mo"]["points"] == 66


def test_chart_history_aggregates_ohlcv_without_averaging_prices():
    dates = pd.date_range("2025-01-02 09:30", periods=4, freq="5min", tz="America/New_York")
    history = pd.DataFrame(
        {
            "Open": [10, 12, 20, 22],
            "High": [13, 15, 24, 25],
            "Low": [9, 11, 19, 21],
            "Close": [12, 14, 22, 24],
            "Volume": [100, 200, 300, 400],
        },
        index=dates,
    )

    aggregated = aggregate_chart_history(history, frequency="10min")

    assert len(aggregated) == 2
    assert aggregated.iloc[0].to_dict() == {
        "Open": 10,
        "High": 15,
        "Low": 9,
        "Close": 14,
        "Volume": 300,
    }
