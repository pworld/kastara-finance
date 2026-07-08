"""Orchestrator Phase B — analysis engine.

Baca asset_ohlcv (BTC, hardcode di sini — analysis/*.py TETAP generic per
plan_b.txt §4), deteksi zona S&R + sinyal breakout/retest, UPSERT sr_zones,
INSERT trade_signals (dedup manual, approved SELALU 0).

Dijadwalkan MANUAL untuk sekarang (plan_b.txt §7.6 — lokal cuma dev, cron
dipindah ke server nanti):
    python -m pipeline.run_analysis
"""
from __future__ import annotations

import sqlite3
from typing import Any

from analysis.indicators import ma_stack_order, moving_average, rolling_ma
from analysis.signals import detect_signals
from analysis.sr_zones import detect_zones, zone_bucket_key
from db.connection import get_connection, init_db
from scrapers.base import created_at

# Phase B cuma proses BTC dulu (plan_b.txt §4, §1 "disiplin build" Master
# Plan §3) — filter di orchestrator, BUKAN di modul analysis/ yang generic.
INSTRUMENT = "BTC"

VOLUME_MA_PERIOD = 20


def _load_history(conn: sqlite3.Connection, instrument: str) -> dict[str, list]:
    rows = conn.execute(
        "SELECT date, high, low, close, volume FROM asset_ohlcv "
        "WHERE instrument = ? ORDER BY date ASC",
        (instrument,),
    ).fetchall()
    return {
        "dates": [r["date"] for r in rows],
        "highs": [r["high"] for r in rows],
        "lows": [r["low"] for r in rows],
        "closes": [r["close"] for r in rows],
        "volumes": [r["volume"] for r in rows],
    }


def upsert_sr_zone(conn: sqlite3.Connection, instrument: str, zone: dict[str, Any]) -> str:
    """UPSERT 1 zona by natural key (bucket relatif, plan_b.txt §7.4).

    Return 'inserted' | 'updated'. TIDAK PERNAH menimpa `validated`
    atau `notes` — itu field manual review, bukan hasil deteksi otomatis.
    """
    target_key = zone_bucket_key(zone["zone_type"], zone["zone_lower"], zone["zone_upper"])
    existing = conn.execute(
        "SELECT id, zone_lower, zone_upper FROM sr_zones WHERE instrument = ? AND zone_type = ?",
        (instrument, zone["zone_type"]),
    ).fetchall()
    match_id = None
    for r in existing:
        if zone_bucket_key(zone["zone_type"], r["zone_lower"], r["zone_upper"]) == target_key:
            match_id = r["id"]
            break

    if match_id is not None:
        conn.execute(
            "UPDATE sr_zones SET zone_lower=?, zone_upper=?, touch_count=?, "
            "last_touched=?, is_active=? WHERE id=?",
            (zone["zone_lower"], zone["zone_upper"], zone["touch_count"],
             zone["last_touched"], zone["is_active"], match_id),
        )
        return "updated"

    conn.execute(
        "INSERT INTO sr_zones (instrument, zone_lower, zone_upper, touch_count, "
        "zone_type, first_seen, last_touched, is_active, validated, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)",
        (instrument, zone["zone_lower"], zone["zone_upper"], zone["touch_count"],
         zone["zone_type"], zone["first_seen"], zone["last_touched"], zone["is_active"]),
    )
    return "inserted"


def insert_signal_dedup(conn: sqlite3.Connection, instrument: str, signal: dict[str, Any]) -> bool:
    """INSERT trade_signals kalau BELUM ADA row (date, instrument,
    signal_type, zone_lower, zone_upper) yang sama persis — dedup manual
    (trade_signals tidak punya UNIQUE index, plan_b.txt §5: append-only).
    Return True kalau baris baru ditulis.

    `approved` HARDCODE 0 di sini — satu-satunya tempat trade_signals
    ditulis dari kode otomatis, jadi ini titik jaminan non-negotiable-nya
    (lihat test_run_analysis.py regression guard).
    """
    exists = conn.execute(
        "SELECT 1 FROM trade_signals WHERE date=? AND instrument=? AND signal_type=? "
        "AND zone_lower=? AND zone_upper=? LIMIT 1",
        (signal["date"], instrument, signal["signal_type"],
         signal["zone_lower"], signal["zone_upper"]),
    ).fetchone()
    if exists:
        return False
    conn.execute(
        "INSERT INTO trade_signals (date, instrument, signal_type, entry_price, "
        "sl_price, tp1_price, tp2_price, rr_ratio, zone_lower, zone_upper, "
        "volume_confirmed, is_valid, approved, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)",
        (signal["date"], instrument, signal["signal_type"], signal["entry_price"],
         signal["sl_price"], signal["tp1_price"], signal["tp2_price"], signal["rr_ratio"],
         signal["zone_lower"], signal["zone_upper"], signal["volume_confirmed"],
         signal["is_valid"], created_at()),
    )
    return True


