"""Emiten Grader engine — rubrik dua sumbu (Phase J+ Build Contract v1.3,
Master Plan §12 "Modul Emiten Grader"). **DRAFT v1** -- dokumen sumber
"v1.1" berisi rubrik detail resmi Giel TIDAK tersedia saat modul ini
ditulis, jadi disusun dari konsep umum kontrak (dua sumbu: fund_score
0-100 × integrity flags -> kuadran). Ditandai jelas di sini supaya gampang
dikoreksi kalau meleset dari spesifikasi asli Giel -- pola sama dgn 5
tabel Phase J+ yang sebelumnya juga ditandai draft.

Axis 1 -- fund_score (0-100): dihitung dari 1 baris `fundamentals_quarterly`
TERBARU. Playbook BEDA utk bank (`is_financial=1`) vs non-bank -- kontrak
menyebut RIVAN slice butuh baca rasio bank berbeda dari korporasi biasa.
4 komponen @25 poin (skema biner ada/tidak, BUKAN skala kontinu -- lebih
sederhana & transparan utk v1, gampang dijelaskan kenapa skor segitu).

Axis 2 -- integrity_flags: list string, tiap flag punya severity RED/ORANGE.
**RED = veto ke kuadran AVOID** tidak peduli fund_score setinggi apa pun
("grader adalah REM di momen tertarik, bukan stempel" — kontrak §16).
Sumber flag yang SUDAH otomatis: UMA_ACTIVE (scrapers/idx_uma.py),
LOW_CONFIDENCE_FUNDAMENTALS, NEGATIVE_NET_INCOME, NEGATIVE_EQUITY (dari
fundamentals_quarterly langsung). **BELUM otomatis** (J-11a lanjutan,
riset lebih jauh diperlukan): papan pemantauan khusus, riwayat suspensi 12
bulan (J8-J10 kontrak) -- TIDAK difabrikasi di sini; kalau Giel punya
datanya, masukkan manual lewat parameter `extra_flags`.

Kuadran (dua sumbu -> 4 kategori):
  AVOID       -- ada minimal 1 RED flag (override, prioritas tertinggi)
  INVESTABLE  -- fund_score >= 70, tanpa flag ORANGE/RED
  WATCH       -- fund_score 40-69 TANPA red, ATAU >=70 tapi ada ORANGE
  SPECULATIVE -- fund_score < 40, tanpa RED
"""
from __future__ import annotations

from typing import Any

RED_FLAGS = {"UMA_ACTIVE", "NEGATIVE_NET_INCOME", "NEGATIVE_EQUITY"}
ORANGE_FLAGS = {"LOW_CONFIDENCE_FUNDAMENTALS"}

INVESTABLE_THRESHOLD = 70
WATCH_THRESHOLD = 40


def compute_fund_score(latest_quarter: dict[str, Any], is_financial: bool) -> float:
    """Skor 0-100 dari 1 baris fundamentals_quarterly TERBARU. 4 komponen
    @25 poin, kriteria beda bank vs non-bank."""
    score = 0.0
    revenue = latest_quarter.get("revenue")
    net_income = latest_quarter.get("net_income")
    ocf = latest_quarter.get("operating_cash_flow")
    fcf = latest_quarter.get("free_cash_flow")
    nii = latest_quarter.get("net_interest_income")
    equity = latest_quarter.get("total_equity")
    # revenue > 0 (bukan cuma != 0) -- kalau revenue negatif, net_income/revenue
    # bisa keliru kelihatan "positif" (mis. -500jt / -1 = angka besar positif)
    # walau keduanya sama-sama tanda buruk. Margin cuma valid dgn basis positif.
    net_margin = (
        net_income / revenue if (revenue is not None and revenue > 0 and net_income is not None) else None
    )

    if is_financial:
        if net_income is not None and net_income > 0:
            score += 25
        if nii is not None and nii > 0:
            score += 25
        if net_margin is not None and net_margin > 0:
            score += 25
        if equity is not None and equity > 0:
            score += 25
    else:
        if revenue is not None and revenue > 0:
            score += 25
        if net_margin is not None and net_margin > 0:
            score += 25
        if ocf is not None and ocf > 0:
            score += 25
        if fcf is not None and fcf > 0:
            score += 25
    return score


def compute_integrity_flags(
    latest_quarter: dict[str, Any] | None, uma_active: bool,
    extra_flags: list[str] | None = None,
) -> list[str]:
    """Flag otomatis (dari fundamentals + UMA) + extra_flags manual (mis.
    papan pemantauan/suspensi yang belum ada scraper-nya)."""
    flags: list[str] = []
    if uma_active:
        flags.append("UMA_ACTIVE")
    if latest_quarter:
        if latest_quarter.get("confidence") == "LOW_CONFIDENCE":
            flags.append("LOW_CONFIDENCE_FUNDAMENTALS")
        net_income = latest_quarter.get("net_income")
        if net_income is not None and net_income < 0:
            flags.append("NEGATIVE_NET_INCOME")
        equity = latest_quarter.get("total_equity")
        if equity is not None and equity < 0:
            flags.append("NEGATIVE_EQUITY")
    if extra_flags:
        flags.extend(extra_flags)
    return flags


def compute_quadrant(fund_score: float, flags: list[str]) -> str:
    if any(f in RED_FLAGS for f in flags):
        return "AVOID"
    has_orange = any(f in ORANGE_FLAGS for f in flags)
    if fund_score >= INVESTABLE_THRESHOLD:
        return "WATCH" if has_orange else "INVESTABLE"
    if fund_score >= WATCH_THRESHOLD:
        return "WATCH"
    return "SPECULATIVE"


def grade_emiten(
    latest_quarter: dict[str, Any] | None, is_financial: bool, uma_active: bool,
    extra_flags: list[str] | None = None,
) -> dict[str, Any]:
    """Return {'fund_score', 'integrity_flags', 'quadrant'}.
    `latest_quarter=None` (belum ada data fundamental) -> fund_score=0,
    turun ke SPECULATIVE (BUKAN AVOID -- data kosong beda dari red flag
    aktif; tidak boleh disamakan)."""
    fund_score = compute_fund_score(latest_quarter, is_financial) if latest_quarter else 0.0
    flags = compute_integrity_flags(latest_quarter, uma_active, extra_flags)
    quadrant = compute_quadrant(fund_score, flags)
    return {"fund_score": fund_score, "integrity_flags": flags, "quadrant": quadrant}
