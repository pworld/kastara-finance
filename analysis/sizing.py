"""Sizing & lot quantization engine (Phase J+ Build Contract v1.3, §14).

Alur: budget risiko per trade (capital × MAX_RISK_PCT) ÷ jarak entry-SL =
unit ideal → **BULATKAN KE BAWAH** ke kelipatan `lot_size`. Risiko aktual
harus SELALU ≤ rencana, TIDAK PERNAH sebaliknya (kontrak §14 poin 1 —
pembulatan ke atas DILARANG).

MAX_RISK_PCT = 2.5 -- keputusan eksplisit Giel (13 Jul 2026), BUKAN
default yang ditebak/dihitung.

Kalau budget tidak cukup utk 1 lot/unit -> `skip=True`,
`skip_reason='RISK_CAPACITY_EXCEEDED'` (kontrak §14 poin 2, status setara
`is_valid=0` di analysis/signals.py — TETAP dilaporkan, bukan silent-drop).

DILARANG KERAS (kontrak §14 poin 3): modul ini TIDAK PUNYA parameter atau
jalur apa pun untuk mengubah SL supaya lot "muat" -- SL tetap struktural
dari zona (analysis/signals.py), sizing yang menyesuaikan mengikuti. Kalau
tidak muat kapasitas, jawabannya SKIP, bukan geser SL.

`capital` WAJIB diisi eksplisit oleh caller -- modul ini TIDAK menyimpan
atau menebak modal Giel (lihat .env.example RISK_CAPITAL_IDR/RISK_CAPITAL_USD,
caller yang baca env itu, bukan modul ini).

`lot_size` dari `instrument_metadata.lot_size`: IDX=100 (kuantisasi lot
penuh berlaku), US=1 atau 0 (IBKR fractional -- kontrak §14 poin 5: rule
RISK_CAPACITY_EXCEEDED "hampir hanya menyala untuk IDX").
"""
from __future__ import annotations

import math
from typing import Any

MAX_RISK_PCT = 2.5  # keputusan eksplisit Giel, 13 Jul 2026


def suggest_position_size(
    entry_price: float, sl_price: float, capital: float, lot_size: int,
    max_risk_pct: float = MAX_RISK_PCT,
) -> dict[str, Any]:
    """Return dict berisi ukuran posisi hasil pembulatan-bawah, atau skip
    kalau kapasitas risiko tidak cukup utk 1 lot/unit.

    `lot_size <= 0` diperlakukan sbg fractional penuh (US/IBKR) -- unit
    ideal dipakai apa adanya (tidak dibulatkan ke kelipatan apa pun).
    """
    if entry_price == sl_price:
        raise ValueError("entry_price dan sl_price tidak boleh sama (jarak risiko 0)")
    if capital <= 0:
        raise ValueError("capital harus > 0")

    risk_per_unit = abs(entry_price - sl_price)
    risk_budget = capital * (max_risk_pct / 100)
    ideal_units = risk_budget / risk_per_unit

    step = lot_size if lot_size and lot_size > 0 else 0
    suggested_units = math.floor(ideal_units / step) * step if step > 0 else ideal_units

    if suggested_units <= 0:
        return {
            "skip": True,
            "skip_reason": "RISK_CAPACITY_EXCEEDED",
            "risk_budget": risk_budget,
            "risk_per_unit": risk_per_unit,
            "suggested_units": 0,
            "actual_risk": 0.0,
        }

    return {
        "skip": False,
        "skip_reason": None,
        "risk_budget": risk_budget,
        "risk_per_unit": risk_per_unit,
        "suggested_units": suggested_units,
        "actual_risk": suggested_units * risk_per_unit,
    }
