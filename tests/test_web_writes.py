"""Test web/writes.py — pure functions tulis-DB untuk Phase C (tanpa Flask)."""
from db.connection import get_connection, init_db
from web.writes import (
    flag_key_trigger,
    insert_policy_note,
    insert_prediction,
    insert_trading_journal,
    list_due_predictions,
    list_policy_notes,
    list_reading_entries,
    save_panel4,
    save_reading_entry,
    save_synthesis,
    score_prediction,
)


def _seed_news(conn, **overrides):
    defaults = {
        "date": "2026-01-01", "source": "CNBC", "headline": "Test headline",
        "raw_url": "https://x.test", "impact_level": "LOW", "is_key_trigger": 0,
    }
    defaults.update(overrides)
    cur = conn.execute(
        "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
        "is_key_trigger, created_at) VALUES (:date, :source, :headline, :raw_url, "
        ":impact_level, :is_key_trigger, '')",
        defaults,
    )
    return cur.lastrowid


# ---------- flag_key_trigger ----------

def test_flag_key_trigger_sets_flag(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        nid = _seed_news(conn)
        conn.commit()
        ok = flag_key_trigger(conn, nid, True)
        conn.commit()
        assert ok is True
        row = conn.execute("SELECT is_key_trigger FROM daily_news WHERE id=?", (nid,)).fetchone()
        assert row["is_key_trigger"] == 1


def test_flag_key_trigger_unknown_id(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert flag_key_trigger(conn, 9999) is False


# ---------- Policy Tracker ----------

def test_insert_and_list_policy_note(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        pid = insert_policy_note(
            conn, date="2026-01-01", speaker="Powell", institution="Fed",
            source_url="https://x.test", literal_statement="Rates stay higher for longer",
            stance_score=1, inference="Hawkish lean", inference_flag="TESTABLE",
            drift_note=None,
        )
        conn.commit()
        assert pid > 0
        notes = list_policy_notes(conn)
        assert len(notes) == 1
        assert notes[0]["speaker"] == "Powell"
        assert notes[0]["inference_flag"] == "TESTABLE"


# ---------- Panel 4 Reading Workspace ----------

def test_save_panel4_skips_empty_fields(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        ids = save_panel4(conn, "2026-01-01", gema="catatan gema", leon="", akela=None, rivan="catatan rivan")
        conn.commit()
        assert len(ids) == 2  # cuma gema + rivan yang terisi
        entries = list_reading_entries(conn, "2026-01-01")
        lenses = {e["lens"] for e in entries}
        assert lenses == {"GEMA", "RIVAN"}


def test_save_panel4_with_external_ai_and_conflict(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_panel4(
            conn, "2026-01-01", gema="a", leon="b", akela="c", rivan="d",
            external_ai="banding TradingAgents", conflict="GEMA vs RIVAN beda arah",
        )
        conn.commit()
        entries = list_reading_entries(conn, "2026-01-01")
        assert len(entries) == 6
        lenses = {e["lens"] for e in entries}
        assert lenses == {"GEMA", "LEON", "AKELA", "RIVAN", "EXTERNAL_AI", "CONFLICT"}


def test_save_reading_entry_single(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        rid = save_reading_entry(conn, "2026-01-01", "GEMA", "catatan singkat")
        conn.commit()
        assert rid > 0


# ---------- Panel 6: Synthesis ----------

def test_save_synthesis(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        rid = save_synthesis(conn, "2026-01-01", "Kesimpulan hari ini: bullish jangka pendek")
        conn.commit()
        assert rid is not None
        entries = list_reading_entries(conn, "2026-01-01")
        assert entries[0]["lens"] == "SYNTHESIS"


def test_save_synthesis_empty_returns_none(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert save_synthesis(conn, "2026-01-01", "   ") is None
        assert save_synthesis(conn, "2026-01-01", "") is None
        assert list_reading_entries(conn, "2026-01-01") == []


# ---------- Trading Journal ----------

def test_insert_trading_journal(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        jid = insert_trading_journal(
            conn, date="2026-01-01", instrument="BTC", setup_type="breakout/retest",
            entry_price=60000.0, sl_price=58000.0, tp1_price=65000.0,
            outcome="ONGOING", personal_notes="mengikuti sinyal id 455",
            lesson_learned=None,
        )
        conn.commit()
        row = conn.execute("SELECT * FROM trading_journal WHERE id=?", (jid,)).fetchone()
        assert row["instrument"] == "BTC"
        assert row["outcome"] == "ONGOING"


# ---------- Prediction Log ----------

def test_insert_prediction_and_list_due(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        pid = insert_prediction(
            conn, date_made="2026-01-01", horizon="1w", claim="BTC tembus 70k",
            confidence=60, basis="net liquidity naik", target_date="2026-01-08",
        )
        conn.commit()

        # belum due (as_of sebelum target_date)
        assert list_due_predictions(conn, "2026-01-05") == []

        # sudah due (as_of >= target_date, outcome masih NULL)
        due = list_due_predictions(conn, "2026-01-08")
        assert len(due) == 1
        assert due[0]["id"] == pid


def test_score_prediction(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        pid = insert_prediction(
            conn, date_made="2026-01-01", horizon="1w", claim="BTC tembus 70k",
            confidence=60, basis="net liquidity naik", target_date="2026-01-08",
        )
        conn.commit()
        ok = score_prediction(conn, pid, "BENAR", lesson="Prediksi tepat, momentum kuat")
        conn.commit()
        assert ok is True

        row = conn.execute("SELECT outcome, lesson FROM prediction_log WHERE id=?", (pid,)).fetchone()
        assert row["outcome"] == "BENAR"
        assert row["lesson"] == "Prediksi tepat, momentum kuat"

        # setelah di-skor, tidak muncul lagi di list_due_predictions
        assert list_due_predictions(conn, "2026-01-08") == []


def test_score_prediction_unknown_id(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert score_prediction(conn, 9999, "BENAR") is False
