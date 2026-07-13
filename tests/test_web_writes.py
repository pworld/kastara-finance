"""Test web/writes.py — pure functions tulis-DB untuk Phase C (tanpa Flask)."""
from db.connection import get_connection, init_db
from web.writes import (
    compute_disonansi,
    flag_key_trigger,
    get_instrument_meta,
    insert_expectation,
    insert_policy_note,
    insert_positioning_manual,
    insert_prediction,
    insert_trading_journal,
    latest_synthesis,
    list_due_predictions,
    list_expectations,
    list_outlook,
    list_policy_notes,
    list_positioning,
    list_predictions,
    list_reading_entries,
    list_intake_log,
    list_reading_history,
    list_synthesis_log,
    list_trading_journal,
    list_universe,
    save_intake_decision,
    save_intake_metadata,
    save_outlook,
    save_panel4,
    save_persona_analysis,
    save_reading_entry,
    save_synthesis,
    score_prediction,
    set_econ_actual,
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


# ---------- Economic Calendar actual ----------

def _seed_econ_event(conn, **overrides):
    defaults = {
        "event_date": "2026-01-01", "event_time": "20:30", "event_name": "CPI m/m",
        "country": "US", "importance": "HIGH", "forecast": "2.5%", "previous": "2.4%",
        "actual": None,
    }
    defaults.update(overrides)
    cur = conn.execute(
        "INSERT INTO econ_calendar (event_date, event_time, event_name, country, "
        "importance, forecast, previous, actual, created_at) VALUES (:event_date, "
        ":event_time, :event_name, :country, :importance, :forecast, :previous, "
        ":actual, '')",
        defaults,
    )
    return cur.lastrowid


def test_set_econ_actual_updates_value(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        eid = _seed_econ_event(conn)
        conn.commit()
        ok = set_econ_actual(conn, eid, "3%")
        conn.commit()
        assert ok is True
        row = conn.execute("SELECT actual FROM econ_calendar WHERE id=?", (eid,)).fetchone()
        assert row["actual"] == "3%"


def test_set_econ_actual_unknown_id(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert set_econ_actual(conn, 9999, "3%") is False


# ---------- Expectations (Layer B, manual) ----------

def test_insert_and_list_expectations(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        eid = insert_expectation(
            conn, date="2026-07-01", metric="cme_fedwatch_cut_prob",
            value=0.72, horizon="next_meeting", source="manual",
        )
        conn.commit()
        assert eid > 0
        rows = list_expectations(conn)
        assert len(rows) == 1
        assert rows[0]["metric"] == "cme_fedwatch_cut_prob"
        assert rows[0]["value"] == 0.72


# ---------- Positioning (Layer C, manual/override) ----------

def test_insert_positioning_manual_then_list(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_positioning_manual(
            conn, date="2026-07-01", instrument="SBN", metric="sbn_foreign_flow",
            value=-1500.0, source="manual_djppr",
        )
        conn.commit()
        rows = list_positioning(conn)
        assert len(rows) == 1
        assert rows[0]["instrument"] == "SBN"
        assert rows[0]["value"] == -1500.0


def test_insert_positioning_manual_overrides_existing_row(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_positioning_manual(
            conn, date="2026-07-01", instrument="BTC", metric="etf_net_flow",
            value=100.0, source="farside_btc_etf",
        )
        conn.commit()
        # koreksi manual atas row hasil scrape yang sama (date+instrument+metric)
        insert_positioning_manual(
            conn, date="2026-07-01", instrument="BTC", metric="etf_net_flow",
            value=123.4, source="manual",
        )
        conn.commit()
        rows = list_positioning(conn)
        assert len(rows) == 1
        assert rows[0]["value"] == 123.4
        assert rows[0]["source"] == "manual"


# ---------- Disonansi Flag ----------

def _seed_disonansi(conn, stance_score, dxy_values):
    conn.execute(
        "INSERT INTO policy_tracker (date, speaker, stance_score, created_at) "
        "VALUES ('2026-07-05', 'Powell', ?, '')", (stance_score,),
    )
    for i, (date, value) in enumerate(dxy_values):
        insert_positioning_manual(
            conn, date=date, instrument="DXY", metric="cot_net_long",
            value=value, source="cftc_cot",
        )


def test_compute_disonansi_insufficient_data(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        result = compute_disonansi(conn)
        assert result == {"available": False}


def test_compute_disonansi_flagged_when_signs_disagree(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        # hawkish stance TAPI DXY net-long malah TURUN -> disonansi
        _seed_disonansi(conn, stance_score=2, dxy_values=[("2026-06-23", 20000.0), ("2026-06-30", 15000.0)])
        conn.commit()
        result = compute_disonansi(conn)
        assert result["available"] is True
        assert result["flagged"] is True


def test_compute_disonansi_not_flagged_when_signs_agree(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        # hawkish stance DAN DXY net-long naik -> searah, tidak disonansi
        _seed_disonansi(conn, stance_score=2, dxy_values=[("2026-06-23", 15000.0), ("2026-06-30", 20000.0)])
        conn.commit()
        result = compute_disonansi(conn)
        assert result["available"] is True
        assert result["flagged"] is False


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


def test_save_persona_analysis_upserts_same_day(tmp_path):
    """Re-run persona yang sama di hari yang sama harus OVERWRITE, bukan
    numpuk duplikat (beda dari SYNTHESIS yang sengaja append-only)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_persona_analysis(conn, "2026-01-01", "GEMA", "analisa versi 1")
        save_persona_analysis(conn, "2026-01-01", "GEMA", "analisa versi 2")
        conn.commit()
        entries = list_reading_entries(conn, "2026-01-01")
        gema_entries = [e for e in entries if e["lens"] == "GEMA"]
        assert len(gema_entries) == 1
        assert gema_entries[0]["notes"] == "analisa versi 2"


def test_save_persona_analysis_isolated_per_lens(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_persona_analysis(conn, "2026-01-01", "GEMA", "analisa gema")
        save_persona_analysis(conn, "2026-01-01", "LEON", "analisa leon")
        conn.commit()
        entries = list_reading_entries(conn, "2026-01-01")
        by_lens = {e["lens"]: e["notes"] for e in entries}
        assert by_lens == {"GEMA": "analisa gema", "LEON": "analisa leon"}


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


# ---------- Panel 6: Outlook persistence (reuse reading_workspace) ----------

def test_save_and_list_outlook(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_outlook(conn, "2026-01-01", "BTC", "Bullish")
        save_outlook(conn, "2026-01-01", "GOLD", "Bearish")
        conn.commit()
        result = list_outlook(conn, "2026-01-01")
        assert result == {"BTC": "Bullish", "GOLD": "Bearish"}


def test_save_outlook_upsert_overwrites_same_instrument(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_outlook(conn, "2026-01-01", "BTC", "Neutral")
        save_outlook(conn, "2026-01-01", "BTC", "Bullish")  # ganti stance hari sama
        conn.commit()
        assert list_outlook(conn, "2026-01-01") == {"BTC": "Bullish"}
        # cuma 1 baris, bukan 2
        n = conn.execute(
            "SELECT COUNT(*) c FROM reading_workspace WHERE lens='OUTLOOK:BTC'"
        ).fetchone()["c"]
        assert n == 1


def test_outlook_not_leaking_into_reading_entries_view(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_reading_entry(conn, "2026-01-01", "GEMA", "analisa makro")
        save_outlook(conn, "2026-01-01", "BTC", "Bullish")
        save_synthesis(conn, "2026-01-01", "kesimpulan hari ini")
        conn.commit()
        # list_reading_entries mengembalikan SEMUA (view Panel 4 memfilter di FE),
        # tapi list_reading_history HARUS mengecualikan SYNTHESIS & OUTLOOK:*.
        hist = list_reading_history(conn)
        lenses = {r["lens"] for r in hist}
        assert lenses == {"GEMA"}


# ---------- Panel 6/7: synthesis latest + log ----------

def test_latest_synthesis_returns_most_recent(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_synthesis(conn, "2026-01-01", "revisi pertama")
        save_synthesis(conn, "2026-01-01", "revisi kedua (final)")
        conn.commit()
        assert latest_synthesis(conn, "2026-01-01") == "revisi kedua (final)"
        assert latest_synthesis(conn, "2026-01-02") is None


def test_list_synthesis_log_newest_first_only_synthesis(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_synthesis(conn, "2026-01-01", "hari pertama")
        save_synthesis(conn, "2026-01-03", "hari ketiga")
        save_reading_entry(conn, "2026-01-02", "GEMA", "bukan synthesis")
        conn.commit()
        log = list_synthesis_log(conn)
        assert [r["date"] for r in log] == ["2026-01-03", "2026-01-01"]
        assert all("notes" in r and "created_at" in r for r in log)


# ---------- Panel 7: predictions + journal history ----------

def test_list_predictions_returns_all(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_prediction(conn, date_made="2026-01-01", horizon="1w", claim="a",
                          confidence=50, basis="x", target_date="2026-01-08")
        insert_prediction(conn, date_made="2026-01-05", horizon="1m", claim="b",
                          confidence=70, basis="y", target_date="2026-02-05")
        conn.commit()
        rows = list_predictions(conn)
        assert len(rows) == 2
        assert rows[0]["date_made"] == "2026-01-05"  # newest first


def test_list_trading_journal_returns_all(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_trading_journal(conn, date="2026-01-01", instrument="BTC", setup_type="breakout",
                               entry_price=1, sl_price=1, tp1_price=1, outcome="WIN",
                               personal_notes=None, lesson_learned=None)
        insert_trading_journal(conn, date="2026-01-04", instrument="GOLD", setup_type="retest",
                               entry_price=1, sl_price=1, tp1_price=1, outcome="LOSS",
                               personal_notes=None, lesson_learned=None)
        conn.commit()
        rows = list_trading_journal(conn)
        assert len(rows) == 2
        assert rows[0]["date"] == "2026-01-04"  # newest first


# ---------- Panel 8: Universe & Grader (Phase J+ Build Contract v1.3 §19) ----------

def test_save_intake_metadata_rejects_trade_lane(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for bad_lane in ("TRADE", "BOTH"):
            try:
                save_intake_metadata(conn, instrument="BBRI", market="IDX", lane=bad_lane)
                assert False, f"lane {bad_lane} seharusnya ditolak"
            except ValueError as exc:
                assert "tidak diizinkan" in str(exc)


def test_save_intake_metadata_inserts_with_invest_lane(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        row = save_intake_metadata(
            conn, instrument="bbri", market="idx", sector="Financial Services",
            market_cap=500_000_000_000.0, free_float=40.0, lot_size=100,
            is_financial=True, has_daily_limit=True,
        )
        conn.commit()
        assert row["instrument"] == "BBRI"
        assert row["market"] == "IDX"
        assert row["lane"] == "INVEST"
        assert row["lane_validated_at"] is None
        stored = conn.execute(
            "SELECT * FROM instrument_metadata WHERE instrument = 'BBRI'"
        ).fetchone()
        assert stored["is_financial"] == 1
        assert stored["has_daily_limit"] == 1
        assert stored["lot_size"] == 100


def test_save_intake_metadata_idempotent_upsert(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBRI", market="IDX")
        conn.commit()
        save_intake_metadata(conn, instrument="BBRI", market="IDX", sector="Updated Sector")
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) c FROM instrument_metadata WHERE instrument = 'BBRI'"
        ).fetchone()["c"]
        assert count == 1


def test_list_universe_joins_latest_grade(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBRI", market="IDX", sector="Banks")
        conn.commit()
        conn.execute(
            "INSERT INTO emiten_grade (instrument, graded_at, fund_score, integrity_flags, "
            "quadrant, created_at) VALUES ('BBRI', '2026-01-01', 60, '[]', 'WATCH', '')"
        )
        conn.execute(
            "INSERT INTO emiten_grade (instrument, graded_at, fund_score, integrity_flags, "
            "quadrant, created_at) VALUES ('BBRI', '2026-02-01', 75, '[\"UMA_ACTIVE\"]', "
            "'INVESTABLE', '')"
        )
        conn.commit()
        rows = list_universe(conn)
        assert len(rows) == 1
        assert rows[0]["instrument"] == "BBRI"
        assert rows[0]["quadrant"] == "INVESTABLE"  # grade TERBARU, bukan yang pertama
        assert rows[0]["fund_score"] == 75


def test_list_universe_no_grade_yet(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBRI", market="IDX")
        conn.commit()
        rows = list_universe(conn)
        assert rows[0]["quadrant"] is None
        assert rows[0]["fund_score"] is None


def test_get_instrument_meta_found_and_missing(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBRI", market="IDX")
        conn.commit()
        assert get_instrument_meta(conn, "bbri")["lane"] == "INVEST"
        assert get_instrument_meta(conn, "BTC") is None


# ---------- Panel 8 Komponen C Gelombang 2: Intake decision (Phase J+ §19.3/§16) ----------

def test_save_intake_decision_requires_reason(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            save_intake_decision(conn, instrument="BBRI", decision="UNIVERSE", reason="")
            assert False, "reason kosong seharusnya ditolak"
        except ValueError as exc:
            assert "reason" in str(exc)


def test_save_intake_decision_rejects_unknown_decision(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            save_intake_decision(conn, instrument="BBRI", decision="MAYBE", reason="alasan valid")
            assert False, "decision tidak dikenal seharusnya ditolak"
        except ValueError as exc:
            assert "tidak dikenal" in str(exc)


def test_save_intake_decision_inserts_and_lists(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        new_id = save_intake_decision(
            conn, instrument="bbri", decision="watchlist", reason="Fundamental oke, tunggu bar-replay",
            grade_snapshot={"fund_score": 75.0, "quadrant": "WATCH"},
        )
        conn.commit()
        assert new_id is not None
        rows = list_intake_log(conn)
        assert len(rows) == 1
        assert rows[0]["instrument"] == "BBRI"
        assert rows[0]["decision"] == "WATCHLIST"
        assert rows[0]["reason"] == "Fundamental oke, tunggu bar-replay"
        assert "fund_score" in rows[0]["grade_snapshot"]
