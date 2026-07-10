"""Calculated fields (bukan data mentah dari API).

- net_liquidity = walcl - rrp - tga
- volume_ma20   = rata-rata 20 nilai volume terakhir (butuh histori di DB)
- compare_from_series = delta Hari/Minggu/Bulan/Tahun (dipakai Panel 1
  web/app.py DAN pipeline/compose_persona_context.py Track D -- dipindah ke
  sini dari web/app.py biar bisa dipakai bareng tanpa pipeline import dari
  web (layering salah arah))
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from db.connection import get_connection

# Jarak hari per periode compare -- "week"=7 dst BUKAN exact calendar
# week/month, cuma pendekatan hari mundur dari tanggal target (cukup akurat
# utk delta pasar, tidak perlu presisi kalender kabisat/dll).
COMPARE_PERIODS = {"day": 1, "week": 7, "month": 30, "year": 365}


def compare_from_series(series: list[tuple[str, float]], latest_date: str, cur_val) -> dict:
    """Bandingkan `cur_val` (hari ini) vs D-1/W-1/M-1/Y-1 dari `series`
    ([(date, value), ...] terurut DESC baru->lama). Cari titik pertama
    dengan date <= target (bukan exact match) -- gap kalender wajar krn
    run_daily manual / weekend tidak ada data equity."""
    compare: dict[str, Any] = {}
    latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
    for period, days_ago in COMPARE_PERIODS.items():
        target = (latest_dt - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        past_date, past_val = None, None
        for d, v in series:
            if d <= target and v is not None:
                past_date, past_val = d, v
                break
        if cur_val is None or past_val is None:
            compare[period] = None
            continue
        delta = cur_val - past_val
        compare[period] = {
            "past_value": past_val,
            "past_date": past_date,
            "delta": delta,
            "pct": (delta / past_val * 100) if past_val else None,
        }
    return compare


def net_liquidity(
    walcl: Optional[float], rrp: Optional[float], tga: Optional[float]
) -> Optional[float]:
    """net_liquidity = WALCL - RRP - TGA. None kalau salah satu komponen None."""
    if walcl is None or rrp is None or tga is None:
        return None
    return walcl - rrp - tga


def volume_ma20_from_values(volumes: list[float]) -> Optional[float]:
    """MA20 dari list volume (paling lama -> paling baru). None kalau kosong.

    Kalau data < 20, hitung rata-rata dari yang tersedia (partial MA).
    """
    vals = [v for v in volumes if v is not None]
    if not vals:
        return None
    window = vals[-20:]
    return sum(window) / len(window)


def volume_ma20_for_instrument(
    instrument: str, as_of_date: str, db_path=None
) -> Optional[float]:
    """Hitung MA20 volume dari asset_ohlcv untuk instrument s/d tanggal tertentu.

    Ambil 20 baris volume terakhir (date <= as_of_date), termasuk hari ini.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT volume FROM asset_ohlcv "
            "WHERE instrument = ? AND date <= ? AND volume IS NOT NULL "
            "ORDER BY date DESC LIMIT 20",
            (instrument, as_of_date),
        ).fetchall()
    if not rows:
        return None
    vols = [r["volume"] for r in rows]  # desc -> tidak masalah untuk rata-rata
    return sum(vols) / len(vols)
