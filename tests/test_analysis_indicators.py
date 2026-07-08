"""Test analysis/indicators.py: MA, stack order, volume ratio."""
from analysis.indicators import (
    is_breakout_volume,
    is_volume_present,
    ma_stack_order,
    moving_average,
    rolling_ma,
    volume_ratio,
)


def test_rolling_ma_basic():
    result = rolling_ma([10, 20, 30, 40, 50], 3)
    assert result == [None, None, 20, 30, 40]


def test_rolling_ma_none_when_gap_in_window():
    result = rolling_ma([10, 20, None, 40, 50], 3)
    # window utk index 2,3,4 masing2 mengandung None -> None semua 3 terakhir
    assert result == [None, None, None, None, None]


def test_rolling_ma_matches_moving_average_at_last_index():
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    period = 4
    assert rolling_ma(values, period)[-1] == moving_average(values, period)


def test_moving_average_full_window():
    assert moving_average([1, 2, 3, 4, 5], 5) == 3
    assert moving_average([10, 20, 30], 3) == 20


def test_moving_average_uses_last_n_values():
    # period=3 dari 5 nilai -> ambil 3 TERAKHIR (30,40,50), bukan 3 pertama
    assert moving_average([10, 20, 30, 40, 50], 3) == 40


def test_moving_average_none_when_insufficient_data():
    assert moving_average([1, 2], 5) is None
    assert moving_average([], 1) is None


def test_ma_stack_order_bullish():
    assert ma_stack_order(110, 100, 90, 80) == "bullish"


def test_ma_stack_order_bearish():
    assert ma_stack_order(80, 90, 100, 110) == "bearish"


def test_ma_stack_order_mixed():
    assert ma_stack_order(100, 110, 90, 80) == "mixed"
    assert ma_stack_order(None, 100, 90, 80) == "mixed"


def test_volume_ratio_basic():
    assert volume_ratio(150, 100) == 1.5
    assert volume_ratio(None, 100) is None
    assert volume_ratio(100, None) is None
    assert volume_ratio(100, 0) is None


def test_is_breakout_volume():
    assert is_breakout_volume(1.6) is True
    assert is_breakout_volume(1.5) is False  # strict > 1.5, bukan >=
    assert is_breakout_volume(1.4) is False
    assert is_breakout_volume(None) is False


def test_is_volume_present():
    assert is_volume_present(0.8) is True
    assert is_volume_present(0.79) is False
    assert is_volume_present(1.2) is True
    assert is_volume_present(None) is False
