"""Test pipeline/run_investing_actual.py -- matching + write logic (tanpa
network, scraper di-monkeypatch). Pola tmp_path db sama tests/test_web_writes.py."""
from db.connection import get_connection, init_db
from pipeline.run_investing_actual import (
    _best_match,
    _find_candidates,
    _normalize_name,
    run_investing_actual,
)


def _seed_econ_event(conn, **overrides):
    defaults = {
        "event_date": "2026-07-14", "event_time": "20:30", "event_name": "CPI m/m",
        "country": "US", "importance": "HIGH", "forecast": "0.3%", "previous": "0.2%",
        "actual": None,
    }
    defaults.update(overrides)
    cur = conn.execute(
        "INSERT INTO econ_calendar (event_date, event_time, event_name, country, "
        "importance, forecast, previous, actual, is_watched, created_at) "
        "VALUES (:event_date, :event_time, :event_name, :country, :importance, "
        ":forecast, :previous, :actual, 0, '')",
        defaults,
    )
    return cur.lastrowid


# ---------- _normalize_name ----------

def test_normalize_keeps_period_marker_but_drops_month():
    assert _normalize_name("Core CPI (MoM) (Jun)") == "core cpi mom"
    assert _normalize_name("CPI m/m") == "cpi mom"
    assert _normalize_name("CPI (YoY) (Jun)") == "cpi yoy"
    assert _normalize_name("CPI y/y") == "cpi yoy"


def test_normalize_disambiguates_mom_vs_yoy():
    # Ini yang tadinya bikin _best_match TIE (skor sama) sebelum period
    # marker dipertahankan -- lihat catatan di _normalize_name.
    assert _normalize_name("CPI (MoM) (Jun)") != _normalize_name("CPI (YoY) (Jun)")


# ---------- _find_candidates ----------

def test_find_candidates_filters_by_high_null_actual_country_and_date_window(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        wanted = _seed_econ_event(conn, event_name="CPI m/m")
        _seed_econ_event(conn, event_name="Already filled", actual="1.0%")  # actual terisi -> skip
        _seed_econ_event(conn, event_name="Wrong country", country="EU")
        _seed_econ_event(conn, event_name="Too far", event_date="2026-07-01")
        _seed_econ_event(conn, event_name="Not HIGH", importance="MED")
        conn.commit()
        candidates = _find_candidates(conn, "2026-07-14", "US")
    assert [c["id"] for c in candidates] == [wanted]


def test_find_candidates_allows_one_day_window(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        wanted = _seed_econ_event(conn, event_date="2026-07-13")
        conn.commit()
        candidates = _find_candidates(conn, "2026-07-14", "US")
    assert [c["id"] for c in candidates] == [wanted]


# ---------- _best_match ----------

def test_best_match_picks_closest_name():
    candidates = [
        {"id": 1, "event_name": "Core CPI m/m"},
        {"id": 2, "event_name": "CPI m/m"},
    ]
    best = _best_match("CPI (MoM) (Jun)", candidates)
    assert best["id"] == 2


def test_best_match_none_when_below_threshold():
    candidates = [{"id": 1, "event_name": "Unemployment Rate"}]
    assert _best_match("Trade Balance", candidates) is None


def test_best_match_none_when_ambiguous_tie():
    candidates = [
        {"id": 1, "event_name": "CPI m/m"},
        {"id": 2, "event_name": "CPI y/y"},
    ]
    assert _best_match("CPI", candidates) is None


# ---------- run_investing_actual (end-to-end, scraper di-monkeypatch) ----------

def test_run_investing_actual_matches_and_writes(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        matched_id = _seed_econ_event(conn, event_name="CPI m/m", event_date="2026-07-14", country="US")
        conn.commit()

    monkeypatch.setattr(
        "pipeline.run_investing_actual.fetch_investing_actuals",
        lambda: {
            "items": [
                {"event_date": "2026-07-14", "country": "US", "event_name": "CPI (MoM) (Jun)", "actual": "0.4%"},
            ],
            "source_flags": {"investing_calendar_actual": "ok"},
        },
    )

    summary = run_investing_actual(db)

    assert summary == {
        "fetched": 1, "matched": 1, "skipped_no_match": 0,
        "source_flags": {"investing_calendar_actual": "ok"},
    }
    with get_connection(db) as conn:
        row = conn.execute("SELECT actual FROM econ_calendar WHERE id = ?", (matched_id,)).fetchone()
        assert row["actual"] == "0.4%"


def test_run_investing_actual_skips_when_no_candidate(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    init_db(db)

    monkeypatch.setattr(
        "pipeline.run_investing_actual.fetch_investing_actuals",
        lambda: {
            "items": [
                {"event_date": "2026-07-14", "country": "US", "event_name": "CPI (MoM) (Jun)", "actual": "0.4%"},
            ],
            "source_flags": {"investing_calendar_actual": "ok"},
        },
    )

    summary = run_investing_actual(db)
    assert summary["matched"] == 0
    assert summary["skipped_no_match"] == 1


def test_run_investing_actual_no_crash_when_scraper_returns_empty(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    init_db(db)
    monkeypatch.setattr(
        "pipeline.run_investing_actual.fetch_investing_actuals",
        lambda: {"items": [], "source_flags": {"investing_calendar_actual": "fail"}},
    )
    summary = run_investing_actual(db)
    assert summary == {
        "fetched": 0, "matched": 0, "skipped_no_match": 0,
        "source_flags": {"investing_calendar_actual": "fail"},
    }
