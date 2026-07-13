"""Kalibrasi per-market untuk engine S&R/signal (Phase J+ Build Contract
v1.3 §13, J-3). BEDA dari analysis/sizing.py (yang urus BUDGET posisi) --
modul ini urus TOLERANSI CLUSTERING ZONA S&R, supaya engine generik
(analysis/sr_zones.py) bisa dikalibrasi per pasar TANPA mengubah instrumen
lain sama sekali (BTC/GOLD/dst tetap ±0.5% default, TIDAK dipanggil lewat
modul ini, TIDAK terpengaruh).

`idx_price_fraction()` -- FAKTUAL (Peraturan Nomor II-A BEI, dikonfirmasi
riset publik Jul 2026), BUKAN judgment call/tebakan:
  harga < Rp200   -> fraksi Rp1
  Rp200 - Rp500   -> fraksi Rp2
  Rp500 - Rp2rb   -> fraksi Rp5
  Rp2rb - Rp5rb   -> fraksi Rp10
  >= Rp5rb        -> fraksi Rp25

`idx_zone_tolerance_pct()` -- **DRAFT, BELUM divalidasi bar-replay Giel**
(kontrak §13.1 poin 5: "engine teruji di BTC ≠ teruji di BBRI, validasi
per instrumen wajib sebelum lane naik ke TRADE"). `IDX_ZONE_TOLERANCE_TICKS
= 2` (2x fraksi harga sbg lebar toleransi) adalah angka DEFAULT yang perlu
dikonfirmasi/direvisi Giel setelah bar-replay -- BUKAN keputusan final,
beda dari `ARA_ARB_BUFFER_MULT` di analysis/sizing.py yang SUDAH terkunci
di §18. Dikembalikan sbg PERSENTASE relatif (sama unit dgn
analysis/sr_zones.py::CLUSTER_TOLERANCE) karena `detect_zones()` menerima
1 angka scalar per pemanggilan -- dihitung dari harga acuan (biasanya
close TERBARU), bukan per-level-harga sepanjang histori.
"""
from __future__ import annotations

IDX_PRICE_FRACTION_TIERS: list[tuple[float, float]] = [
    (200, 1), (500, 2), (2000, 5), (5000, 10), (float("inf"), 25),
]

# DRAFT -- lihat catatan modul di atas. Giel yang putuskan apakah 2 ticks
# ini cukup lebar/sempit setelah review bar-replay chart historis.
IDX_ZONE_TOLERANCE_TICKS = 2


def idx_price_fraction(price: float) -> float:
    """Fraksi harga resmi IDX (Peraturan No. II-A BEI) untuk 1 level harga."""
    for threshold, fraction in IDX_PRICE_FRACTION_TIERS:
        if price < threshold:
            return fraction
    return IDX_PRICE_FRACTION_TIERS[-1][1]


def idx_zone_tolerance_pct(reference_price: float, ticks: float = IDX_ZONE_TOLERANCE_TICKS) -> float:
    """Toleransi clustering S&R (persentase relatif) untuk instrumen IDX,
    dihitung dari fraksi harga pada `reference_price`. DRAFT -- lihat
    catatan `IDX_ZONE_TOLERANCE_TICKS` di atas."""
    if reference_price <= 0:
        raise ValueError("reference_price harus > 0")
    return (idx_price_fraction(reference_price) * ticks) / reference_price
