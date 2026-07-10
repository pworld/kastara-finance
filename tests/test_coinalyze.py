"""Test Coinalyze scraper. Butuh network + COINALYZE_API_KEY (live API).
Skip kalau key kosong/API down (pola sama tests/test_crypto.py)."""
import db.connection  # noqa: F401 -- trigger load_dotenv() sebelum import scraper
import pytest

from scrapers.coinalyze import fetch_coinalyze

EXPECTED_KEYS = {
    "btc_oi_aggregate", "btc_long_short_ratio",
    "btc_liq_long_24h", "btc_liq_short_24h",
}


@pytest.fixture(scope="module")
def coinalyze():
    return fetch_coinalyze()


def test_returns_dict_with_all_keys(coinalyze):
    assert isinstance(coinalyze, dict)
    for k in EXPECTED_KEYS:
        assert k in coinalyze, f"kolom {k} hilang"
    assert "source_flags" in coinalyze


def test_no_crash_on_failure(coinalyze):
    # fetch_coinalyze tidak boleh melempar; selalu ada source_flags dict
    assert isinstance(coinalyze["source_flags"], dict)


def test_oi_aggregate_positive(coinalyze):
    oi = coinalyze["btc_oi_aggregate"]
    if oi is not None:  # bisa None kalau key kosong/API down
        assert oi > 0


def test_liquidation_long_short_separate(coinalyze):
    # long dan short HARUS field terpisah (bukan 1 angka gabungan) --
    # RIVAN persona butuh baca komposisi pergerakan.
    long_liq = coinalyze["btc_liq_long_24h"]
    short_liq = coinalyze["btc_liq_short_24h"]
    if long_liq is not None and short_liq is not None:
        assert long_liq >= 0
        assert short_liq >= 0


def test_long_short_ratio_sane_range(coinalyze):
    ratio = coinalyze["btc_long_short_ratio"]
    if ratio is not None:
        # rasio long/short historis wajar di rentang ini, bukan validasi ketat
        assert 0 < ratio < 10
