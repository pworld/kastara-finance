"""Scraper UMA (Unusual Market Activity) IDX (Phase J+ Build Contract v1.3,
J-11a). Sumber: laman berita UMA idx.co.id (SSR — di-render SERVER-SIDE,
BEDA dari laman "Financial Data and Ratio" yang client-side/JS-driven dan
gagal diriset — laman ini tidak butuh interaksi filter, cukup 1x GET).

Pola nama file pengumuman (dikonfirmasi live dari payload __NUXT__ halaman):
  YYYYMMDD-UMA_<TICKER>.pdf       -> UMA baru diumumkan BEI
  YYYYMMDD-WAS_UMA_<TICKER>.pdf   -> pernyataan susulan emiten ("Written
                                     Affirmation Statement") -- BUKAN
                                     dipastikan berarti UMA "selesai"
                                     (semantik resmi IDX utk WAS tidak
                                     dikonfirmasi 100% di riset ini), jadi
                                     TIDAK dipakai sbg sinyal "sudah aman".

Butuh curl_cffi (Cloudflare bot-management) -- TAPI beda dari
scrapers/idx_foreign_flow.py, laman ini tidak perlu handshake cookie
terpisah dulu (dikonfirmasi live, 1x GET langsung 200).

Cakupan: HANYA sepanjang histori yang IDX tampilkan di 1 laman ini (tidak
ada paginasi di scraper ini) -- cukup utk cek UMA baru-baru ini, bukan
arsip lengkap sepanjang masa.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from curl_cffi import requests as cffi_requests

from scrapers.base import SourceFlags, safe_call, today_wib

IDX_UMA_URL = "https://www.idx.co.id/id/berita/unusual-market-activity-uma"
_PDF_PATTERN = re.compile(r"(\d{8})-(WAS_)?UMA_([A-Z]{2,6})\.pdf")


def _fetch_uma_list() -> list[dict[str, Any]]:
    session = cffi_requests.Session(impersonate="chrome")
    resp = session.get(IDX_UMA_URL, timeout=20)
    resp.raise_for_status()
    items = []
    for m in _PDF_PATTERN.finditer(resp.text):
        date_str, is_was, ticker = m.groups()
        items.append({
            "date": datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d"),
            "ticker": ticker,
            "is_followup_statement": bool(is_was),
        })
    return items


def fetch_uma_announcements() -> dict[str, Any]:
    """Return {'items': [...], 'source_flags': {...}}. Tidak pernah raise."""
    flags = SourceFlags()
    items = safe_call("idx_uma", _fetch_uma_list, flags) or []
    return {"items": items, "source_flags": flags.as_dict()}


def uma_history_for(items: list[dict[str, Any]], instrument: str) -> list[dict[str, Any]]:
    """Semua entri utk 1 ticker, terbaru dulu."""
    rows = [i for i in items if i["ticker"] == instrument.upper()]
    return sorted(rows, key=lambda r: r["date"], reverse=True)


def is_recently_flagged(
    items: list[dict[str, Any]], instrument: str, as_of_date: str | None = None,
    window_days: int = 90,
) -> bool:
    """True kalau ADA entri UMA/WAS_UMA utk ticker ini dalam `window_days`
    terakhir dari `as_of_date`. Heuristik KONSERVATIF -- semantik "WAS"
    tidak dikonfirmasi berarti "selesai", jadi entri WAS TETAP dihitung
    (bukan diabaikan). Kalau Giel punya kejelasan semantik resmi IDX,
    logika ini perlu direvisi (dicatat sbg asumsi eksplisit)."""
    as_of = datetime.strptime(as_of_date or today_wib(), "%Y-%m-%d")
    cutoff = as_of - timedelta(days=window_days)
    for row in uma_history_for(items, instrument):
        if datetime.strptime(row["date"], "%Y-%m-%d") >= cutoff:
            return True
    return False


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_uma_announcements(), indent=2, default=str))
