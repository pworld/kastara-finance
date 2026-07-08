"""Indikator teknikal untuk S&R/signal detector (Phase B).

Beda dengan `indicators/calc.py` (Phase A): itu "calculated fields" yang
dipanggil tiap hari oleh pipeline (net_liquidity, volume_ma20 partial-window
buat dashboard). Modul ini murni untuk analysis engine — MA di sini WAJIB
full window (return None kalau data kurang), karena dipakai untuk baca
trend/S&R, bukan buat ditampilkan apa adanya.

Semua fungsi generic per-instrument (tidak hardcode BTC) — orchestrator
(`pipeline/run_analysis.py`) yang membatasi ke instrument tertentu.
"""
from __future__ import annotations


def rolling_ma(values: list[float | None], period: int) -> list[float | None]:
    """MA rolling untuk SETIAP index (bukan cuma nilai terakhir seperti
    `moving_average`). Dipakai orchestrator untuk re-derive volume_ma20 dari
    histori penuh -- kolom volume_ma20 di asset_ohlcv cuma keisi buat hari
    yang diproses run_daily.py; baris hasil backfill historis NULL semua.

    None di posisi manapun kalau window belum penuh ATAU ada nilai None di
    window itu (konsisten dengan `moving_average` -- MA butuh window utuh).
    """
    result: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < period:
            result.append(None)
            continue
        window = values[i + 1 - period : i + 1]
        result.append(None if any(v is None for v in window) else sum(window) / period)
    return result


def moving_average(closes: list[float], period: int) -> float | None:
    """Simple moving average dari `period` nilai TERAKHIR di `closes`.

    None kalau data < period (bukan partial-average -- MA teknikal harus
    full window supaya valid buat baca trend).
    """
    if len(closes) < period:
        return None
    window = closes[-period:]
    return sum(window) / period


def ma_stack_order(
    ma20: float | None, ma50: float | None,
    ma100: float | None, ma200: float | None,
) -> str:
    """Urutan MA -> 'bullish' | 'bearish' | 'mixed'.

    bullish: MA20 > MA50 > MA100 > MA200 (uptrend, stack rapi menurun)
    bearish: urutan kebalikan (MA20 < MA50 < MA100 < MA200)
    mixed  : selain itu, atau ada MA yang None (data belum cukup)
    """
    vals = (ma20, ma50, ma100, ma200)
    if any(v is None for v in vals):
        return "mixed"
    if ma20 > ma50 > ma100 > ma200:
        return "bullish"
    if ma20 < ma50 < ma100 < ma200:
        return "bearish"
    return "mixed"


def volume_ratio(volume_today: float | None, volume_ma20: float | None) -> float | None:
    """volume_today / volume_ma20. None kalau salah satu None atau ma20=0."""
    if volume_today is None or not volume_ma20:
        return None
    return volume_today / volume_ma20


def is_breakout_volume(ratio: float | None) -> bool:
    """True kalau volume_ratio > 1.5 (Master Plan §7: breakout volume confirmed)."""
    if ratio is None:
        return False
    return ratio > 1.5


def is_volume_present(ratio: float | None, threshold: float = 0.8) -> bool:
    """Volume retest 'hadir, tidak sepi' -> ratio >= threshold (default 0.8,
    dikunci di plan_b.txt §7.2)."""
    if ratio is None:
        return False
    return ratio >= threshold
