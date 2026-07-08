"""Test tools/review_signal.py — approve/reject by id eksplisit, tidak ada
mode 'approve semua' (Master Plan §3: Giel yang approve, bukan mesin)."""
from db.connection import get_connection, init_db
from tools.review_signal import list_signals, set_review


def _seed_signal(conn, **overrides):
    defaults = {
        "date": "2026-01-01", "instrument": "BTC", "signal_type": "RETEST",
        "entry_price": 100.0, "sl_price": 95.0, "tp1_price": 115.0,
        "rr_ratio": 3.0, "zone_lower": 95.0, "zone_upper": 100.0,
        "volume_confirmed": 1, "is_valid": 1, "giel_approved": 0, "notes": None,
    }
    defaults.update(overrides)
    cur = conn.execute(
        "INSERT INTO trade_signals (date, instrument, signal_type, entry_price, "
        "sl_price, tp1_price, rr_ratio, zone_lower, zone_upper, volume_confirmed, "
        "is_valid, giel_approved, notes, created_at) "
        "VALUES (:date, :instrument, :signal_type, :entry_price, :sl_price, "
        ":tp1_price, :rr_ratio, :zone_lower, :zone_upper, :volume_confirmed, "
        ":is_valid, :giel_approved, :notes, '')",
        defaults,
    )
    return cur.lastrowid


def test_list_default_shows_only_pending(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        id_pending = _seed_signal(conn)
        id_approved = _seed_signal(conn, giel_approved=1)
        id_rejected = _seed_signal(conn, notes="skip, alasan")
        conn.commit()

        pending = list_signals(conn)
        pending_ids = {r["id"] for r in pending}
        assert id_pending in pending_ids
        assert id_approved not in pending_ids
        assert id_rejected not in pending_ids


def test_list_all_shows_everything(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_signal(conn)
        _seed_signal(conn, giel_approved=1)
        conn.commit()
        rows = list_signals(conn, show_all=True)
        assert len(rows) == 2


def test_list_filters_instrument_and_valid_only(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_signal(conn, instrument="BTC", is_valid=1)
        _seed_signal(conn, instrument="BTC", is_valid=0)
        _seed_signal(conn, instrument="SP500", is_valid=1)
        conn.commit()
        rows = list_signals(conn, show_all=True, instrument="btc", valid_only=True)
        assert len(rows) == 1
        assert rows[0]["instrument"] == "BTC"
        assert rows[0]["is_valid"] == 1


def test_set_review_approve(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        sid = _seed_signal(conn)
        conn.commit()
        ok = set_review(conn, sid, approved=True, notes="setup bagus")
        conn.commit()
        assert ok is True
        row = conn.execute("SELECT giel_approved, notes FROM trade_signals WHERE id=?", (sid,)).fetchone()
        assert row["giel_approved"] == 1
        assert row["notes"] == "setup bagus"


def test_set_review_reject_keeps_giel_approved_zero(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        sid = _seed_signal(conn)
        conn.commit()
        ok = set_review(conn, sid, approved=False, notes="DXY breakout barengan, skip")
        conn.commit()
        assert ok is True
        row = conn.execute("SELECT giel_approved, notes FROM trade_signals WHERE id=?", (sid,)).fetchone()
        assert row["giel_approved"] == 0
        assert row["notes"] == "DXY breakout barengan, skip"


def test_set_review_unknown_id_returns_false(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        ok = set_review(conn, 9999, approved=True, notes="x")
        assert ok is False


def test_set_review_only_affects_target_row(tmp_path):
    # Regression guard: approve/reject tidak pernah mempengaruhi row lain
    # (tidak ada mode "approve semua").
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        id1 = _seed_signal(conn)
        id2 = _seed_signal(conn)
        conn.commit()
        set_review(conn, id1, approved=True, notes="only this one")
        conn.commit()
        row2 = conn.execute("SELECT giel_approved, notes FROM trade_signals WHERE id=?", (id2,)).fetchone()
        assert row2["giel_approved"] == 0
        assert row2["notes"] is None
