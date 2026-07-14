"""Investing.com economic calendar scraper — pass KEDUA untuk isi `actual`
event HIGH-importance (bintang 3), MELENGKAPI (bukan menggantikan)
scrapers/econ_calendar.py (ForexFactory).

KENAPA ADA DUA SUMBER: ForexFactory tidak pernah menyediakan kolom `actual`
(dicek langsung ke raw JSON -- field itu memang tidak ada di respons).
Investing.com MENERBITKAN `actual` di hari yang sama event rilis, tapi
navigasi tanggal ("Yesterday"/"Tomorrow") di halamannya murni AJAX
client-side ke endpoint yang tidak ketemu (riset via curl_cffi -- lihat
docs/ROADMAP.md). Solusinya: scrape halaman DEFAULT ("hari ini" versi
investing.com) di SORE/MALAM hari lewat cron KEDUA yang terpisah dari
run_daily pagi (lihat pipeline/run_investing_actual.py) -- pada jam segitu
event HIGH hari itu biasanya sudah rilis actual-nya, jadi navigasi tanggal
tidak dibutuhkan sama sekali.

PENTING -- pakai `curl_cffi`, BUKAN `requests` biasa, alasan SAMA seperti
scrapers/idx_foreign_flow.py (Cloudflare, TLS/JA3 fingerprint check gagal di
requests biasa). investing.com JAUH lebih agresif soal rate-limit dibanding
idx.co.id/ForexFactory -- riset langsung sempat kena HTTP 429 yang TIDAK
pulih meski nunggu 2 menit setelah cuma ~5-6 request cepat berturut-turut.
Makanya scraper ini SENGAJA cuma 1x GET per pemanggilan, dijadwalkan 1x/hari
sore (bukan digabung ke run_daily pagi, dan JANGAN dipanggil berulang untuk
backfill agresif -- risiko kena block lebih besar dari manfaatnya).

HANYA importance HIGH (bintang 3) yang diambil -- sesuai permintaan awal
("hanya bintang 3 dari investing.com"), sekaligus mengecilkan volume
matching/write-back di pipeline/run_investing_actual.py.

Struktur HTML (Next.js SSR investing.com, dikonfirmasi live per Jul 2026):
  - 1 baris <tr id="{eventTemplateId}-{releaseInstanceId}-{Country}-{idx}">
    per event, class mengandung "datatable-v2_row".
  - Importance: 3 <svg> PERTAMA tiap baris (baris ini render 6 svg total --
    duplikat kedua untuk layout mobile/desktop -- HARUS di-slice [:3],
    kalau tidak jumlah bintang aktif jadi 2x lipat/salah hitung).
    class "opacity-60" = bintang aktif/terisi.
  - Country: <span data-test="flag-XX"> -- XX dipakai APA ADANYA (2 huruf,
    sudah selaras gaya kode negara sumber lain: US/EU/GB/JP/dst).
  - Nama event: <a href=".../economic-calendar/{slug}-{id}">{nama}</a>.
  - Act/Cons/Prev: diambil dari teks baris via regex label "Act : .. Cons :
    .. Prev. : .." -- label ini HANYA muncul di blok mobile (disembunyikan
    lewat CSS di layar besar, tapi tetap ada di HTML), jadi regex atas teks
    gabungan 1 baris aman dipakai tanpa perlu bedah struktur kolom desktop.
  - Tanggal: SATU div per halaman (default view = 1 hari saja), format
    "Tuesday, July 14, 2026" -- di-parse ke YYYY-MM-DD, dipakai untuk SEMUA
    baris di halaman itu (bukan per-baris, karena tidak ada tanggal per-row).

Output: list item {event_date, country, event_name, actual} -- HANYA event
HIGH yang actual-nya SUDAH terisi (yang masih kosong/"-"/"--" di-skip, bukan
dikirim sebagai None). Matching ke baris econ_calendar yang sudah ada +
UPDATE-nya dilakukan di pipeline/run_investing_actual.py (BUKAN di sini --
scraper ini murni fetch+parse tanpa akses DB, pola sama semua scraper lain).

Acceptance:
  - Tidak pernah raise; gagal (network/Cloudflare/struktur berubah) ->
    source_flags fail, items kosong, caller (pipeline) tetap lanjut.
  - Importance yang di-return SELALU 'HIGH' (LOW/MED sudah difilter di sini).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from scrapers.base import SourceFlags, safe_call

INVESTING_CALENDAR_URL = "https://www.investing.com/economic-calendar/"
INVESTING_TIMEOUT = 20

_DATE_RE = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"(\w+) (\d{1,2}), (\d{4})"
)
_ACP_RE = re.compile(
    r"Act\s*:\s*(?P<act>\S+)\s*Cons\s*:\s*(?P<cons>\S+)\s*Prev\.?\s*:\s*(?P<prev>\S+)"
)
_EMPTY_VALUES = {"-", "--", ""}


def _page_event_date(soup: BeautifulSoup) -> str | None:
    """Tanggal satu-satunya di halaman default (bisa beda 1 hari dari WIB
    tergantung jam scrape -- lihat catatan zona waktu di docstring modul)."""
    for text in soup.find_all(string=_DATE_RE):
        m = _DATE_RE.search(text)
        if m:
            try:
                dt = datetime.strptime(f"{m.group(2)} {m.group(3)} {m.group(4)}", "%B %d %Y")
            except ValueError:
                continue
            return dt.strftime("%Y-%m-%d")
    return None


def _star_count(row: Any) -> int:
    """Bintang aktif dari 3 svg PERTAMA (lihat catatan duplikat di docstring)."""
    svgs = row.find_all("svg")[:3]
    return sum(1 for s in svgs if "opacity-60" in (s.get("class") or []))


def _parse_row(row: Any, event_date: str) -> dict[str, Any] | None:
    """1 baris -> event HIGH ber-actual, atau None kalau bukan HIGH/actual kosong."""
    if _star_count(row) != 3:
        return None
    m = _ACP_RE.search(row.get_text(" ", strip=True))
    if not m:
        return None
    actual = m.group("act").strip()
    if actual in _EMPTY_VALUES:
        return None
    flag = row.select_one("span[data-test^='flag-']")
    country = flag.get("data-test", "").removeprefix("flag-").upper() if flag else ""
    link = row.select_one("a[href*='economic-calendar/']")
    name = link.get_text(" ", strip=True) if link else ""
    if not name or not country:
        return None
    return {"event_date": event_date, "country": country, "event_name": name, "actual": actual}


def _fetch_investing_rows() -> list[dict[str, Any]]:
    session = cffi_requests.Session(impersonate="chrome")
    resp = session.get(INVESTING_CALENDAR_URL, timeout=INVESTING_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    event_date = _page_event_date(soup)
    if event_date is None:
        raise ValueError("tanggal halaman investing.com tidak ketemu (struktur halaman berubah?)")
    rows = [r for r in soup.select("tr[id]") if "datatable-v2_row" in " ".join(r.get("class", []))]
    items = [_parse_row(r, event_date) for r in rows]
    return [it for it in items if it is not None]


def fetch_investing_actuals() -> dict[str, Any]:
    """Return dict: 'items' (list event HIGH ber-actual) + 'source_flags'.
    Tidak pernah raise."""
    flags = SourceFlags()
    items = safe_call("investing_calendar_actual", _fetch_investing_rows, flags, default=[])
    return {"items": items or [], "source_flags": flags.as_dict()}


if __name__ == "__main__":
    out = fetch_investing_actuals()
    print(f"{len(out['items'])} event HIGH ber-actual. flags={out['source_flags']}")
    for it in out["items"][:10]:
        print(f"  {it['event_date']} {it['country']}: {it['event_name']} = {it['actual']}")
