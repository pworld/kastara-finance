"""Test pipeline/seed_universe.py — idempotent seed instrument_metadata (Phase J+)."""
from db.connection import get_connection, init_db
from pipeline.seed_universe import UNIVERSE, seed_instrument_metadata


def test_seed_inserts_bbca(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        n = seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
        assert n == len(UNIVERSE)
        row = conn.execute(
            "SELECT * FROM instrument_metadata WHERE instrument = 'BBCA'"
        ).fetchone()
        assert row is not None
        assert row["market"] == "IDX"
        assert row["lane"] == "INVEST"
        assert row["lane_validated_at"] is None
        assert row["is_financial"] == 1
        assert row["lot_size"] == 100


def test_seed_inserts_tsla(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
        row = conn.execute(
            "SELECT * FROM instrument_metadata WHERE instrument = 'TSLA'"
        ).fetchone()
        assert row is not None
        assert row["market"] == "US"
        assert row["lane"] == "INVEST"
        assert row["lane_validated_at"] is None
        assert row["has_daily_limit"] == 0  # LULD, bukan ARA/ARB
        assert row["lot_size"] == 1


def test_seed_idempotent_no_duplicates(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) c FROM instrument_metadata WHERE instrument = 'BBCA'"
        ).fetchone()["c"]
        assert count == 1


def test_new_instrument_never_defaults_to_trade(tmp_path):
    """Kontrak §13.1 poin 5: instrumen baru WAJIB masuk INVEST/NONE dulu,
    tidak boleh langsung TRADE tanpa validasi bar-replay."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
        rows = conn.execute("SELECT lane, lane_validated_at FROM instrument_metadata").fetchall()
    for row in rows:
        assert row["lane"] in ("INVEST", "NONE")
        assert row["lane_validated_at"] is None
