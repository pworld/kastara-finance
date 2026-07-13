"""Test pipeline/run_grader.py (Phase J+ Build Contract v1.3, J-11)."""
from db.connection import get_connection, init_db
from pipeline.backfill_fundamentals import backfill_fundamentals
from pipeline.run_grader import log_grade_change, run_grader, upsert_grade
from pipeline.seed_universe import UNIVERSE, seed_instrument_metadata


def test_upsert_grade_inserts_row(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        upsert_grade(conn, "BBCA", "2026-07-13", {
            "fund_score": 75.0, "integrity_flags": ["LOW_CONFIDENCE_FUNDAMENTALS"],
            "quadrant": "WATCH",
        })
        conn.commit()
        row = conn.execute("SELECT * FROM emiten_grade WHERE instrument='BBCA'").fetchone()
        assert row["fund_score"] == 75.0
        assert row["quadrant"] == "WATCH"
        assert "LOW_CONFIDENCE_FUNDAMENTALS" in row["integrity_flags"]


def test_log_grade_change_records_transition(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        log_grade_change(conn, "BBCA", "2026-07-13", None, "INVESTABLE", "initial grade")
        conn.commit()
        row = conn.execute("SELECT * FROM grader_log WHERE instrument='BBCA'").fetchone()
        assert row["old_grade"] is None
        assert row["new_grade"] == "INVESTABLE"


def test_run_grader_logs_only_on_quadrant_change(tmp_path):
    """Anti-overtuning (kontrak §16): grader_log HANYA nambah entry kalau
    kuadran berubah, bukan tiap kali run_grader dipanggil."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    backfill_fundamentals(db_path=db)  # live network, isi fundamentals_quarterly dulu

    run_grader(db_path=db)  # run pertama -> initial grade utk tiap instrumen
    with get_connection(db) as conn:
        log_count_1 = conn.execute("SELECT COUNT(*) c FROM grader_log").fetchone()["c"]

    run_grader(db_path=db)  # run kedua, data sama -> kuadran seharusnya SAMA
    with get_connection(db) as conn:
        log_count_2 = conn.execute("SELECT COUNT(*) c FROM grader_log").fetchone()["c"]
        grade_count = conn.execute("SELECT COUNT(*) c FROM emiten_grade").fetchone()["c"]

    assert log_count_1 == len(UNIVERSE)  # 1 entry log per instrumen (initial)
    assert log_count_2 == log_count_1  # run kedua TIDAK nambah log (kuadran tidak berubah)
    assert grade_count == 2 * len(UNIVERSE)  # emiten_grade tetap APPEND tiap run (histori grade)


def test_run_grader_single_instrument(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    backfill_fundamentals(instrument="BBCA", db_path=db)
    summary = run_grader(instrument="BBCA", db_path=db)
    assert set(summary.keys()) == {"BBCA"}
    assert summary["BBCA"]["quadrant"] in ("INVESTABLE", "WATCH", "SPECULATIVE", "AVOID")
