"""Test web/app.py pure helpers (Panel 1 snapshot Hari/Minggu/Bulan/Tahun compare)."""
import pytest

from web.app import COMPARE_PERIODS, _compare_from_series


def test_compare_from_series_all_periods_available():
    # series DESC (baru->lama), 1 titik per hari mundur dari 2026-07-09
    series = [
        ("2026-07-09", 100.0),
        ("2026-07-08", 90.0),
        ("2026-07-02", 80.0),
        ("2026-06-09", 70.0),
        ("2025-07-09", 50.0),
    ]
    result = _compare_from_series(series, "2026-07-09", 100.0)
    assert result["day"]["past_value"] == 90.0
    assert result["day"]["delta"] == 10.0
    assert result["day"]["pct"] == pytest.approx(11.111, abs=0.01)
    assert result["week"]["past_value"] == 80.0
    assert result["month"]["past_value"] == 70.0
    assert result["year"]["past_value"] == 50.0
    assert result["year"]["delta"] == 50.0


def test_compare_from_series_missing_period_returns_none():
    # cuma ada data day (kemarin), tidak ada yang cukup jauh utk week/month/year
    series = [("2026-07-09", 100.0), ("2026-07-08", 90.0)]
    result = _compare_from_series(series, "2026-07-09", 100.0)
    assert result["day"] is not None
    assert result["week"] is None
    assert result["month"] is None
    assert result["year"] is None


def test_compare_from_series_no_current_value_returns_all_none():
    series = [("2026-07-08", 90.0)]
    result = _compare_from_series(series, "2026-07-09", None)
    assert all(v is None for v in result.values())


def test_compare_from_series_skips_null_values_in_series():
    # titik dgn value None (kolom kosong hari itu) dilewati, cari yang valid berikutnya
    series = [
        ("2026-07-09", 100.0),
        ("2026-07-08", None),
        ("2026-07-07", 88.0),
    ]
    result = _compare_from_series(series, "2026-07-09", 100.0)
    assert result["day"]["past_value"] == 88.0
    assert result["day"]["past_date"] == "2026-07-07"


def test_compare_periods_keys():
    assert set(COMPARE_PERIODS) == {"day", "week", "month", "year"}
    assert COMPARE_PERIODS["day"] == 1
    assert COMPARE_PERIODS["week"] == 7
    assert COMPARE_PERIODS["month"] == 30
    assert COMPARE_PERIODS["year"] == 365
