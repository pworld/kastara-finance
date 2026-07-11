"""Seed instrument_metadata — universe Phase J+ (Build Contract v1.3).

Manual seed sementara (satu-per-satu, ditambah Giel by request) sampai ada
sistem input manual di dashboard (backlog, lihat docs/ROADMAP.md). BUKAN
scraper otomatis -- metadata seperti market_cap/free_float berubah lambat,
tidak perlu di-refresh tiap run_daily seperti daily_market.

Lane semua entry baru = INVEST (BUKAN TRADE), sesuai aturan kontrak §13.1
poin 5: "instrumen baru masuk lane INVEST/NONE dulu -> naik ke TRADE hanya
setelah validasi bar-replay". `lane_validated_at` sengaja NULL sampai
validasi itu terjadi (J-3, belum dikerjakan).

avg_volume_20d SENGAJA NULL saat seed -- ini field yang seharusnya dihitung
dari histori asset_ohlcv riil (pola sama `volume_ma20_for_instrument`,
indicators/calc.py), bukan pendekatan sekali-catat dari yfinance `info`
(yang default 3-bulan, bukan 20 hari persis). Baru terisi akurat setelah
J-2 (OHLCV universe -> asset_ohlcv) benar-benar jalan utk instrumen ini.

Pakai:
    python -m pipeline.seed_universe
"""
from __future__ import annotations

from typing import Any

from db.connection import get_connection, init_db
from scrapers.base import created_at

# instrument -> field instrument_metadata. Data market_cap/free_float dari
# yfinance .JK (dicek live saat penulisan ini, lihat docs/ROADMAP.md Phase
# J+ kickoff) -- akan basi seiring waktu, wajar utk field metadata lambat
# berubah, di-refresh manual/berkala, bukan tiap hari.
UNIVERSE: list[dict[str, Any]] = [
    {
        "instrument": "BBCA",
        "market": "IDX",
        "asset_class": "equity",
        # yfinance kasih klasifikasi GICS ("Financial Services"/"Banks -
        # Regional"), BUKAN IDX-IC -- dipakai apa adanya sampai ada
        # keputusan mapping ke IDX-IC.
        "sector": "Financial Services (GICS) -- belum di-mapping ke IDX-IC",
        "market_cap": 758_760_800_780_288.0,
        "free_float": 39.27,  # % -- floatShares/sharesOutstanding * 100 (yfinance)
        "avg_volume_20d": None,
        "lot_size": 100,
        "lane": "INVEST",       # BUKAN TRADE -- lihat docstring modul
        "lane_validated_at": None,
        "accounting_std": "PSAK",
        "is_financial": 1,      # bank -- playbook CAR/NPL/NIM/LDR (J7, belum dibangun)
        "fx_exposure": "domestik",
        "has_daily_limit": 1,   # ARA/ARB berlaku (saham IDX)
        "has_real_volume": 1,   # volume riil tersedia (bukan FX/Gold spot)
        "data_as_of_rule": None,
    },
]


def seed_instrument_metadata(conn, entries: list[dict[str, Any]]) -> int:
    """UPSERT tiap entry by instrument (PRIMARY KEY -> INSERT OR REPLACE
    idempotent, aman dijalankan ulang). Return jumlah baris diproses."""
    n = 0
    for entry in entries:
        row = {**entry, "created_at": created_at()}
        cols = ", ".join(row)
        placeholders = ", ".join(f":{c}" for c in row)
        conn.execute(
            f"INSERT OR REPLACE INTO instrument_metadata ({cols}) VALUES ({placeholders})",
            row,
        )
        n += 1
    return n


def main() -> None:
    init_db()
    with get_connection() as conn:
        n = seed_instrument_metadata(conn, UNIVERSE)
        conn.commit()
    print(f"[seed_universe] {n} instrumen diproses (upsert): "
          f"{', '.join(e['instrument'] for e in UNIVERSE)}")


if __name__ == "__main__":
    main()
