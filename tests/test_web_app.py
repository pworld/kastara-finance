"""Test web/app.py pure helpers (Panel 1 snapshot compare + data-gap detection)."""
import pytest

from web.app import (
    COMPARE_PERIODS,
    INSTRUMENT_SOURCE,
    SNAPSHOT_FIELDS,
    _compare_from_series,
    _detect_gaps,
)


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


# ---------- SNAPSHOT_FIELDS categories ----------

def test_snapshot_fields_all_have_category():
    for field in SNAPSHOT_FIELDS:
        assert field["category"] in {"Crypto (BTC)", "Makro Global", "Ekuitas & FX"}


# ---------- Data gap detection ----------

def test_detect_gaps_no_gap_daily():
    dates = ["2026-07-07", "2026-07-08", "2026-07-09"]
    assert _detect_gaps(dates, "DAILY") == []


def test_detect_gaps_weekly_wed_always_empty():
    # WALCL/TGA -- rilis mingguan, "kosong" antar-Rabu itu wajar, bukan gap
    dates = ["2026-06-24", "2026-07-01"]
    assert _detect_gaps(dates, "WEEKLY_WED") == []


def test_detect_gaps_single_missing_day_not_reported():
    # gap 1 hari (mis. libur biasa) sengaja TIDAK dilaporkan -- cuma noise
    dates = ["2026-07-06", "2026-07-08"]  # 07-07 kosong, cuma 1 hari
    assert _detect_gaps(dates, "DAILY") == []


def test_detect_gaps_daily_calendar_detects_multi_day_gap():
    dates = ["2026-07-01", "2026-07-02", "2026-07-06"]  # 03-05 kosong (3 hari)
    gaps = _detect_gaps(dates, "DAILY")
    assert gaps == [{"from": "2026-07-03", "to": "2026-07-05", "days": 3}]


def test_detect_gaps_weekday_calendar_ignores_weekends():
    # Jumat -> Senin (lompat weekend) TIDAK dianggap gap utk kalender WEEKDAY
    dates = ["2026-07-03", "2026-07-06"]  # Jum'at 07-03, Senin 07-06
    assert _detect_gaps(dates, "WEEKDAY") == []


def test_detect_gaps_weekday_calendar_detects_real_gap():
    # Senin 06-29 s.d Jumat 07-10, hilang Senin 07-06 s.d Jumat 07-10 (5 hari kerja)
    dates = ["2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-13"]
    gaps = _detect_gaps(dates, "WEEKDAY")
    assert gaps == [{"from": "2026-07-06", "to": "2026-07-10", "days": 5}]


def test_detect_gaps_empty_dates_returns_empty():
    assert _detect_gaps([], "DAILY") == []


def test_instrument_source_covers_all_backfill_instruments():
    expected = {"BTC", "SP500", "IHSG", "GOLD", "USDIDR", "USDJPY",
                "DXY", "US10Y", "VIX", "WALCL", "RRP", "TGA", "HY"}
    assert set(INSTRUMENT_SOURCE) == expected
    for source, col, calendar in INSTRUMENT_SOURCE.values():
        assert source in {"asset_ohlcv", "daily_market"}
        assert (col is None) == (source == "asset_ohlcv")
        assert calendar in {"DAILY", "WEEKDAY", "WEEKLY_WED"}
