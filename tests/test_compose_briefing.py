"""Test pipeline/compose_briefing.py — pure function, tanpa network/Telegram."""
from db.connection import get_connection, init_db
from pipeline.compose_briefing import compose_daily_briefing


def _seed_market(conn, date, **overrides):
    defaults = {
        "date": date, "btc_close": 62000.0, "dxy_close": 120.5,
        "fear_greed_value": 20, "fear_greed_label": "Extreme Fear",
        "created_at": "",
    }
    defaults.update(overrides)
    conn.execute(
        "INSERT INTO daily_market (date, btc_close, dxy_close, fear_greed_value, "
        "fear_greed_label, created_at) VALUES (:date, :btc_close, :dxy_close, "
        ":fear_greed_value, :fear_greed_label, :created_at)", defaults,
    )


def _seed_ohlcv(conn, date, close):
    conn.execute(
        "INSERT INTO asset_ohlcv (date, instrument, close, created_at) "
        "VALUES (?, 'BTC', ?, '')", (date, close),
    )


def test_briefing_all_sections_empty(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08")
        conn.commit()
        text = compose_daily_briefing(conn, "2026-07-08")

    assert "🔷 KASTARA FINANCE · 2026-07-08" in text
    assert "BTC: $62,000.00" in text
    assert "DXY: 120.50" in text
    assert "F&G: 20 · Extreme Fear" in text
    assert "📰 KEY EVENTS" not in text  # tidak ada key-trigger -> section dihilangkan
    assert "GEMA: (belum diisi)" in text
    assert "LEON: (belum diisi)" in text
    assert "AKELA: (belum diisi)" in text
    assert "RIVAN: (belum diisi)" in text
    assert "📈 SIGNAL\n(belum diisi)" in text
    assert "⚠️ Ini bukan rekomendasi finansial." in text
    assert "Keputusan ada di tangan kamu." in text


def test_briefing_btc_pct_change_computed(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08", btc_close=63000.0)
        _seed_ohlcv(conn, "2026-07-07", 60000.0)
        _seed_ohlcv(conn, "2026-07-08", 63000.0)
        conn.commit()
        text = compose_daily_briefing(conn, "2026-07-08")

    assert "BTC: $63,000.00 (+5.0%)" in text


def test_briefing_key_events_shown(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08")
        conn.execute(
            "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
            "for_reading, created_at) VALUES ('2026-07-08', 'CNBC', "
            "'Fed signals rate cut', 'https://x.test', 'HIGH', 1, '')"
        )
        conn.commit()
        text = compose_daily_briefing(conn, "2026-07-08")

    assert "📰 KEY EVENTS" in text
    assert "- Fed signals rate cut" in text


def test_briefing_lens_notes_shown(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08")
        conn.execute(
            "INSERT INTO reading_workspace (date, lens, notes, created_at) "
            "VALUES ('2026-07-08', 'GEMA', 'Makro netral, tunggu CPI', '')"
        )
        conn.commit()
        text = compose_daily_briefing(conn, "2026-07-08")

    assert "GEMA: Makro netral, tunggu CPI" in text
    assert "LEON: (belum diisi)" in text


def test_briefing_multiple_approved_signals_all_shown(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08")
        conn.execute(
            "INSERT INTO trade_signals (date, instrument, signal_type, entry_price, "
            "sl_price, tp1_price, rr_ratio, approved, created_at) VALUES "
            "('2026-07-08', 'BTC', 'BREAKOUT', 63000, 61000, 68000, 2.5, 1, '')"
        )
        conn.execute(
            "INSERT INTO trade_signals (date, instrument, signal_type, entry_price, "
            "sl_price, tp1_price, rr_ratio, approved, created_at) VALUES "
            "('2026-07-08', 'BTC', 'RETEST', 62000, 60500, 65000, 1.8, 1, '')"
        )
        # pending (belum approve) -> TIDAK boleh muncul
        conn.execute(
            "INSERT INTO trade_signals (date, instrument, signal_type, entry_price, "
            "sl_price, tp1_price, rr_ratio, approved, created_at) VALUES "
            "('2026-07-08', 'BTC', 'BREAKOUT', 70000, 68000, 75000, 2.0, 0, '')"
        )
        conn.commit()
        text = compose_daily_briefing(conn, "2026-07-08")

    assert text.count("BTC BREAKOUT") == 1  # cuma yang approved
    assert "BTC RETEST" in text
    assert "70,000.00" not in text
