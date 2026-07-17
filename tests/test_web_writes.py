"""Test web/writes.py — pure functions tulis-DB untuk Phase C (tanpa Flask)."""
import json
from datetime import datetime, timedelta

from scrapers.base import today_wib
from db.connection import get_connection, init_db


def _date_shift(date_str: str, days: int) -> str:
    """Geser 'YYYY-MM-DD' sekian hari (dipakai seed test earnings window)."""
    return (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")
from web.writes import (
    compute_disonansi,
    set_for_reading,
    set_display_subtitle,
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
    get_emiten_detail,
    list_bank_ratios,
    list_grader_log,
    list_intake_log,
    list_lane_validation_log,
    list_reading_history,
    list_synthesis_log,
    list_trading_journal,
    list_universe,
    save_bank_ratios_manual,
    save_grade_override,
    save_grader_outcome,
    save_intake_decision,
    save_intake_metadata,
    save_outlook,
    save_panel4,
    save_persona_analysis,
    save_reading_entry,
    save_synthesis,
    score_prediction,
    validate_lane,
    set_econ_actual,
    list_earnings_calendar,
    list_earnings_warnings,
    save_thread,
    patch_thread,
    list_threads,
    get_thread,
    suggest_thread_links,
    confirm_thread_link,
    reject_thread_link,
    add_thread_link_manual,
    list_thread_links,
    attach_thread_suggestions,
    create_tag,
    list_tags,
    resolve_tag,
    apply_tag,
    remove_tag,
    list_content_tags,
    attach_content_tags,
    update_tag,
    delete_tag,
    merge_tag,
    list_orphan_tags,
    thread_stats,
    list_threads_with_stats,
    suggest_tags_for_news,
    auto_dormant_stale_threads,
)


def _seed_news(conn, **overrides):
    defaults = {
        "date": "2026-01-01", "source": "CNBC", "headline": "Test headline",
        "raw_url": "https://x.test", "impact_level": "LOW", "for_reading": 0,
    }
    defaults.update(overrides)
    cur = conn.execute(
        "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
        "for_reading, created_at) VALUES (:date, :source, :headline, :raw_url, "
        ":impact_level, :for_reading, '')",
        defaults,
    )
    return cur.lastrowid


# ---------- set_for_reading / set_display_subtitle (Addendum C §21.2, renamed dari flag_key_trigger) ----------

def test_set_for_reading_sets_flag(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        nid = _seed_news(conn)
        conn.commit()
        ok = set_for_reading(conn, nid, True)
        conn.commit()
        assert ok is True
        row = conn.execute("SELECT for_reading FROM daily_news WHERE id=?", (nid,)).fetchone()
        assert row["for_reading"] == 1


def test_set_for_reading_unknown_id(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert set_for_reading(conn, 9999) is False


def test_set_display_subtitle_updates_and_keeps_headline_intact(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        nid = _seed_news(conn, headline="Original headline asli")
        conn.commit()
        ok = set_display_subtitle(conn, nid, "Catatan Giel di sini")
        conn.commit()
        assert ok is True
        row = conn.execute(
            "SELECT headline, display_subtitle FROM daily_news WHERE id=?", (nid,)
        ).fetchone()
        assert row["headline"] == "Original headline asli"  # tidak pernah ditimpa
        assert row["display_subtitle"] == "Catatan Giel di sini"


def test_set_display_subtitle_unknown_id(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert set_display_subtitle(conn, 9999, "x") is False


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


# ---------- Earnings emiten (READ-ONLY, J-15 gel.2) ----------

def _seed_meta(conn, instrument, market):
    conn.execute(
        "INSERT INTO instrument_metadata (instrument, market) VALUES (?, ?)",
        (instrument, market),
    )


def _seed_earnings(conn, instrument, earnings_date, **overrides):
    row = {"eps_forecast": 1.0, "eps_actual": None, "event_type": "EARNINGS"}
    row.update(overrides)
    conn.execute(
        "INSERT INTO earnings_calendar (instrument, earnings_date, eps_forecast, "
        "eps_actual, event_type, created_at) VALUES (?, ?, ?, ?, ?, '')",
        (instrument, earnings_date, row["eps_forecast"], row["eps_actual"], row["event_type"]),
    )


def _seed_ongoing(conn, instrument):
    conn.execute(
        "INSERT INTO trading_journal (date, instrument, outcome, created_at) "
        "VALUES ('2026-07-15', ?, 'ONGOING', '')",
        (instrument,),
    )


def test_list_earnings_calendar_window_and_market_join(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    today = today_wib()
    with get_connection(db) as conn:
        _seed_meta(conn, "TSLA", "US")
        _seed_earnings(conn, "TSLA", _date_shift(today, 5))     # upcoming -> masuk
        _seed_earnings(conn, "TSLA", _date_shift(today, -10))   # baru lewat (dalam 30d) -> masuk
        _seed_earnings(conn, "TSLA", _date_shift(today, -60))   # di luar window -> keluar
        conn.commit()
        rows = list_earnings_calendar(conn)
    dates = [r["earnings_date"] for r in rows]
    assert _date_shift(today, 5) in dates
    assert _date_shift(today, -10) in dates
    assert _date_shift(today, -60) not in dates
    assert all(r["market"] == "US" for r in rows)  # JOIN instrument_metadata


def test_list_earnings_warnings_us_hard_rule(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    today = today_wib()
    with get_connection(db) as conn:
        _seed_meta(conn, "TSLA", "US")
        _seed_ongoing(conn, "TSLA")
        _seed_earnings(conn, "TSLA", _date_shift(today, 5))
        conn.commit()
        warns = list_earnings_warnings(conn, within_days=14)
    assert len(warns) == 1
    assert warns[0]["instrument"] == "TSLA"
    assert warns[0]["hard_rule"] is True
    assert warns[0]["days_until"] == 5


def test_list_earnings_warnings_idx_soft_rule(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    today = today_wib()
    with get_connection(db) as conn:
        _seed_meta(conn, "BBCA", "IDX")
        _seed_ongoing(conn, "BBCA")
        _seed_earnings(conn, "BBCA", _date_shift(today, 5))
        conn.commit()
        warns = list_earnings_warnings(conn, within_days=14)
    assert len(warns) == 1
    assert warns[0]["hard_rule"] is False


def test_list_earnings_warnings_empty_without_open_position(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    today = today_wib()
    with get_connection(db) as conn:
        _seed_meta(conn, "TSLA", "US")
        _seed_earnings(conn, "TSLA", _date_shift(today, 5))  # ada earnings, TAPI tak ada posisi
        conn.commit()
        assert list_earnings_warnings(conn) == []


def test_list_earnings_warnings_ignores_past_and_far(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    today = today_wib()
    with get_connection(db) as conn:
        _seed_meta(conn, "TSLA", "US")
        _seed_ongoing(conn, "TSLA")
        _seed_earnings(conn, "TSLA", _date_shift(today, -3))   # sudah lewat
        _seed_earnings(conn, "TSLA", _date_shift(today, 20))   # > within_days
        conn.commit()
        assert list_earnings_warnings(conn, within_days=14) == []


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


def test_insert_trading_journal_with_sizing_fields(tmp_path):
    """Ekstensi Phase J+ §14/J-13 -- planned_size/actual_size/skip_reason/
    return ganda ccy, semua opsional (backward-compat dgn caller lama)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        jid = insert_trading_journal(
            conn, date="2026-07-13", instrument="BBCA", setup_type="retest",
            entry_price=6100.0, sl_price=6000.0, tp1_price=6300.0,
            outcome="ONGOING", personal_notes=None, lesson_learned=None,
            planned_size=2500.0, actual_size=2500.0, skip_reason=None,
            return_asset_ccy=None, return_idr=None,
        )
        conn.commit()
        row = conn.execute("SELECT * FROM trading_journal WHERE id=?", (jid,)).fetchone()
        assert row["planned_size"] == 2500.0
        assert row["actual_size"] == 2500.0
        assert row["skip_reason"] is None


def test_insert_trading_journal_skip_reason_without_size(tmp_path):
    """Sinyal SKIP (kapasitas risiko tidak cukup) -- dicatat dgn skip_reason,
    size tetap None (bukan 0, kosong ≠ nol)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        jid = insert_trading_journal(
            conn, date="2026-07-13", instrument="BBCA", setup_type="retest",
            entry_price=6100.0, sl_price=6000.0, tp1_price=6300.0,
            outcome="ONGOING", personal_notes=None, lesson_learned=None,
            skip_reason="RISK_CAPACITY_EXCEEDED",
        )
        conn.commit()
        row = conn.execute("SELECT * FROM trading_journal WHERE id=?", (jid,)).fetchone()
        assert row["skip_reason"] == "RISK_CAPACITY_EXCEEDED"
        assert row["planned_size"] is None


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


# ---------- Rasio prudential bank manual (CAR/NPL/NIM/LDR, Phase J+ §2 J7/J-6) ----------

def test_save_bank_ratios_manual_inserts_new_row(tmp_path):
    """Kuartal belum ada di fundamentals_quarterly sama sekali -- INSERT
    baris baru source='manual'."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_bank_ratios_manual(
            conn, instrument="bbca", quarter_end="2026-03-31",
            car=25.5, npl_gross=1.2, nim=5.8, ldr=78.3,
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM fundamentals_quarterly WHERE instrument='BBCA' AND quarter_end='2026-03-31'"
        ).fetchone()
        assert row["car"] == 25.5
        assert row["npl_gross"] == 1.2
        assert row["source"] == "manual"


def test_save_bank_ratios_manual_does_not_clobber_yfinance_row(tmp_path):
    """Kuartal SUDAH ada dari yfinance (revenue/net_income terisi) -- input
    manual rasio bank cuma update 4 kolom rasio, TIDAK menimpa data lain."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        conn.execute(
            "INSERT INTO fundamentals_quarterly (instrument, quarter_end, revenue, "
            "net_income, source, confidence, created_at) VALUES "
            "('BBCA', '2026-03-31', 28000000000000, 14000000000000, 'yfinance', 'LOW_CONFIDENCE', '')"
        )
        conn.commit()
        save_bank_ratios_manual(conn, instrument="BBCA", quarter_end="2026-03-31", car=25.5)
        conn.commit()
        row = conn.execute(
            "SELECT * FROM fundamentals_quarterly WHERE instrument='BBCA' AND quarter_end='2026-03-31'"
        ).fetchone()
        assert row["car"] == 25.5
        assert row["revenue"] == 28000000000000  # TIDAK ter-clobber
        assert row["source"] == "yfinance"  # source asli tetap, bukan ketimpa 'manual'


def test_list_bank_ratios_only_rows_with_ratio_filled(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        conn.execute(
            "INSERT INTO fundamentals_quarterly (instrument, quarter_end, revenue, created_at) "
            "VALUES ('BBCA', '2025-12-31', 27000000000000, '')"
        )  # kuartal lain, TANPA rasio bank -- tidak boleh muncul
        save_bank_ratios_manual(conn, instrument="BBCA", quarter_end="2026-03-31", car=25.5, ldr=78.3)
        conn.commit()
        rows = list_bank_ratios(conn, "BBCA")
        assert len(rows) == 1
        assert rows[0]["quarter_end"] == "2026-03-31"


# ---------- Panel 8 Komponen B/D: detail emiten, override, grader log (Addendum A §19.2/§19.4) ----------

def test_get_emiten_detail_unknown_instrument_returns_none(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert get_emiten_detail(conn, "ZZZZ") is None


def test_get_emiten_detail_combines_metadata_fundamentals_grade(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBRI", market="IDX", is_financial=True)
        conn.execute(
            "INSERT INTO fundamentals_quarterly (instrument, quarter_end, revenue, "
            "net_income, confidence, created_at) VALUES "
            "('BBRI', '2026-03-31', 100, 20, 'LOW_CONFIDENCE', '')"
        )
        conn.execute(
            "INSERT INTO emiten_grade (instrument, graded_at, fund_score, integrity_flags, "
            "quadrant, created_at) VALUES ('BBRI', '2026-07-13', 75, '[\"UMA_ACTIVE\"]', 'AVOID', '')"
        )
        conn.commit()
        detail = get_emiten_detail(conn, "bbri")
        assert detail["metadata"]["instrument"] == "BBRI"
        assert len(detail["fundamentals"]) == 1
        assert detail["grade"]["quadrant"] == "AVOID"
        assert detail["grade"]["integrity_flags"] == ["UMA_ACTIVE"]
        assert detail["grade"]["giel_override"] is None


def test_save_grade_override_requires_reason(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            save_grade_override(conn, "BBRI", "WATCH", "")
            assert False, "reason kosong seharusnya ditolak"
        except ValueError as exc:
            assert "reason" in str(exc)


def test_save_grade_override_rejects_unknown_quadrant(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            save_grade_override(conn, "BBRI", "MAYBE", "alasan valid")
            assert False, "quadrant tidak dikenal seharusnya ditolak"
        except ValueError as exc:
            assert "tidak dikenal" in str(exc)


def test_save_grade_override_returns_false_when_never_graded(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert save_grade_override(conn, "BBRI", "WATCH", "alasan valid") is False


def test_save_grade_override_updates_latest_grade_preserving_original(tmp_path):
    """Override TIDAK menimpa kolom `quadrant` asli (nilai mesin) --
    disimpan terpisah di `giel_override` (kontrak §19.2)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        conn.execute(
            "INSERT INTO emiten_grade (instrument, graded_at, fund_score, integrity_flags, "
            "quadrant, created_at) VALUES ('BBRI', '2026-07-13', 75, '[]', 'WATCH', '')"
        )
        conn.commit()
        ok = save_grade_override(conn, "bbri", "investable", "Giel yakin fundamental lebih kuat dari skor mesin")
        conn.commit()
        assert ok is True
        row = conn.execute("SELECT * FROM emiten_grade WHERE instrument='BBRI'").fetchone()
        assert row["quadrant"] == "WATCH"  # nilai mesin asli TIDAK berubah
        override = json.loads(row["giel_override"])
        assert override["quadrant"] == "INVESTABLE"
        assert "reason" in override


def test_validate_lane_rejects_unknown_lane(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBRI", market="IDX")
        try:
            validate_lane(conn, instrument="BBRI", new_lane="MAYBE", evidence="cek chart")
            assert False, "lane tidak dikenal seharusnya ditolak"
        except ValueError as exc:
            assert "tidak dikenal" in str(exc)


def test_validate_lane_requires_evidence(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBRI", market="IDX")
        try:
            validate_lane(conn, instrument="BBRI", new_lane="TRADE", evidence="  ")
            assert False, "evidence kosong seharusnya ditolak"
        except ValueError as exc:
            assert "evidence" in str(exc)


def test_validate_lane_returns_none_when_instrument_not_in_universe(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert validate_lane(conn, instrument="NOPE", new_lane="TRADE", evidence="cek chart") is None


def test_validate_lane_updates_metadata_and_logs_evidence(tmp_path):
    """Kontrak §13.1 poin 5: naik ke TRADE harus terekam dgn evidence, dan
    `lane_validated_at` terisi tanggal validasi -- BUKAN NULL lagi."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBCA", market="IDX", lane="INVEST")
        conn.commit()
        meta_before = get_instrument_meta(conn, "BBCA")
        assert meta_before["lane"] == "INVEST"
        assert meta_before["lane_validated_at"] is None

        result = validate_lane(
            conn, instrument="bbca", new_lane="TRADE",
            evidence="Cek 2 tahun candle historis, zona S&R konsisten, pola breakout/retest valid",
        )
        conn.commit()
        assert result["instrument"] == "BBCA"
        assert result["old_lane"] == "INVEST"
        assert result["new_lane"] == "TRADE"
        assert result["lane_validated_at"] is not None

        meta_after = get_instrument_meta(conn, "BBCA")
        assert meta_after["lane"] == "TRADE"
        assert meta_after["lane_validated_at"] == result["lane_validated_at"]

        log = list_lane_validation_log(conn, instrument="BBCA")
        assert len(log) == 1
        assert log[0]["old_lane"] == "INVEST"
        assert log[0]["new_lane"] == "TRADE"
        assert "breakout" in log[0]["evidence"]


def test_list_lane_validation_log_filters_by_instrument(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        save_intake_metadata(conn, instrument="BBCA", market="IDX")
        save_intake_metadata(conn, instrument="TSLA", market="US")
        conn.commit()
        validate_lane(conn, instrument="BBCA", new_lane="TRADE", evidence="cek chart BBCA")
        validate_lane(conn, instrument="TSLA", new_lane="TRADE", evidence="cek chart TSLA")
        conn.commit()
        assert len(list_lane_validation_log(conn)) == 2
        assert len(list_lane_validation_log(conn, instrument="BBCA")) == 1


def test_list_grader_log_filters_by_instrument(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        conn.execute(
            "INSERT INTO grader_log (instrument, date, old_grade, new_grade, reason, created_at) "
            "VALUES ('BBCA', '2026-07-01', NULL, 'WATCH', 'initial', '')"
        )
        conn.execute(
            "INSERT INTO grader_log (instrument, date, old_grade, new_grade, reason, created_at) "
            "VALUES ('TSLA', '2026-07-01', NULL, 'WATCH', 'initial', '')"
        )
        conn.commit()
        assert len(list_grader_log(conn)) == 2
        assert len(list_grader_log(conn, instrument="BBCA")) == 1


def test_save_grader_outcome_independent_3m_6m(tmp_path):
    """Isi outcome_3m TIDAK menghapus outcome_6m yang sudah ada (2 widget
    independen, diisi di waktu berbeda)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        cur = conn.execute(
            "INSERT INTO grader_log (instrument, date, old_grade, new_grade, reason, created_at) "
            "VALUES ('BBCA', '2026-01-01', NULL, 'WATCH', 'initial', '')"
        )
        log_id = cur.lastrowid
        conn.commit()
        save_grader_outcome(conn, log_id, outcome_6m="BENAR")
        conn.commit()
        save_grader_outcome(conn, log_id, outcome_3m="PARTIAL")
        conn.commit()
        row = conn.execute("SELECT * FROM grader_log WHERE id=?", (log_id,)).fetchone()
        assert row["outcome_3m"] == "PARTIAL"
        assert row["outcome_6m"] == "BENAR"  # tidak ter-hapus


def test_save_grader_outcome_unknown_id_returns_false(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert save_grader_outcome(conn, 9999, outcome_3m="BENAR") is False


# ---------- News Threads (Addendum B §20, N-1 fondasi) ----------

def _seed_news_row(conn, **overrides):
    defaults = {
        "date": "2026-07-15", "source": "CNBC", "headline": "Warsh signals hawkish stance",
        "raw_url": "https://x.test", "impact_level": "HIGH", "for_reading": 0,
    }
    defaults.update(overrides)
    cur = conn.execute(
        "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
        "for_reading, created_at) VALUES (:date, :source, :headline, :raw_url, "
        ":impact_level, :for_reading, '')",
        defaults,
    )
    return cur.lastrowid


def test_save_thread_requires_title(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            save_thread(conn, title="")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "title" in str(exc)


def test_save_thread_enforces_max_active(tmp_path):
    """Kontrak §20.1 keputusan #5: maks 7 thread ACTIVE bersamaan, ditegakkan
    di write function -- bukan cuma UI."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for i in range(7):
            save_thread(conn, title=f"Thread {i}")
        conn.commit()
        try:
            save_thread(conn, title="Thread ke-8")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "7" in str(exc)


def test_save_thread_stores_keywords_as_json(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        row = save_thread(conn, title="Rezim Warsh Hawkish", keywords=["warsh", "fed"])
        conn.commit()
        assert row["keywords"] == ["warsh", "fed"]
        assert row["status"] == "ACTIVE"
        fetched = get_thread(conn, row["id"])
        assert fetched["keywords"] == ["warsh", "fed"]


def test_save_thread_runs_catchup_scan_against_existing_news(tmp_path):
    """Ketemu 17 Jul 2026: thread baru mulai kosong krn suggest_thread_links
    cuma dipanggil run_daily dgn headline yang BARU di-fetch -- berita lama
    yang sudah ada di DB terlewat. save_thread() sekarang catch-up sekali
    saat dibuat."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_news_row(conn, headline="Warsh speaks on rates", date="2026-07-15")
        _seed_news_row(conn, headline="Unrelated tech news", date="2026-07-16")
        conn.commit()
        thread = save_thread(conn, title="Rezim Warsh", keywords=["warsh"])
        conn.commit()
        links = list_thread_links(conn, thread["id"])
        assert len(links) == 1
        assert links[0]["source_info"]["headline"] == "Warsh speaks on rates"
        assert links[0]["link_status"] == "SUGGESTED"


def test_save_thread_catchup_respects_window(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        # di luar THREAD_CATCHUP_DAYS (7 hari) dari hari ini -- tidak ke-scan
        _seed_news_row(conn, headline="Warsh old news", date="2020-01-01")
        conn.commit()
        thread = save_thread(conn, title="Rezim Warsh", keywords=["warsh"])
        conn.commit()
        assert list_thread_links(conn, thread["id"]) == []


def test_save_thread_no_catchup_without_keywords(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_news_row(conn, headline="Warsh speaks on rates")
        conn.commit()
        thread = save_thread(conn, title="Thread Tanpa Keyword")
        conn.commit()
        assert list_thread_links(conn, thread["id"]) == []


def test_patch_thread_requires_verdict_when_closing(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        row = save_thread(conn, title="Thread A")
        conn.commit()
        try:
            patch_thread(conn, row["id"], status="CLOSED")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "verdict" in str(exc)


def test_patch_thread_closes_with_verdict(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        row = save_thread(conn, title="Thread A")
        conn.commit()
        updated = patch_thread(conn, row["id"], status="CLOSED", verdict="Tesis terbukti benar")
        conn.commit()
        assert updated["status"] == "CLOSED"
        assert updated["verdict"] == "Tesis terbukti benar"


def test_patch_thread_unknown_id_returns_none(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert patch_thread(conn, 9999, current_read="x") is None


def test_patch_thread_updates_title_and_keywords(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        row = save_thread(conn, title="Thread A", keywords=["warsh"])
        conn.commit()
        updated = patch_thread(conn, row["id"], title="Thread A Renamed", keywords=["warsh", "powell"])
        conn.commit()
        assert updated["title"] == "Thread A Renamed"
        assert updated["keywords"] == ["warsh", "powell"]


def test_patch_thread_rejects_empty_title(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        row = save_thread(conn, title="Thread A")
        conn.commit()
        try:
            patch_thread(conn, row["id"], title="")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "title" in str(exc)


def test_patch_thread_keyword_change_triggers_catchup(tmp_path):
    """Ketemu 17 Jul 2026: kata kunci baru harus langsung catch-up scan
    berita yang sudah ada, bukan nunggu cron besok (pola sama save_thread)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        row = save_thread(conn, title="Thread A")  # tanpa keywords -> tidak ada catch-up awal
        _seed_news_row(conn, headline="Powell testifies before Congress")
        conn.commit()
        assert list_thread_links(conn, row["id"]) == []
        patch_thread(conn, row["id"], keywords=["powell"])
        conn.commit()
        links = list_thread_links(conn, row["id"])
        assert len(links) == 1
        assert links[0]["source_info"]["headline"] == "Powell testifies before Congress"


def test_list_threads_filters_by_status(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        a = save_thread(conn, title="Thread A")
        save_thread(conn, title="Thread B")
        conn.commit()
        patch_thread(conn, a["id"], status="CLOSED", verdict="selesai")
        conn.commit()
        assert len(list_threads(conn)) == 2
        assert len(list_threads(conn, status="ACTIVE")) == 1
        assert len(list_threads(conn, status="CLOSED")) == 1


def test_suggest_thread_links_matches_keyword_and_is_idempotent(tmp_path):
    """Auto-suggest (§20.2): keyword match -> SUGGESTED, TIDAK PERNAH
    CONFIRMED. Re-run dgn news_items sama TIDAK duplikat (idempoten via
    UNIQUE index idx_news_thread_links_dedup)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Rezim Warsh Hawkish", keywords=["warsh"])
        conn.commit()
        _seed_news_row(conn, headline="Warsh signals hawkish stance")
        _seed_news_row(conn, headline="Unrelated tech news", date="2026-07-15", source="X")
        conn.commit()
        news_items = [
            {"date": "2026-07-15", "headline": "Warsh signals hawkish stance"},
            {"date": "2026-07-15", "headline": "Unrelated tech news"},
        ]
        n1 = suggest_thread_links(conn, news_items)
        conn.commit()
        assert n1 == 1  # cuma yang match keyword
        links = list_thread_links(conn, thread["id"])
        assert len(links) == 1
        assert links[0]["link_status"] == "SUGGESTED"

        n2 = suggest_thread_links(conn, news_items)  # re-run, sama news_items
        conn.commit()
        assert n2 == 0  # idempoten, tidak duplikat
        assert len(list_thread_links(conn, thread["id"])) == 1


def test_suggest_thread_links_only_scans_active_threads(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        closed = save_thread(conn, title="Thread Lama", keywords=["warsh"])
        conn.commit()
        patch_thread(conn, closed["id"], status="CLOSED", verdict="selesai")
        conn.commit()
        _seed_news_row(conn, headline="Warsh speaks again")
        conn.commit()
        n = suggest_thread_links(conn, [{"date": "2026-07-15", "headline": "Warsh speaks again"}])
        conn.commit()
        assert n == 0  # thread CLOSED tidak ikut di-scan


def test_confirm_thread_link_requires_valid_stance(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Thread A", keywords=["warsh"])
        news_id = _seed_news_row(conn)
        conn.commit()
        suggest_thread_links(conn, [{"date": "2026-07-15", "headline": "Warsh signals hawkish stance"}])
        conn.commit()
        link_id = list_thread_links(conn, thread["id"])[0]["id"]
        try:
            confirm_thread_link(conn, link_id, "SETUJU")  # bukan salah satu dari 3 pilihan
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "stance" in str(exc)


def test_confirm_thread_link_also_for_reading_reuses_set_for_reading(tmp_path):
    """also_for_reading=True harus benar-benar set daily_news.for_reading
    lewat set_for_reading() yang sudah ada (reuse, bukan duplikat write path)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Thread A", keywords=["warsh"])
        news_id = _seed_news_row(conn)
        conn.commit()
        suggest_thread_links(conn, [{"date": "2026-07-15", "headline": "Warsh signals hawkish stance"}])
        conn.commit()
        link_id = list_thread_links(conn, thread["id"])[0]["id"]
        ok = confirm_thread_link(conn, link_id, "mendukung", also_for_reading=True)
        conn.commit()
        assert ok is True
        row = conn.execute("SELECT for_reading FROM daily_news WHERE id=?", (news_id,)).fetchone()
        assert row["for_reading"] == 1
        link = list_thread_links(conn, thread["id"])[0]
        assert link["link_status"] == "CONFIRMED"
        assert link["stance"] == "MENDUKUNG"  # dinormalisasi upper


def test_confirm_thread_link_unknown_id_returns_false(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert confirm_thread_link(conn, 9999, "MENDUKUNG") is False


def test_reject_thread_link(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Thread A", keywords=["warsh"])
        _seed_news_row(conn)
        conn.commit()
        suggest_thread_links(conn, [{"date": "2026-07-15", "headline": "Warsh signals hawkish stance"}])
        conn.commit()
        link_id = list_thread_links(conn, thread["id"])[0]["id"]
        assert reject_thread_link(conn, link_id) is True
        assert list_thread_links(conn, thread["id"], status="REJECTED")[0]["link_status"] == "REJECTED"
        assert reject_thread_link(conn, 9999) is False


def test_add_thread_link_manual_confirmed_immediately(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Thread A")
        pol_id = conn.execute(
            "INSERT INTO policy_tracker (date, speaker, institution, literal_statement, created_at) "
            "VALUES ('2026-07-14', 'Powell', 'Fed', 'Rates may stay higher for longer', '')"
        ).lastrowid
        conn.commit()
        row = add_thread_link_manual(conn, thread["id"], "policy_tracker", pol_id, "kontra", note="catatan")
        conn.commit()
        assert row["link_status"] == "CONFIRMED"
        assert row["stance"] == "KONTRA"
        links = list_thread_links(conn, thread["id"])
        assert links[0]["source_info"]["headline"] == "Rates may stay higher for longer"
        assert links[0]["source_info"]["source"] == "Powell (Fed)"


def test_add_thread_link_manual_rejects_unknown_ref_table(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Thread A")
        conn.commit()
        try:
            add_thread_link_manual(conn, thread["id"], "some_other_table", 1, "MENDUKUNG")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "ref_table" in str(exc)


def test_add_thread_link_manual_rejects_duplicate(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Thread A")
        news_id = _seed_news_row(conn)
        conn.commit()
        add_thread_link_manual(conn, thread["id"], "daily_news", news_id, "MENDUKUNG")
        conn.commit()
        try:
            add_thread_link_manual(conn, thread["id"], "daily_news", news_id, "KONTRA")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "sudah ada" in str(exc)


def test_list_thread_links_joins_daily_news_and_manual_articles(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Thread A")
        news_id = _seed_news_row(conn)
        art_id = conn.execute(
            "INSERT INTO manual_articles (date, source, url, headline, created_at) "
            "VALUES ('2026-07-13', 'Reuters', 'https://x', 'Manual article headline', '')"
        ).lastrowid
        conn.commit()
        add_thread_link_manual(conn, thread["id"], "daily_news", news_id, "MENDUKUNG")
        add_thread_link_manual(conn, thread["id"], "manual_articles", art_id, "NETRAL")
        conn.commit()
        links = {l["ref_table"]: l for l in list_thread_links(conn, thread["id"])}
        assert links["daily_news"]["source_info"]["headline"] == "Warsh signals hawkish stance"
        assert links["manual_articles"]["source_info"]["headline"] == "Manual article headline"


def test_attach_thread_suggestions_returns_all_non_rejected_confirmed_first(tmp_path):
    """1 headline bisa match >1 thread sekaligus (mis. berita relevan ke 2
    narasi berbeda) -- Giel harus bisa lihat/ubah/lepas SEMUANYA, bukan cuma
    1 'pemenang'. Array thread_links kembalikan semua link non-REJECTED,
    CONFIRMED duluan (deterministik, bukan urutan sisipan acak)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        t1 = save_thread(conn, title="Thread Suggested Only")
        t2 = save_thread(conn, title="Thread Confirmed")
        news_id = _seed_news_row(conn)
        conn.commit()
        conn.execute(
            "INSERT INTO news_thread_links (thread_id, ref_table, ref_id, link_status, linked_at) "
            "VALUES (?, 'daily_news', ?, 'SUGGESTED', '')", (t1["id"], news_id),
        )
        add_thread_link_manual(conn, t2["id"], "daily_news", news_id, "MENDUKUNG")
        conn.commit()
        rows = [{"id": news_id, "headline": "Warsh signals hawkish stance"}]
        attached = attach_thread_suggestions(conn, rows)
        links = attached[0]["thread_links"]
        assert len(links) == 2
        assert links[0]["thread_title"] == "Thread Confirmed"
        assert links[0]["link_status"] == "CONFIRMED"
        assert links[1]["thread_title"] == "Thread Suggested Only"
        assert links[1]["link_status"] == "SUGGESTED"


def test_attach_thread_suggestions_excludes_rejected(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        t1 = save_thread(conn, title="Thread Rejected")
        news_id = _seed_news_row(conn)
        conn.commit()
        cur = conn.execute(
            "INSERT INTO news_thread_links (thread_id, ref_table, ref_id, link_status, linked_at) "
            "VALUES (?, 'daily_news', ?, 'REJECTED', '')", (t1["id"], news_id),
        )
        conn.commit()
        rows = [{"id": news_id, "headline": "Warsh signals hawkish stance"}]
        attached = attach_thread_suggestions(conn, rows)
        assert attached[0]["thread_links"] == []


def test_attach_thread_suggestions_empty_list_when_no_link(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        news_id = _seed_news_row(conn)
        conn.commit()
        rows = [{"id": news_id, "headline": "Warsh signals hawkish stance"}]
        attached = attach_thread_suggestions(conn, rows)
        assert attached[0]["thread_links"] == []


# ---------- Faceted Tagging (Addendum C §21, GELOMBANG C-1 fondasi) ----------

def test_create_tag_and_derives_facet(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh", aliases=["fed-warsh"], description="Fed governor")
        conn.commit()
        assert tag["facet"] == "who"
        assert tag["aliases"] == ["fed-warsh"]
        assert tag["usage_count"] == 0


def test_create_tag_rejects_missing_colon(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            create_tag(conn, "badformat")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "facet:value" in str(exc)


def test_create_tag_rejects_unknown_facet(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            create_tag(conn, "xx:warsh")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "facet" in str(exc)


def test_create_tag_rejects_space_in_value(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            create_tag(conn, "who:warsh guy")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "lowercase" in str(exc) or "valid" in str(exc)


def test_create_tag_sym_requires_region_prefix(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            create_tag(conn, "sym:bbca")  # tanpa region prefix
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "region-prefix" in str(exc)
        ok = create_tag(conn, "sym:id-bbca")  # dgn region prefix -- lolos
        assert ok["canonical"] == "sym:id-bbca"


def test_create_tag_sym_global_symbols_exempt_from_region_prefix(tmp_path):
    """Ketemu 17 Jul 2026 (seed_tags.py): kontrak §21.1 sendiri mencontohkan
    'sym:btc'/'sym:xau' TANPA region-prefix -- simbol global/makro yang tidak
    ambigu lintas market dikecualikan dari aturan region-prefix (beda dari
    ticker saham spt 'bbca' yang tetap wajib, lihat test di atas)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for canonical in ["sym:btc", "sym:eth", "sym:xau", "sym:dxy", "sym:us10y", "sym:vix", "sym:sp500", "sym:idx"]:
            ok = create_tag(conn, canonical)
            assert ok["canonical"] == canonical


def test_create_tag_rejects_duplicate_canonical(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        conn.commit()
        try:
            create_tag(conn, "who:warsh")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "sudah ada" in str(exc)


def test_list_tags_filters_by_facet(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        create_tag(conn, "org:fed")
        conn.commit()
        assert len(list_tags(conn)) == 2
        assert len(list_tags(conn, facet="who")) == 1


def test_resolve_tag_by_canonical_and_alias(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh", aliases=["fed-warsh", "warsh"])
        conn.commit()
        assert resolve_tag(conn, "who:warsh")["canonical"] == "who:warsh"
        assert resolve_tag(conn, "fed-warsh")["canonical"] == "who:warsh"
        assert resolve_tag(conn, "does-not-exist") is None


def test_apply_tag_requires_existing_tag(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        news_id = _seed_news_row(conn)
        conn.commit()
        try:
            apply_tag(conn, "daily_news", news_id, "org:unknown")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "tidak ditemukan" in str(exc)


def test_apply_tag_rejects_unknown_ref_table(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        conn.commit()
        try:
            apply_tag(conn, "policy_tracker", 1, "who:warsh")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "ref_table" in str(exc)


def test_apply_tag_increments_usage_count_and_dedups(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        news_id = _seed_news_row(conn)
        conn.commit()
        applied = apply_tag(conn, "daily_news", news_id, "who:warsh")
        conn.commit()
        assert applied["canonical"] == "who:warsh"
        assert list_tags(conn)[0]["usage_count"] == 1
        try:
            apply_tag(conn, "daily_news", news_id, "who:warsh")
            assert False, "harusnya raise ValueError (dedup)"
        except ValueError as exc:
            assert "sudah terpasang" in str(exc)


def test_apply_tag_resolves_via_alias(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh", aliases=["fed-warsh"])
        news_id = _seed_news_row(conn)
        conn.commit()
        applied = apply_tag(conn, "daily_news", news_id, "fed-warsh")
        assert applied["canonical"] == "who:warsh"


def test_remove_tag_and_unknown_id(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        news_id = _seed_news_row(conn)
        conn.commit()
        applied = apply_tag(conn, "daily_news", news_id, "who:warsh")
        conn.commit()
        assert remove_tag(conn, applied["id"]) is True
        assert list_content_tags(conn, "daily_news", news_id) == []
        assert remove_tag(conn, 9999) is False


def test_list_content_tags_for_one_item(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        create_tag(conn, "org:fed")
        news_id = _seed_news_row(conn)
        conn.commit()
        apply_tag(conn, "daily_news", news_id, "who:warsh")
        apply_tag(conn, "daily_news", news_id, "org:fed")
        conn.commit()
        tags = list_content_tags(conn, "daily_news", news_id)
        assert {t["canonical"] for t in tags} == {"who:warsh", "org:fed"}


def test_attach_content_tags_batch(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        news_id_1 = _seed_news_row(conn, headline="A")
        news_id_2 = _seed_news_row(conn, headline="B", date="2026-07-16")
        conn.commit()
        applied = apply_tag(conn, "daily_news", news_id_1, "who:warsh")
        conn.commit()
        rows = [{"id": news_id_1}, {"id": news_id_2}]
        attached = attach_content_tags(conn, "daily_news", rows)
        # `id` disertakan (content_tags PK) supaya UI bisa panggil remove_tag()
        # langsung -- dicek eksplisit, bukan cuma canonical/facet.
        assert attached[0]["tags"] == [
            {"id": applied["id"], "canonical": "who:warsh", "facet": "who", "source": "MANUAL"}
        ]
        assert attached[1]["tags"] == []


def test_attach_content_tags_empty_rows(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert attach_content_tags(conn, "daily_news", []) == []


# ---------- Settings -> Tag & Thread Management (Addendum C §21.11, C-1 gap ditutup 17 Jul 2026) ----------

def test_update_tag_description_and_facet(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh")
        conn.commit()
        updated = update_tag(conn, tag["id"], description="Fed governor", facet="org")
        assert updated["description"] == "Fed governor"
        assert updated["facet"] == "org"


def test_update_tag_rejects_unknown_facet(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh")
        conn.commit()
        try:
            update_tag(conn, tag["id"], facet="bogus")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "facet" in str(exc)


def test_update_tag_unknown_id_raises(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            update_tag(conn, 999, description="x")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "tidak ditemukan" in str(exc)


def test_delete_tag_blocks_when_still_used_without_force(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh")
        news_id = _seed_news_row(conn)
        conn.commit()
        apply_tag(conn, "daily_news", news_id, "who:warsh")
        conn.commit()
        try:
            delete_tag(conn, tag["id"])
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "force" in str(exc)
        # tag masih ada, belum terhapus
        assert list_tags(conn)


def test_delete_tag_force_cleans_content_tags(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh")
        news_id = _seed_news_row(conn)
        conn.commit()
        apply_tag(conn, "daily_news", news_id, "who:warsh")
        conn.commit()
        assert delete_tag(conn, tag["id"], force=True) is True
        assert list_tags(conn) == []
        assert list_content_tags(conn, "daily_news", news_id) == []


def test_delete_tag_unused_no_force_needed(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh")
        conn.commit()
        assert delete_tag(conn, tag["id"]) is True


def test_delete_tag_unknown_returns_false(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        assert delete_tag(conn, 999) is False


def test_merge_tag_repoints_content_and_merges_aliases(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        dupe = create_tag(conn, "org:us-fed", aliases=["usfed"])
        canonical = create_tag(conn, "org:fed")
        news_id = _seed_news_row(conn)
        conn.commit()
        apply_tag(conn, "daily_news", news_id, "org:us-fed")
        conn.commit()
        merged = merge_tag(conn, dupe["id"], canonical["id"])
        assert merged["canonical"] == "org:fed"
        assert "org:us-fed" in merged["aliases"]
        assert "usfed" in merged["aliases"]
        assert merged["usage_count"] == 1
        # tag lama hilang dari kamus
        assert all(t["id"] != dupe["id"] for t in list_tags(conn))
        # konten yang dulu ditag "dupe" sekarang nunjuk "canonical"
        tags = list_content_tags(conn, "daily_news", news_id)
        assert len(tags) == 1
        assert tags[0]["canonical"] == "org:fed"


def test_merge_tag_no_unique_collision_when_both_already_tagged(tmp_path):
    """Berita yang SUDAH ditag dgn `into` sebelum merge -- re-point `from`
    tidak boleh duplikat baris (UNIQUE ref_table,ref_id,tag_id), dan
    usage_count harus dihitung ulang dari row count aktual, bukan dijumlah."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        dupe = create_tag(conn, "org:us-fed")
        canonical = create_tag(conn, "org:fed")
        news_id = _seed_news_row(conn)
        conn.commit()
        apply_tag(conn, "daily_news", news_id, "org:us-fed")
        apply_tag(conn, "daily_news", news_id, "org:fed")
        conn.commit()
        merged = merge_tag(conn, dupe["id"], canonical["id"])
        assert merged["usage_count"] == 1
        tags = list_content_tags(conn, "daily_news", news_id)
        assert len(tags) == 1


def test_merge_tag_rejects_self_merge(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh")
        conn.commit()
        try:
            merge_tag(conn, tag["id"], tag["id"])
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "sendiri" in str(exc)


def test_merge_tag_unknown_id_raises(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        tag = create_tag(conn, "who:warsh")
        conn.commit()
        try:
            merge_tag(conn, tag["id"], 999)
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "tidak ditemukan" in str(exc)


def test_list_orphan_tags_only_unused(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        orphan = create_tag(conn, "who:warsh")
        used = create_tag(conn, "org:fed")
        news_id = _seed_news_row(conn)
        conn.commit()
        apply_tag(conn, "daily_news", news_id, "org:fed")
        conn.commit()
        orphans = list_orphan_tags(conn)
        ids = {t["id"] for t in orphans}
        assert orphan["id"] in ids
        assert used["id"] not in ids


def test_thread_stats_composition_and_pending(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Rezim Warsh")
        n1 = _seed_news_row(conn, headline="A")
        n2 = _seed_news_row(conn, headline="B")
        n3 = _seed_news_row(conn, headline="C")
        conn.commit()
        l1 = add_thread_link_manual(conn, thread["id"], "daily_news", n1, "MENDUKUNG")
        l2 = add_thread_link_manual(conn, thread["id"], "daily_news", n2, "KONTRA")
        conn.commit()
        # 1 link SUGGESTED pending (manual insert langsung, bukan lewat auto-suggest)
        conn.execute(
            "INSERT INTO news_thread_links (thread_id, ref_table, ref_id, link_status, linked_at) "
            "VALUES (?, 'daily_news', ?, 'SUGGESTED', '')", (thread["id"], n3),
        )
        conn.commit()
        stats = thread_stats(conn, thread["id"])
        assert stats["composition"] == {"MENDUKUNG": 1, "KONTRA": 1, "NETRAL": 0}
        assert stats["pending_suggested"] == 1
        assert stats["age_days"] >= 0


def test_list_threads_with_stats_includes_active_count_and_tags(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        t1 = save_thread(conn, title="Thread A")
        save_thread(conn, title="Thread B")
        conn.commit()
        create_tag(conn, "who:warsh")
        conn.commit()
        apply_tag(conn, "news_threads", t1["id"], "who:warsh")
        conn.commit()
        rows = list_threads_with_stats(conn)
        assert len(rows) == 2
        assert all(r["active_count"] == 2 for r in rows)
        row_a = next(r for r in rows if r["id"] == t1["id"])
        assert row_a["tags"][0]["canonical"] == "who:warsh"


# ---------- GELOMBANG C-2 (Addendum C §21.9, 17 Jul 2026 -- Giel override 2-minggu-tunggu, "FINAL") ----------

def test_suggest_tags_for_news_matches_alias_and_hyphenated_value(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh", aliases=["fed-warsh"])
        create_tag(conn, "theme:rate-policy")
        news_id = _seed_news_row(conn, headline="Fed-Warsh signals rate policy shift")
        conn.commit()
        n = suggest_tags_for_news(conn, [{"date": "2026-07-15", "headline": "Fed-Warsh signals rate policy shift"}])
        assert n == 2
        tags = {t["canonical"] for t in list_content_tags(conn, "daily_news", news_id)}
        assert tags == {"who:warsh", "theme:rate-policy"}
        applied = list_content_tags(conn, "daily_news", news_id)
        assert all(t["source"] == "SUGGESTED" for t in applied)


def test_suggest_tags_for_news_idempotent(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        create_tag(conn, "who:warsh")
        _seed_news_row(conn, headline="Warsh speaks")
        conn.commit()
        items = [{"date": "2026-07-15", "headline": "Warsh speaks"}]
        first = suggest_tags_for_news(conn, items)
        second = suggest_tags_for_news(conn, items)
        assert first == 1
        assert second == 0
        tag = resolve_tag(conn, "who:warsh")
        assert tag["usage_count"] == 1


def test_suggest_thread_links_tag_overlap_matches_without_keyword(tmp_path):
    """Thread yang tidak punya keywords sama sekali tapi punya facet tag ->
    tetap dapat SUGGESTED link kalau berita match tag yang sama (§21.5)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Rezim Warsh")  # tanpa keywords
        conn.commit()
        create_tag(conn, "who:warsh")
        conn.commit()
        apply_tag(conn, "news_threads", thread["id"], "who:warsh")
        conn.commit()
        news_id = _seed_news_row(conn, headline="Central bank governor speaks today")
        conn.commit()
        apply_tag(conn, "daily_news", news_id, "who:warsh")
        conn.commit()
        n = suggest_thread_links(
            conn, [{"date": "2026-07-15", "headline": "Central bank governor speaks today"}]
        )
        assert n == 1
        links = list_thread_links(conn, thread["id"])
        assert links[0]["link_status"] == "SUGGESTED"


def test_suggest_thread_links_keyword_only_thread_still_works(tmp_path):
    """Regression guard: thread TANPA facet tag (kasus lama, News Threads N-1)
    tetap match lewat keyword-only fallback, tidak rusak oleh tag-overlap pass."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Rezim Warsh", keywords=["warsh"])
        _seed_news_row(conn, headline="Warsh signals hawkish stance")
        conn.commit()
        n = suggest_thread_links(conn, [{"date": "2026-07-15", "headline": "Warsh signals hawkish stance"}])
        assert n == 1


def test_auto_dormant_stale_threads_only_touches_active_and_stale(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        fresh = save_thread(conn, title="Fresh Thread")
        stale = save_thread(conn, title="Stale Thread")
        closed = save_thread(conn, title="Closed Thread")
        conn.commit()
        patch_thread(conn, closed["id"], status="CLOSED", verdict="selesai")
        conn.execute(
            "UPDATE news_threads SET updated_at = date('now', '-40 day') WHERE id = ?", (stale["id"],)
        )
        conn.commit()
        n = auto_dormant_stale_threads(conn, stale_days=30)
        assert n == 1
        assert get_thread(conn, stale["id"])["status"] == "DORMANT"
        assert get_thread(conn, fresh["id"])["status"] == "ACTIVE"
        assert get_thread(conn, closed["id"])["status"] == "CLOSED"
