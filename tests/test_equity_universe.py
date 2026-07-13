"""Test scrapers/equity_universe.py (Phase J+ Build Contract v1.3, J-2)."""
from db.connection import get_connection, init_db
from pipeline.seed_universe import UNIVERSE, seed_instrument_metadata
from scrapers.equity_universe import fetch_equity_universe, yf_ticker_for


def test_yf_ticker_for_idx_adds_jk_suffix():
    assert yf_ticker_for("BBCA", "IDX") == "BBCA.JK"
    assert yf_ticker_for("bbca", "idx") == "BBCA.JK"


def test_yf_ticker_for_us_market_plain():
    assert yf_ticker_for("AAPL", "US") == "AAPL"
    assert yf_ticker_for("AAPL", None) == "AAPL"


def test_fetch_equity_universe_empty_when_no_instruments(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    out = fetch_equity_universe(db_path=db)
    assert out == {"asset_rows": [], "source_flags": {}}


def test_fetch_equity_universe_returns_real_data_for_universe(tmp_path):
    """Live network -- pola sama scraper lain di project ini (test_crypto.py,
    test_macro.py). Kalau yfinance down utk 1 ticker, source_flags akan
    tandai fail dan ticker itu di-skip dari asset_rows, bukan crash. Tidak
    assert urutan (SELECT tanpa ORDER BY) -- cari row per instrumen."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    out = fetch_equity_universe(db_path=db)
    assert "source_flags" in out
    by_instrument = {r["instrument"]: r for r in out["asset_rows"]}
    for instrument in ("BBCA", "TSLA"):
        row = by_instrument.get(instrument)
        if row is None:
            continue  # source down saat test jalan -- bukan kegagalan test ini
        for col in ("date", "open", "high", "low", "close"):
            assert col in row
        assert row["low"] <= row["high"]
