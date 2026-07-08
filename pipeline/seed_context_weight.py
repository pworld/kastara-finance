"""Seed asset_context_weight — pembobotan driver per aset (Master Plan §4.3).

BTC dulu (plan_b.txt §7.7, pakai contoh persis dari Master Plan §4.3):
  net_liquidity=HIGH, etf_flow=HIGH, fear_greed=MED, dxy=MED

Idempotent: cek (instrument, driver) dulu, skip kalau sudah ada — bukan
INSERT OR IGNORE (tabel ini tidak punya UNIQUE index), jadi dedup manual.

Pakai:
    python -m pipeline.seed_context_weight
"""
from __future__ import annotations

from db.connection import get_connection, init_db

BTC_WEIGHTS = [
    ("net_liquidity", "HIGH", "Driver utama BTC — WALCL-RRP-TGA"),
    ("etf_flow", "HIGH", "Net flow ETF spot BTC, belum ada scraper otomatis (Phase D)"),
    ("fear_greed", "MED", "Sentimen pasar crypto, sudah ada di daily_market"),
    ("dxy", "MED", "Kekuatan dolar, korelasi negatif historis dgn BTC"),
]


def seed_instrument(conn, instrument: str, weights: list[tuple[str, str, str]]) -> int:
    """Insert (instrument, driver, weight, notes) kalau (instrument, driver)
    belum ada. Return jumlah baris baru."""
    inserted = 0
    for driver, weight, notes in weights:
        exists = conn.execute(
            "SELECT 1 FROM asset_context_weight WHERE instrument = ? AND driver = ?",
            (instrument, driver),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO asset_context_weight (instrument, driver, weight, notes) "
            "VALUES (?, ?, ?, ?)",
            (instrument, driver, weight, notes),
        )
        inserted += 1
    return inserted


def main() -> None:
    init_db()
    with get_connection() as conn:
        n = seed_instrument(conn, "BTC", BTC_WEIGHTS)
        conn.commit()
    print(f"[seed_context_weight] BTC: {n} baris baru ditambah.")


if __name__ == "__main__":
    main()
