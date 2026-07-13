"""Test pipeline/seed_context_weight.py — idempotent seed per instrument (Master Plan §4.3)."""
from db.connection import get_connection, init_db
from pipeline.seed_context_weight import (
    BBCA_WEIGHTS,
    BTC_WEIGHTS,
    FOREX_WEIGHTS,
    GOLD_WEIGHTS,
    IHSG_WEIGHTS,
    SP500_WEIGHTS,
    TSLA_WEIGHTS,
    USDJPY_WEIGHTS,
    seed_instrument,
)


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


# ---------- Phase F+ expansion (GOLD/SP500/IHSG/USDIDR/USDJPY) ----------

def test_seed_other_instruments(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for instrument, weights in [
            ("GOLD", GOLD_WEIGHTS), ("SP500", SP500_WEIGHTS),
            ("IHSG", IHSG_WEIGHTS), ("USDIDR", FOREX_WEIGHTS),
            ("USDJPY", USDJPY_WEIGHTS),
        ]:
            n = seed_instrument(conn, instrument, weights)
            assert n == len(weights)
        conn.commit()

        for instrument, weights in [
            ("GOLD", GOLD_WEIGHTS), ("SP500", SP500_WEIGHTS),
            ("IHSG", IHSG_WEIGHTS), ("USDIDR", FOREX_WEIGHTS),
            ("USDJPY", USDJPY_WEIGHTS),
        ]:
            rows = conn.execute(
                "SELECT driver FROM asset_context_weight WHERE instrument=?", (instrument,)
            ).fetchall()
            assert {r["driver"] for r in rows} == {d for d, _, _ in weights}


# ---------- Phase J+ (BBCA/TSLA, Build Contract v1.3 J-10) ----------

def test_seed_bbca_tsla_weights(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        n_bbca = seed_instrument(conn, "BBCA", BBCA_WEIGHTS)
        n_tsla = seed_instrument(conn, "TSLA", TSLA_WEIGHTS)
        conn.commit()
        assert n_bbca == len(BBCA_WEIGHTS)
        assert n_tsla == len(TSLA_WEIGHTS)

        bbca_drivers = {
            r["driver"] for r in conn.execute(
                "SELECT driver FROM asset_context_weight WHERE instrument='BBCA'"
            ).fetchall()
        }
        assert bbca_drivers == {d for d, _, _ in BBCA_WEIGHTS}
        assert "ihsg_foreign_flow" in bbca_drivers  # bukan sekadar generic FOREX/BTC weights

        tsla_drivers = {
            r["driver"] for r in conn.execute(
                "SELECT driver FROM asset_context_weight WHERE instrument='TSLA'"
            ).fetchall()
        }
        assert tsla_drivers == {d for d, _, _ in TSLA_WEIGHTS}

        # level DEFAULT 'INSTRUMENT' (schema.sql) -- belum bangun pewarisan
        # index->sector->instrument, seed manual instrument-level saja (J-10 scope).
        levels = {
            r["level"] for r in conn.execute(
                "SELECT level FROM asset_context_weight WHERE instrument IN ('BBCA','TSLA')"
            ).fetchall()
        }
        assert levels == {"INSTRUMENT"}
