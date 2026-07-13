"""Test pipeline/backfill_fundamentals.py (Phase J+ Build Contract v1.3, J-4)."""
from db.connection import get_connection, init_db
from pipeline.backfill_fundamentals import backfill_fundamentals, upsert_fundamentals_quarterly
from pipeline.seed_universe import UNIVERSE, seed_instrument_metadata


def test_upsert_fundamentals_quarterly_inserts_rows(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        n = upsert_fundamentals_quarterly(conn, "BBCA", [
            {"quarter_end": "2026-03-31", "revenue": 100.0, "net_income": 20.0,
             "eps": 1.5, "net_interest_income": 50.0, "total_equity": 500.0,
             "total_assets": 1000.0, "operating_cash_flow": 30.0,
             "free_cash_flow": 25.0, "confidence": "LOW_CONFIDENCE"},
        ])
        conn.commit()
        assert n == 1
        row = conn.execute(
            "SELECT * FROM fundamentals_quarterly WHERE instrument='BBCA'"
        ).fetchone()
        assert row["revenue"] == 100.0
        assert row["confidence"] == "LOW_CONFIDENCE"
        assert row["source"] == "yfinance"


def test_upsert_fundamentals_quarterly_updates_on_conflict(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        upsert_fundamentals_quarterly(conn, "BBCA", [
            {"quarter_end": "2026-03-31", "revenue": 100.0, "net_income": 20.0,
             "eps": None, "net_interest_income": None, "total_equity": None,
             "total_assets": None, "operating_cash_flow": None,
             "free_cash_flow": None, "confidence": "LOW_CONFIDENCE"},
        ])
        conn.commit()
        upsert_fundamentals_quarterly(conn, "BBCA", [
            {"quarter_end": "2026-03-31", "revenue": 999.0, "net_income": 20.0,
             "eps": None, "net_interest_income": None, "total_equity": None,
             "total_assets": None, "operating_cash_flow": None,
             "free_cash_flow": None, "confidence": "LOW_CONFIDENCE"},
        ])
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) c FROM fundamentals_quarterly WHERE instrument='BBCA'"
        ).fetchone()["c"]
        assert count == 1  # bukan duplikat baris baru
        row = conn.execute(
            "SELECT revenue FROM fundamentals_quarterly WHERE instrument='BBCA'"
        ).fetchone()
        assert row["revenue"] == 999.0  # ter-update


def test_backfill_fundamentals_live_for_bbca(tmp_path):
    """Live network -- pola sama scraper lain di project ini."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    summary = backfill_fundamentals(instrument="BBCA", db_path=db)
    assert "BBCA" in summary
    with get_connection(db) as conn:
        rows = conn.execute(
            "SELECT * FROM fundamentals_quarterly WHERE instrument='BBCA'"
        ).fetchall()
    if summary["BBCA"]["quarters"] > 0:
        assert len(rows) == summary["BBCA"]["quarters"]
        assert all(r["source"] == "yfinance" for r in rows)


def test_backfill_fundamentals_all_instruments(tmp_path):
    """Tanpa --instrument -> proses SEMUA yang ada di instrument_metadata."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    summary = backfill_fundamentals(db_path=db)
    assert set(summary.keys()) == {e["instrument"] for e in UNIVERSE}
