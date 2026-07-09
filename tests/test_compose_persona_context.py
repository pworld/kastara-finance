"""Test pipeline/compose_persona_context.py — pure function, tanpa network/LLM."""
from db.connection import get_connection, init_db
from pipeline.compose_persona_context import compose_persona_context


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


def test_context_no_key_news(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08")
        conn.commit()
        text = compose_persona_context(conn, "2026-07-08")

    assert "[SNAPSHOT PASAR - 2026-07-08]" in text
    assert "BTC: $62,000.00" in text
    assert "DXY: 120.50" in text
    assert "F&G: 20 · Extreme Fear" in text
    assert "[BERITA KEY HARI INI]" in text
    assert "(belum ada berita yang di-flag key hari ini)" in text


def test_context_btc_pct_change_computed(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08", btc_close=63000.0)
        _seed_ohlcv(conn, "2026-07-07", 60000.0)
        _seed_ohlcv(conn, "2026-07-08", 63000.0)
        conn.commit()
        text = compose_persona_context(conn, "2026-07-08")

    assert "BTC: $63,000.00 (+5.0%)" in text


def test_context_key_news_shown(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_market(conn, "2026-07-08")
        conn.execute(
            "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
            "is_key_trigger, created_at) VALUES ('2026-07-08', 'CNBC', "
            "'Fed signals rate cut', 'https://x.test', 'HIGH', 1, '')"
        )
        # non-key -> tidak boleh muncul
        conn.execute(
            "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
            "is_key_trigger, created_at) VALUES ('2026-07-08', 'CNBC', "
            "'Berita biasa', 'https://x.test', 'LOW', 0, '')"
        )
        conn.commit()
        text = compose_persona_context(conn, "2026-07-08")

    assert "- [HIGH] Fed signals rate cut (CNBC)" in text
    assert "Berita biasa" not in text
    assert "(belum ada berita yang di-flag key hari ini)" not in text
