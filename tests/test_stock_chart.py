import pandas as pd

from app.services.yfinance_service import build_chart_points, moving_average


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