def _format_price(v: float | None) -> str:
    return f"{v:,.2f}" if v is not None else "n/a"


def run_analysis(instrument: str = INSTRUMENT, db_path=None) -> dict[str, Any]:
    """Jalankan full analysis engine untuk 1 instrument. Return ringkasan."""
    init_db(db_path)

    with get_connection(db_path) as conn:
        hist = _load_history(conn, instrument)
        n = len(hist["dates"])
        if n == 0:
            print(f"[run_analysis] Tidak ada data asset_ohlcv untuk {instrument}.")
            return {"instrument": instrument, "rows": 0}

        # volume_ma20 di asset_ohlcv cuma keisi buat hari yang diproses
        # run_daily.py (baris backfill historis NULL) -> re-derive dari
        # histori volume penuh (lihat penemuan saat eksekusi Phase B).
        volume_mas = rolling_ma(hist["volumes"], VOLUME_MA_PERIOD)

        # 1) S&R zone detection -> UPSERT
        zones = detect_zones(hist["dates"], hist["highs"], hist["lows"], hist["closes"])
        n_inserted = n_updated = 0
        for z in zones:
            if upsert_sr_zone(conn, instrument, z) == "inserted":
                n_inserted += 1
            else:
                n_updated += 1

        # 2) Reload zona AKTIF dari DB (termasuk yang barusan di-upsert)
        active_zones = [
            {"zone_lower": r["zone_lower"], "zone_upper": r["zone_upper"],
             "zone_type": r["zone_type"], "is_active": r["is_active"]}
            for r in conn.execute(
                "SELECT zone_lower, zone_upper, zone_type, is_active FROM sr_zones "
                "WHERE instrument = ? AND is_active = 1", (instrument,),
            ).fetchall()
        ]

        # 3) Signal detection -> INSERT (dedup)
        signals = detect_signals(
            hist["dates"], hist["closes"], hist["highs"], hist["lows"],
            hist["volumes"], volume_mas, active_zones,
        )
        n_new_signals = sum(1 for s in signals if insert_signal_dedup(conn, instrument, s))

        conn.commit()

        # 4) Indikator diagnostik (plan_b.txt §4 step 4) — informational,
        # tidak ada kolom DB untuk MA harga, jadi cuma dilaporkan di ringkasan.
        ma20 = moving_average(hist["closes"], 20)
        ma50 = moving_average(hist["closes"], 50)
        ma100 = moving_average(hist["closes"], 100)
        ma200 = moving_average(hist["closes"], 200)
        stack = ma_stack_order(ma20, ma50, ma100, ma200)

    summary = {
        "instrument": instrument,
        "rows": n,
        "zones_inserted": n_inserted,
        "zones_updated": n_updated,
        "zones_active": len(active_zones),
        "signals_new": n_new_signals,
        "ma20": ma20, "ma50": ma50, "ma100": ma100, "ma200": ma200,
        "ma_stack": stack,
    }
    _print_summary(summary)
    return summary


def _print_summary(s: dict[str, Any]) -> None:
    print("\n========== RINGKASAN ANALISIS ==========")
    print(f"  instrument      : {s['instrument']}")
    print(f"  rows histori    : {s['rows']}")
    print(f"  zona baru       : {s['zones_inserted']}")
    print(f"  zona di-refresh : {s['zones_updated']}")
    print(f"  zona aktif      : {s['zones_active']}")
    print(f"  sinyal baru     : {s['signals_new']}")
    print(f"  MA20/50/100/200 : {_format_price(s['ma20'])} / {_format_price(s['ma50'])} / "
          f"{_format_price(s['ma100'])} / {_format_price(s['ma200'])}")
    print(f"  MA stack order  : {s['ma_stack']}")
    print("=========================================\n")


if __name__ == "__main__":
    run_analysis()
