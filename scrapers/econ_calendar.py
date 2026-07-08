"""Economic calendar scraper — event MASA DEPAN (FOMC/CPI/NFP/RDG BI/dll).

SUMBER: ForexFactory (via endpoint JSON tidak resmi yang dipakai widget
kalendernya, di-hosting Fair Economy — gratis, no key). VERIFIKASI endpoint
masih aktif saat implementasi (sesuai plan.txt) — endpoint tidak resmi bisa
berubah/mati sewaktu-waktu; kalau begitu, tandai fail di source_flags dan
pipeline tetap lanjut, jangan crash.

Trading Economics **sengaja tidak dipakai**: API resminya butuh key
berbayar untuk cakupan penuh (guest key cuma kasih beberapa negara sample)
— melanggar aturan "JANGAN pakai API berbayar" di plan.txt.

Keterbatasan sumber ini yang perlu diketahui:
  - Hanya mencakup rolling window "minggu ini" (tidak ada histori/minggu depan
    di endpoint yang sama) -> di-refresh tiap kali scraper jalan, event lama
    otomatis tidak muncul lagi.
  - Tidak menyediakan kolom "actual" (hasil rilis) -> kolom itu tetap NULL
    dari scraper ini; pengisian actual perlu sumber lain atau manual.

Output ke econ_calendar: event_date, event_time, event_name, country,
importance (HIGH/MED/LOW), forecast, previous. is_watched DEFAULT 0 (Giel
flag manual).

Idempotent: UPSERT by (event_date, event_name, country) — event yang sama
di-refresh (forecast bisa berubah mendekati rilis), bukan duplikat baris.

Acceptance:
  - importance selalu salah satu HIGH/MED/LOW
  - event_date tersimpan YYYY-MM-DD (WIB), event_time HH:MM (WIB)
  - Endpoint gagal -> source_flags fail, list kosong, pipeline lanjut
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from scrapers.base import SourceFlags, WIB, http_get_json, safe_call, today_wib

FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Impact sumber -> importance kita. "Holiday" bukan event terukur -> LOW.
IMPACT_MAP = {"high": "HIGH", "medium": "MED", "low": "LOW", "holiday": "LOW"}

# Kode mata uang sumber -> kode negara 2-huruf, biar konsisten gaya "US/ID/JP".
COUNTRY_MAP = {
    "USD": "US", "EUR": "EU", "GBP": "GB", "JPY": "JP", "CHF": "CH",
    "AUD": "AU", "CAD": "CA", "NZD": "NZ", "CNY": "CN",
}


def _normalize(raw: str | None) -> str | None:
    """Kosongkan string kosong jadi None (forecast/previous sering '')."""
    if raw is None:
        return None
    raw = raw.strip()
    return raw or None


def _parse_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Ubah 1 entri JSON ForexFactory jadi row siap-UPSERT econ_calendar."""
    title = (raw.get("title") or "").strip()
    date_str = raw.get("date")
    if not title or not date_str:
        return None
    dt = datetime.fromisoformat(date_str).astimezone(WIB)
    importance = IMPACT_MAP.get((raw.get("impact") or "").strip().lower(), "LOW")
    country = raw.get("country") or ""
    return {
        "event_date": dt.strftime("%Y-%m-%d"),
        "event_time": dt.strftime("%H:%M"),
        "event_name": title,
        "country": COUNTRY_MAP.get(country, country),
        "importance": importance,
        "forecast": _normalize(raw.get("forecast")),
        "previous": _normalize(raw.get("previous")),
        "actual": None,  # sumber ini tidak menyediakan actual (lihat docstring)
    }


def _fetch_ff_calendar() -> list[dict[str, Any]]:
    raw_items = http_get_json(FF_CALENDAR_URL)
    if not isinstance(raw_items, list):
        raise ValueError("format ForexFactory calendar tidak sesuai ekspektasi")
    events = [_parse_event(r) for r in raw_items]
    return [e for e in events if e is not None]


def fetch_econ_calendar() -> dict[str, Any]:
    """Return dict: 'items' (list event) + 'source_flags'. Tidak pernah raise."""
    flags = SourceFlags()
    items = safe_call("forexfactory_calendar", _fetch_ff_calendar, flags, default=[])
    return {"items": items or [], "source_flags": flags.as_dict()}


if __name__ == "__main__":
    out = fetch_econ_calendar()
    print(f"{len(out['items'])} event. flags={out['source_flags']}")
    for it in out["items"][:10]:
        print(f"  [{it['importance']:>4}] {it['event_date']} {it['event_time']} "
              f"{it['country']}: {it['event_name']}")
    print(f"(dijalankan {today_wib()})")
