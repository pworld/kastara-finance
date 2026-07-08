"""Test DB layer: init_db bikin 14 tabel sesuai schema (11 Phase A + 3 forward-layer)."""
from db.connection import EXPECTED_TABLES, init_db, list_tables


def test_init_db_creates_all_tables(tmp_path):
    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    tables = list_tables(db_file)
    assert len(tables) == 14
    for t in EXPECTED_TABLES:
        assert t in tables, f"tabel {t} tidak terbuat"


def test_init_db_idempotent(tmp_path):
    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    # Jalan 2x tidak boleh error / tidak duplikat tabel
    init_db(db_file)
    assert len(list_tables(db_file)) == 14


def test_daily_market_has_source_flags_column(tmp_path):
    db_file = tmp_path / "test_kastara-finance.db"
    init_db(db_file)
    from db.connection import get_connection

    with get_connection(db_file) as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(daily_market)")]
    assert "source_flags" in cols
    assert "net_liquidity" in cols
