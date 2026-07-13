"""Orchestrator Emiten Grader (Phase J+ Build Contract v1.3, J-11b/c/d/e).

Baca fundamentals_quarterly TERBARU + UMA live (scrapers/idx_uma.py) per
instrumen di `instrument_metadata` -> hitung grade (analysis/grader.py,
DRAFT v1, lihat docstring modul itu) -> UPSERT `emiten_grade` + catat
`grader_log` kalau kuadran BERUBAH dari grade sebelumnya (anti-overtuning
— audit trail eksplisit, bukan revisi diam-diam, kontrak §16/J-11e).

Dijalankan manual/berkala (fundamental + UMA sama-sama berubah lambat,
BUKAN bagian run_daily harian) — pola sama pipeline/backfill_fundamentals.py.

Pakai:
    python -m pipeline.run_grader              # semua instrumen
    python -m pipeline.run_grader --instrument BBCA
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from analysis.grader import grade_emiten
from db.connection import get_connection, init_db
from scrapers.base import created_at, today_wib
from scrapers.idx_uma import fetch_uma_announcements, is_recently_flagged


def _latest_fundamentals(conn, instrument: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM fundamentals_quarterly WHERE instrument = ? "
        "ORDER BY quarter_end DESC LIMIT 1", (instrument,),
    ).fetchone()
    return dict(row) if row else None


def _latest_grade(conn, instrument: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM emiten_grade WHERE instrument = ? "
        "ORDER BY graded_at DESC, id DESC LIMIT 1", (instrument,),
    ).fetchone()
    return dict(row) if row else None


def upsert_grade(conn, instrument: str, graded_at: str, result: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO emiten_grade (instrument, graded_at, fund_score, integrity_flags, "
        "quadrant, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (instrument, graded_at, result["fund_score"], json.dumps(result["integrity_flags"]),
         result["quadrant"], None, created_at()),
    )


def log_grade_change(
    conn, instrument: str, date: str, old_quadrant: str | None, new_quadrant: str, reason: str,
) -> None:
    conn.execute(
        "INSERT INTO grader_log (instrument, date, old_grade, new_grade, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (instrument, date, old_quadrant, new_quadrant, reason, created_at()),
    )


def run_grader(instrument: str | None = None, db_path=None) -> dict[str, dict[str, Any]]:
    init_db(db_path)
    uma_result = fetch_uma_announcements()
    uma_items = uma_result["items"]

    with get_connection(db_path) as conn:
        if instrument:
            targets = conn.execute(
                "SELECT instrument, is_financial FROM instrument_metadata WHERE instrument = ?",
                (instrument.upper(),),
            ).fetchall()
        else:
            targets = conn.execute(
                "SELECT instrument, is_financial FROM instrument_metadata"
            ).fetchall()

    today = today_wib()
    summary: dict[str, dict[str, Any]] = {}
    with get_connection(db_path) as conn:
        for t in targets:
            inst = t["instrument"]
            latest_q = _latest_fundamentals(conn, inst)
            uma_active = is_recently_flagged(uma_items, inst, as_of_date=today)

            result = grade_emiten(latest_q, bool(t["is_financial"]), uma_active)
            prev = _latest_grade(conn, inst)
            upsert_grade(conn, inst, today, result)

            if prev is None or prev["quadrant"] != result["quadrant"]:
                log_grade_change(
                    conn, inst, today, prev["quadrant"] if prev else None,
                    result["quadrant"],
                    "initial grade" if prev is None else "recomputed (auto run_grader)",
                )
            summary[inst] = result
        conn.commit()
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description="Emiten Grader (Phase J+ J-11)")
    p.add_argument("--instrument", default=None,
                    help="Kosongkan utk semua instrumen di instrument_metadata")
    args = p.parse_args()
    summary = run_grader(args.instrument)
    if not summary:
        print("[run_grader] Tidak ada instrumen di instrument_metadata.")
    for inst, r in summary.items():
        print(f"[run_grader] {inst}: score={r['fund_score']} quadrant={r['quadrant']} "
              f"flags={r['integrity_flags']}")


if __name__ == "__main__":
    main()
