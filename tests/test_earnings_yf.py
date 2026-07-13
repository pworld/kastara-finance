"""Test scrapers/earnings_yf.py (Phase J+ Build Contract v1.3, J-7)."""
import pytest

from scrapers.earnings_yf import fetch_earnings_calendar


@pytest.fixture(scope="module")
def tsla_earnings():
    return fetch_earnings_calendar("TSLA", "US")


@pytest.fixture(scope="module")
def bbca_earnings():
    return fetch_earnings_calendar("BBCA", "IDX")


def test_returns_structure(tsla_earnings):
    assert "rows" in tsla_earnings
    assert "source_flags" in tsla_earnings
    assert isinstance(tsla_earnings["source_flags"], dict)


def test_rows_have_columns(tsla_earnings):
    for row in tsla_earnings["rows"]:
        for col in ("earnings_date", "eps_forecast", "eps_actual", "event_type"):
            assert col in row
        assert row["event_type"] == "EARNINGS"


def test_has_future_earnings_with_null_actual(tsla_earnings):
    """Setidaknya 1 baris earnings BELUM rilis (eps_actual None) --
    itulah baris yang dipakai rule SOP no-hold-through-earnings."""
    rows = tsla_earnings["rows"]
    if rows:
        assert any(r["eps_actual"] is None for r in rows)


def test_has_past_earnings_with_reported_actual(tsla_earnings):
    rows = tsla_earnings["rows"]
    if rows:
        assert any(r["eps_actual"] is not None for r in rows)


def test_bbca_also_works(bbca_earnings):
    for row in bbca_earnings["rows"]:
        assert "earnings_date" in row
