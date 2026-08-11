from app.services.yfinance_service import moving_average


def test_moving_average_waits_for_complete_window():
    values = [10.0, 20.0, 30.0, 40.0]

    assert moving_average(values, 3) == [None, None, 20.0, 30.0]


def test_moving_average_supports_common_long_periods():
    values = [float(value) for value in range(1, 201)]

    result = moving_average(values, 200)

    assert result[198] is None
    assert result[199] == 100.5
