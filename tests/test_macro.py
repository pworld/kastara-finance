"""Test macro scrapers (yfinance + FRED). Tes news scraper ada di test_news.py."""
import pytest

from scrapers.macro_yf import fetch_macro_yf
from scrapers.macro_fred import fetch_macro_fred


# ---------- yfinance ----------
@pytest.fixture(scope="module")
def yf_data():
    return fetch_macro_yf()


def test_yf_returns_structure(yf_data):
    assert isinstance(yf_data, dict)
    assert "asset_rows" in yf_data
    assert "source_flags" in yf_data
    for k in ("sp500_close", "ihsg_close", "usd_idr", "usd_jpy", "gold_close"):
        assert k in yf_data


def test_yf_asset_rows_have_columns(yf_data):
    for row in yf_data["asset_rows"]:
        for col in ("instrument", "date", "open", "high", "low", "close"):
            assert col in row
        assert row["low"] <= row["high"]


def test_yf_no_crash(yf_data):
    assert isinstance(yf_data["source_flags"], dict)


# ---------- FRED ----------
def test_fred_no_crash_without_key():
    # Tanpa FRED_API_KEY harus tetap return dict (series di-skip), bukan crash.
    out = fetch_macro_fred()
    assert isinstance(out, dict)
    assert "source_flags" in out
    for k in ("dxy_close", "us10y_yield", "vix_close", "walcl", "rrp", "tga"):
        assert k in out
