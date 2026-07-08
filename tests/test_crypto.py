"""Test crypto scraper. Butuh network (live API). Skip kalau semua source fail."""
import pytest

from scrapers.crypto import fetch_btc

EXPECTED_KEYS = {
    "btc_open", "btc_high", "btc_low", "btc_close", "btc_volume",
    "btc_dominance", "btc_funding_rate", "btc_oi",
    "fear_greed_value", "fear_greed_label",
}


@pytest.fixture(scope="module")
def btc():
    return fetch_btc()


def test_returns_dict_with_all_keys(btc):
    assert isinstance(btc, dict)
    for k in EXPECTED_KEYS:
        assert k in btc, f"kolom {k} hilang"
    assert "source_flags" in btc


def test_no_crash_on_failure(btc):
    # fetch_btc tidak boleh melempar; selalu ada source_flags dict
    assert isinstance(btc["source_flags"], dict)


def test_fear_greed_range(btc):
    val = btc["fear_greed_value"]
    if val is not None:  # bisa None kalau API down
        assert 0 <= val <= 100


def test_funding_rate_is_decimal(btc):
    fr = btc["btc_funding_rate"]
    if fr is not None:
        # funding rate desimal kecil, bukan persen (mis. 0.0001 bukan 0.01%)
        assert abs(fr) < 1, f"funding rate terlihat seperti persen: {fr}"


def test_ohlc_sane(btc):
    if btc["btc_close"] is not None:
        assert btc["btc_low"] <= btc["btc_high"]
        assert btc["btc_close"] > 0
