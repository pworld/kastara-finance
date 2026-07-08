"""Test pipeline/run_analysis.py end-to-end — data sintetis di temp DB
(bukan data BTC asli, supaya deterministic & cepat). Verifikasi wiring
DB (load histori, UPSERT zona, INSERT sinyal dedup, idempotent) dan
regression guard approved SELALU 0.
"""
from db.connection import get_connection, init_db
from pipeline.run_analysis import run_analysis

INSTRUMENT = "TESTCOIN"


def _seed_synthetic_history(db_path):
    """150 candle: 2 sentuhan resistance [100.0, 100.2] (index 15 & 60,
    berjarak >2*lookback biar swing detection tidak saling interferensi)
    -> zona aktif, lalu breakout (index 110) + retest (index 111)."""
    n = 150
    prices = [50.0] * n
    prices[15] = 100.0
    prices[60] = 100.2
    prices[110] = 110.0   # breakout: close > zone_upper
    prices[111] = 100.1   # retest: touching zona, close > zone_lower

    volumes = [100.0] * n
    volumes[110] = 250.0  # ratio ~2.3 -> breakout volume confirmed
    volumes[111] = 90.0   # ratio ~0.84 -> volume "hadir"

    init_db(db_path)
    with get_connection(db_path) as conn:
        for i in range(n):
            conn.execute(
                "INSERT INTO asset_ohlcv (date, instrument, open, high, low, close, volume, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, '')",
                (f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}", INSTRUMENT,
                 prices[i], prices[i], prices[i], prices[i], volumes[i]),
            )
        conn.commit()


def test_run_analysis_end_to_end(tmp_path):
    db = tmp_path / "analysis_test.db"
    _seed_synthetic_history(db)

    summary = run_analysis(instrument=INSTRUMENT, db_path=db)

    assert summary["rows"] == 150
    # 3 zona kedeteksi: (1) baseline 50.0 itu sendiri -- artefak wajar dari
    # data sintetis "flat" (banyak candle harga identik berturut-turut
    # otomatis lolos kriteria swing low ==min di window-nya -- tidak akan
    # terjadi di data pasar asli), (2) zona resistance utama [100,100.2],
    # (3) spike breakout terisolasi di 110.0 (touch_count=1, is_active=0).
    assert summary["zones_inserted"] == 3
    assert summary["zones_active"] == 2  # baseline + zona utama, keduanya touch_count>=2
    assert summary["signals_new"] >= 1

    with get_connection(db) as conn:
        zones = conn.execute(
            "SELECT * FROM sr_zones WHERE instrument = ?", (INSTRUMENT,)
        ).fetchall()
        assert len(zones) == 3
        main_zone = [z for z in zones if z["zone_lower"] <= 100.2 and z["zone_upper"] >= 100.0]
        assert len(main_zone) == 1
        assert main_zone[0]["zone_type"] == "RESISTANCE"
        # 3 touch: 2 swing point asli (d15, d60) + candle retest (d111) yang
        # harganya (100.1) juga legitimately jatuh di dalam batas zona ini.
        assert main_zone[0]["touch_count"] == 3
        assert main_zone[0]["is_active"] == 1
        assert main_zone[0]["validated"] == 0  # default, belum direview manual

        signals = conn.execute(
            "SELECT * FROM trade_signals WHERE instrument = ?", (INSTRUMENT,)
        ).fetchall()
        assert len(signals) >= 2  # minimal 1 BREAKOUT + 1 RETEST
        types = {s["signal_type"] for s in signals}
        assert "BREAKOUT" in types
        assert "RETEST" in types


def test_run_analysis_approved_always_zero(tmp_path):
    """Regression guard non-negotiable (plan_b.txt §9 Definition of Done)."""
    db = tmp_path / "analysis_test.db"
    _seed_synthetic_history(db)
    run_analysis(instrument=INSTRUMENT, db_path=db)

    with get_connection(db) as conn:
        rows = conn.execute(
            "SELECT approved FROM trade_signals WHERE instrument = ?", (INSTRUMENT,)
        ).fetchall()
        assert len(rows) > 0
        assert all(r["approved"] == 0 for r in rows)


def test_run_analysis_idempotent(tmp_path):
    db = tmp_path / "analysis_test.db"
    _seed_synthetic_history(db)

    run_analysis(instrument=INSTRUMENT, db_path=db)
    with get_connection(db) as conn:
        zones_1 = conn.execute("SELECT COUNT(*) c FROM sr_zones WHERE instrument=?", (INSTRUMENT,)).fetchone()["c"]
        signals_1 = conn.execute("SELECT COUNT(*) c FROM trade_signals WHERE instrument=?", (INSTRUMENT,)).fetchone()["c"]

    # run ke-2: tidak boleh nambah zona/sinyal (data histori sama persis)
    summary2 = run_analysis(instrument=INSTRUMENT, db_path=db)
    assert summary2["zones_inserted"] == 0
    assert summary2["signals_new"] == 0

    with get_connection(db) as conn:
        zones_2 = conn.execute("SELECT COUNT(*) c FROM sr_zones WHERE instrument=?", (INSTRUMENT,)).fetchone()["c"]
        signals_2 = conn.execute("SELECT COUNT(*) c FROM trade_signals WHERE instrument=?", (INSTRUMENT,)).fetchone()["c"]
    assert zones_2 == zones_1
    assert signals_2 == signals_1


def test_run_analysis_preserves_manual_review_on_rerun(tmp_path):
    """Re-run TIDAK BOLEH menimpa validated/notes yang sudah diisi
    manual -- ini prinsip non-negotiable (plan_b.txt), bukan detail kecil."""
    db = tmp_path / "analysis_test.db"
    _seed_synthetic_history(db)
    run_analysis(instrument=INSTRUMENT, db_path=db)

    with get_connection(db) as conn:
        zone_id = conn.execute(
            "SELECT id FROM sr_zones WHERE instrument=? AND zone_lower<=100.2 AND zone_upper>=100.0",
            (INSTRUMENT,),
        ).fetchone()["id"]
        conn.execute(
            "UPDATE sr_zones SET validated=1, notes='sudah dicek manual' WHERE id=?",
            (zone_id,),
        )
        conn.commit()

    run_analysis(instrument=INSTRUMENT, db_path=db)

    with get_connection(db) as conn:
        row = conn.execute("SELECT validated, notes FROM sr_zones WHERE id=?", (zone_id,)).fetchone()
        assert row["validated"] == 1
        assert row["notes"] == "sudah dicek manual"


def test_run_analysis_no_data_returns_empty_summary(tmp_path):
    db = tmp_path / "empty.db"
    init_db(db)
    summary = run_analysis(instrument="NOPE", db_path=db)
    assert summary["rows"] == 0
