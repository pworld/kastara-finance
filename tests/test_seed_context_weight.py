"""Test pipeline/seed_context_weight.py — idempotent seed BTC (Master Plan §4.3)."""
from db.connection import get_connection, init_db
from pipeline.seed_context_weight import BTC_WEIGHTS, seed_instrument


def test_seed_inserts_all_btc_weights(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        n = seed_instrument(conn, "BTC", BTC_WEIGHTS)
        conn.commit()
        assert n == len(BTC_WEIGHTS)
        rows = conn.execute(
            "SELECT driver, weight FROM asset_context_weight WHERE instrument='BTC'"
        ).fetchall()
        drivers = {r["driver"]: r["weight"] for r in rows}
        assert drivers == {
            "net_liquidity": "HIGH", "etf_flow": "HIGH",
            "fear_greed": "MED", "dxy": "MED",
        }


def test_seed_idempotent(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        seed_instrument(conn, "BTC", BTC_WEIGHTS)
        conn.commit()
        n_second = seed_instrument(conn, "BTC", BTC_WEIGHTS)
        conn.commit()
        assert n_second == 0
        total = conn.execute("SELECT COUNT(*) FROM asset_context_weight WHERE instrument='BTC'").fetchone()[0]
        assert total == len(BTC_WEIGHTS)
