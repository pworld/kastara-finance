"""Backfill fundamentals_quarterly (Phase J+ Build Contract v1.3, J-4).

Gerbang G3 dijawab Giel (13 Jul 2026): "bisa yfinance atau langsung idx" --
yfinance dipakai sbg sumber (scrapers/fundamentals_yf.py). Target 8 kuartal
per instrumen; kalau kurang, baris disimpan dgn confidence='LOW_CONFIDENCE'
(BUKAN ditolak, kontrak §16 poin 2).

Beda dari pipeline/run_daily.py: fundamentals berubah PER KUARTAL, bukan
harian -- dijalankan manual/berkala (bukan bagian run_daily), pola sama
`pipeline/seed_universe.py` (dijalankan saat perlu, bukan tiap pagi).

Pakai:
    python -m pipeline.backfill_fundamentals              # semua instrumen
    python -m pipeline.backfill_fundamentals --instrument BBCA
"""
from __future__ import annotations

import argparse
from typing import Any

from db.connection import get_connection, init_db
from scrapers.base import created_at
from scrapers.fundamentals_yf import fetch_fundamentals_quarterly


def upsert_fundamentals_quarterly(conn, instrument: str, rows: list[dict[str, Any]]) -> int:
    """UPSERT by (instrument, quarter_end) -- natural key UNIQUE constraint
    sudah ada di schema.sql (idx implisit lewat UNIQUE(instrument,
    quarter_end)). Return jumlah baris diproses."""
    n = 0
    for row in rows:
        params = {**row, "instrument": instrument, "source": "yfinance", "created_at": created_at()}
        conn.execute(
            "INSERT INTO fundamentals_quarterly "
            "(instrument, quarter_end, revenue, net_income, eps, net_interest_income, "
            "total_equity, total_assets, operating_cash_flow, free_cash_flow, source, "
            "confidence, created_at) "
            "VALUES (:instrument, :quarter_end, :revenue, :net_income, :eps, "
            ":net_interest_income, :total_equity, :total_assets, :operating_cash_flow, "
            ":free_cash_flow, :source, :confidence, :created_at) "
            "ON CONFLICT(instrument, quarter_end) DO UPDATE SET "
            "revenue=excluded.revenue, net_income=excluded.net_income, eps=excluded.eps, "
            "net_interest_income=excluded.net_interest_income, "
            "total_equity=excluded.total_equity, total_assets=excluded.total_assets, "
            "operating_cash_flow=excluded.operating_cash_flow, "
            "free_cash_flow=excluded.free_cash_flow, confidence=excluded.confidence",
            params,
        )
        n += 1
    return n


def backfill_fundamentals(instrument: str | None = None, db_path=None) -> dict[str, dict[str, Any]]:
    """Backfill 1 instrumen (kalau `instrument` diisi) atau SEMUA instrumen
    di instrument_metadata. Return {instrument: {quarters, confidence, source_flags}}."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        if instrument:
            targets = conn.execute(
                "SELECT instrument, market, is_financial FROM instrument_metadata "
                "WHERE instrument = ?", (instrument.upper(),),
            ).fetchall()
        else:
            targets = conn.execute(
                "SELECT instrument, market, is_financial FROM instrument_metadata"
            ).fetchall()

    summary: dict[str, dict[str, Any]] = {}
    with get_connection(db_path) as conn:
        for t in targets:
            result = fetch_fundamentals_quarterly(
                t["instrument"], t["market"], bool(t["is_financial"])
            )
            n = upsert_fundamentals_quarterly(conn, t["instrument"], result["rows"])
            summary[t["instrument"]] = {
                "quarters": n,
                "confidence": result["rows"][0]["confidence"] if result["rows"] else None,
                "source_flags": result["source_flags"],
            }
        conn.commit()
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill fundamentals_quarterly (Phase J+ J-4)")
    p.add_argument("--instrument", default=None,
                    help="Kosongkan utk semua instrumen di instrument_metadata")
    args = p.parse_args()
    summary = backfill_fundamentals(args.instrument)
    if not summary:
        print("[backfill_fundamentals] Tidak ada instrumen di instrument_metadata.")
    for inst, s in summary.items():
        print(f"[backfill_fundamentals] {inst}: {s['quarters']} kuartal ({s['confidence']})")


if __name__ == "__main__":
    main()
