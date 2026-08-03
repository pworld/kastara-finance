"""Test DB layer: init_db bikin 29 tabel sesuai schema (11 Phase A + 3 forward-layer + 7 Phase J+ equity expansion + 1 lane_validation_log + 3 News Threads Addendum B + 2 Faceted Tagging Addendum C + 2 Holdings/Portfolio tracker)."""
from db.connection import EXPECTED_TABLES, init_db, list_tables


def test_init_db_creates_all_tables(tmp_path):
    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    tables = list_tables(db_file)
    assert len(tables) == 29
    for t in EXPECTED_TABLES:
        assert t in tables, f"tabel {t} tidak terbuat"


def test_init_db_idempotent(tmp_path):
    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    # Jalan 2x tidak boleh error / tidak duplikat tabel
    init_db(db_file)
    assert len(list_tables(db_file)) == 29


def test_daily_market_has_source_flags_column(tmp_path):
    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    from db.connection import get_connection

    with get_connection(db_file) as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(daily_market)")]
    assert "source_flags" in cols
    assert "net_liquidity" in cols


def test_for_reading_migration_backfills_from_is_key_trigger(tmp_path):
    """Addendum C §21.2: for_reading gantikan is_key_trigger secara
    fungsional -- kolom baru harus ke-backfill dari nilai lama, TEPAT SEKALI
    saat kolom ini pertama dibuat (bukan tiap init_db dipanggil ulang)."""
    from db.connection import get_connection

    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    with get_connection(db_file) as conn:
        conn.execute(
            "INSERT INTO daily_news (date, source, headline, raw_url, "
            "impact_level, is_key_trigger, created_at) VALUES "
            "('2026-01-01','CNBC','Test','https://x','HIGH',1,'')"
        )
        conn.commit()
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(daily_news)")]
        assert "display_subtitle" in cols
        assert "for_reading" in cols

    # init_db lagi (idempotent) -- kolom sudah ada, backfill TIDAK jalan ulang
    # (kalau jalan ulang & row baru punya is_key_trigger=0 override manual
    # for_reading yang sudah diedit, itu bug -- test ini menegakkan itu).
    with get_connection(db_file) as conn:
        conn.execute("UPDATE daily_news SET for_reading = 0")  # simulasikan Giel sudah ubah manual
        conn.commit()
    init_db(db_file)
    with get_connection(db_file) as conn:
        row = conn.execute("SELECT is_key_trigger, for_reading FROM daily_news").fetchone()
        assert row["is_key_trigger"] == 1  # kolom lama beku, tidak disentuh lagi
        assert row["for_reading"] == 0  # TIDAK di-backfill ulang (re-run idempotent)


def test_daily_news_has_rss_summary_column(tmp_path):
    """Addendum D §22.2 (D-1) -- rss_summary kolom baru, NULL wajar (tanpa
    backfill, beda dari for_reading yang perlu copy nilai lama)."""
    from db.connection import get_connection

    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    with get_connection(db_file) as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(daily_news)")]
        assert "rss_summary" in cols
        conn.execute(
            "INSERT INTO daily_news (date, source, headline, raw_url, "
            "impact_level, created_at) VALUES "
            "('2026-01-01','CNBC','Test','https://x','HIGH','')"
        )
        conn.commit()
        row = conn.execute("SELECT rss_summary FROM daily_news").fetchone()
        assert row["rss_summary"] is None
