"""Test pipeline/backfill_earnings.py (Phase J+ Build Contract v1.3, J-7)."""
from db.connection import get_connection, init_db
from pipeline.backfill_earnings import backfill_earnings, upsert_earnings_calendar
from pipeline.seed_universe import UNIVERSE, seed_instrument_metadata


def test_upsert_earnings_calendar_inserts_rows(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        n = upsert_earnings_calendar(conn, "TSLA", [
            {"earnings_date": "2026-07-22", "eps_forecast": 0.5,
             "eps_actual": None, "event_type": "EARNINGS"},
        ])
        conn.commit()
        assert n == 1
        row = conn.execute(
            "SELECT * FROM earnings_calendar WHERE instrument='TSLA'"
        ).fetchone()
        assert row["eps_forecast"] == 0.5
        assert row["eps_actual"] is None


def test_upsert_earnings_calendar_updates_on_conflict(tmp_path):
    """Simulasi: earnings belum rilis (actual NULL) -> setelah rilis,
    re-run mengisi eps_actual (bukan duplikat baris baru)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        upsert_earnings_calendar(conn, "TSLA", [
            {"earnings_date": "2026-07-22", "eps_forecast": 0.5,
             "eps_actual": None, "event_type": "EARNINGS"},
        ])
        conn.commit()
        upsert_earnings_calendar(conn, "TSLA", [
            {"earnings_date": "2026-07-22", "eps_forecast": 0.5,
             "eps_actual": 0.55, "event_type": "EARNINGS"},
        ])
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) c FROM earnings_calendar WHERE instrument='TSLA'"
        ).fetchone()["c"]
        assert count == 1
        row = conn.execute(
            "SELECT eps_actual FROM earnings_calendar WHERE instrument='TSLA'"
        ).fetchone()
        assert row["eps_actual"] == 0.55


def test_backfill_earnings_live_for_tsla(tmp_path):
    """Live network -- pola sama scraper lain di project ini."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    summary = backfill_earnings(instrument="TSLA", db_path=db)
    assert "TSLA" in summary
    with get_connection(db) as conn:
        rows = conn.execute("SELECT * FROM earnings_calendar WHERE instrument='TSLA'").fetchall()
    if summary["TSLA"]["rows"] > 0:
        assert len(rows) == summary["TSLA"]["rows"]


def test_backfill_earnings_all_instruments(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    summary = backfill_earnings(db_path=db)
    assert set(summary.keys()) == {e["instrument"] for e in UNIVERSE}
