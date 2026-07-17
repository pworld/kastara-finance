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


# ---------- FRED staleness (ketemu 17 Jul 2026: DXY/US10Y/VIX kelihatan
# "kosong" -- ternyata fetch sukses tapi observasi FRED-nya basi berhari-
# hari, source_flags lama tidak bedakan itu dari data fresh). Live-test
# TIDAK bisa mengontrol seberapa basi data FRED beneran hari ini secara
# deterministik -- monkeypatch di sini, pola sama pengecualian
# tests/test_notify_telegram.py (operasi yang perlu skenario terkontrol,
# bukan default "test scraper pakai network asli"). ----------
def test_fred_flags_stale_when_observation_too_old(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "dummy-key-for-test")

    def fake_fetch_series(series_id, api_key, n=2):
        # DXY basi 7 hari (> MAX_LAG_DAYS["dxy"]=4), lainnya fresh (1 hari).
        if series_id == "DTWEXBGS":
            return [{"date": "2026-07-10", "value": 120.5046}, {"date": "2026-07-09", "value": 120.753}]
        return [{"date": "2026-07-16", "value": 4.55}, {"date": "2026-07-15", "value": 4.58}]

    monkeypatch.setattr("scrapers.macro_fred._fetch_series", fake_fetch_series)
    out = fetch_macro_fred("2026-07-17")

    assert out["source_flags"]["fred_dxy"] == "stale"
    assert out["dxy_close"] == 120.5046  # value TETAP ditulis meski basi
    assert out["source_flags"]["fred_us10y"] == "ok"  # 1 hari lag, dalam batas wajar


def test_fred_flags_ok_when_observation_recent(monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "dummy-key-for-test")

    def fake_fetch_series(series_id, api_key, n=2):
        return [{"date": "2026-07-16", "value": 15.67}, {"date": "2026-07-15", "value": 16.5}]

    monkeypatch.setattr("scrapers.macro_fred._fetch_series", fake_fetch_series)
    out = fetch_macro_fred("2026-07-17")

    for label in ("fred_dxy", "fred_us10y", "fred_vix", "fred_walcl", "fred_rrp", "fred_tga", "fred_hy_spread"):
        assert out["source_flags"][label] == "ok"
