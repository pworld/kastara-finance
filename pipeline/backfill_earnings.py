"""Backfill earnings_calendar (Phase J+ Build Contract v1.3, J-7).

Beda dari pipeline/run_daily.py: earnings calendar berubah jarang (per
rilis kuartalan + revisi estimate analis sesekali) -- dijalankan manual/
berkala, pola sama pipeline/backfill_fundamentals.py, BUKAN bagian
run_daily harian.

Pakai:
    python -m pipeline.backfill_earnings              # semua instrumen
    python -m pipeline.backfill_earnings --instrument TSLA
"""
from __future__ import annotations

import argparse
from typing import Any

from db.connection import get_connection, init_db
from scrapers.base import created_at
from scrapers.earnings_yf import fetch_earnings_calendar


def upsert_earnings_calendar(conn, instrument: str, rows: list[dict[str, Any]]) -> int:
    """UPSERT by (instrument, earnings_date, event_type) -- natural key
    UNIQUE constraint idx_earnings_calendar_dedup (db/schema.sql). Return
    jumlah baris diproses."""
    n = 0
    for row in rows:
        params = {**row, "instrument": instrument, "created_at": created_at()}
        conn.execute(
            "INSERT INTO earnings_calendar "
            "(instrument, earnings_date, eps_forecast, eps_actual, event_type, "
            "notes, created_at) "
            "VALUES (:instrument, :earnings_date, :eps_forecast, :eps_actual, "
            ":event_type, NULL, :created_at) "
            "ON CONFLICT(instrument, earnings_date, event_type) DO UPDATE SET "
            "eps_forecast=excluded.eps_forecast, eps_actual=excluded.eps_actual",
            params,
        )
        n += 1
    return n


def backfill_earnings(instrument: str | None = None, db_path=None) -> dict[str, dict[str, Any]]:
    """Backfill 1 instrumen atau SEMUA di instrument_metadata. Return
    {instrument: {rows, source_flags}}."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        if instrument:
            targets = conn.execute(
                "SELECT instrument, market FROM instrument_metadata WHERE instrument = ?",
                (instrument.upper(),),
            ).fetchall()
        else:
            targets = conn.execute("SELECT instrument, market FROM instrument_metadata").fetchall()

    summary: dict[str, dict[str, Any]] = {}
    with get_connection(db_path) as conn:
        for t in targets:
            result = fetch_earnings_calendar(t["instrument"], t["market"])
            n = upsert_earnings_calendar(conn, t["instrument"], result["rows"])
            summary[t["instrument"]] = {"rows": n, "source_flags": result["source_flags"]}
        conn.commit()
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill earnings_calendar (Phase J+ J-7)")
    p.add_argument("--instrument", default=None,
                    help="Kosongkan utk semua instrumen di instrument_metadata")
    args = p.parse_args()
    summary = backfill_earnings(args.instrument)
    if not summary:
        print("[backfill_earnings] Tidak ada instrumen di instrument_metadata.")
    for inst, s in summary.items():
        print(f"[backfill_earnings] {inst}: {s['rows']} baris earnings")


if __name__ == "__main__":
    main()
