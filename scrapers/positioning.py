"""Positioning scraper (Stage 2 / Layer C, Phase D, Master Plan v1.4 §4.2)
— arah "uang besar", validator utk Policy Tracker (Layer A).

Dua sumber, DUA profil resiko beda:

1. COT report (CFTC) — GRATIS, TANPA API key. Dikonfirmasi langsung saat
   riset Phase D: publicreporting.cftc.gov (Socrata) bisa di-query tanpa
   registrasi apapun. Rilis MINGGUAN (data per Selasa, keluar Jumat) —
   dipanggil tiap hari lewat run_daily tapi cuma dapat row baru pas
   memang ada rilis baru minggu itu (idempotent, bukan error di hari lain).
   Metric: `cot_net_long` = noncomm (speculator) long - short, proxy umum
   "arah uang besar" di kontrak berjangka.

2. BTC ETF net flow — farside.co.uk TIDAK punya API resmi gratis; ini
   scrape HTML tak-resmi (situs dilindungi Cloudflare -- butuh header
   browser-realistis, BUKAN `DEFAULT_HEADERS` bawaan `scrapers/base.py`
   yang isinya UA bot + `Accept: application/json`, soalnya itu malah
   kena challenge page). Kalau markup berubah/situs down -> source_flags
   fail + lanjut, TIDAK crash (sama pola dengan scraper lain).

SBN foreign flow SENGAJA TIDAK ADA di sini — djppr.kemenkeu.go.id tidak
scrape-able reliable (SPA/render-JS, fetch polos tidak dapat konten
bermakna). Diisi MANUAL lewat dashboard, lihat
`web/writes.py::insert_positioning_manual`.

Output ke `positioning`: date, instrument, metric, value, source.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import SourceFlags, http_get, http_get_json, safe_call

CFTC_LEGACY_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"

# instrument kita -> nama kontrak PERSIS di CFTC Legacy Futures Only report
# (dicek manual saat riset Phase D lewat pencarian $q; IHSG/USDIDR/USDJPY
# tidak listed di CFTC -- tidak ada mapping utk instrument itu, dilewati).
COT_CONTRACTS = {
    "BTC": "BITCOIN - CHICAGO MERCANTILE EXCHANGE",
    "DXY": "USD INDEX - ICE FUTURES U.S.",
    "GOLD": "GOLD - COMMODITY EXCHANGE INC.",
    "SP500": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
}

FARSIDE_BTC_URL = "https://farside.co.uk/btc/"

# Header browser-realistis -- WAJIB, `DEFAULT_HEADERS` bawaan (Accept:
# application/json) kena Cloudflare challenge page di situs ini.
FARSIDE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Berapa hari terakhir dari tabel farside yang diambil tiap run -- cukup
# besar utk menutup jeda kalau pipeline sempat tidak jalan beberapa hari,
# tapi tidak perlu tarik seluruh histori (sudah ada di DB, UPSERT skip).
FARSIDE_RECENT_DAYS = 10

_DATE_RE = re.compile(r"^\d{1,2} [A-Za-z]{3} \d{4}$")


def _parse_farside_number(raw: str) -> float | None:
    """'209.4' -> 209.4, '(44.5)' -> -44.5, '' / '-' -> None."""
    raw = raw.strip().replace(",", "")
    if not raw or raw == "-":
        return None
    neg = raw.startswith("(") and raw.endswith(")")
    if neg:
        raw = raw[1:-1]
    try:
        value = float(raw)
    except ValueError:
        return None
    return -value if neg else value


def _fetch_cot_row(contract_name: str) -> dict[str, Any] | None:
    """Row COT terbaru utk 1 kontrak. None kalau tidak ada data."""
    data = http_get_json(
        CFTC_LEGACY_URL,
        params={
            "market_and_exchange_names": contract_name,
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": 1,
        },
    )
    if not data:
        return None
    row = data[0]
    net_long = (
        float(row["noncomm_positions_long_all"])
        - float(row["noncomm_positions_short_all"])
    )
    return {"date": row["report_date_as_yyyy_mm_dd"][:10], "net_long": net_long}


def fetch_cot_positioning() -> tuple[list[dict[str, Any]], SourceFlags]:
    """COT net-long (non-commercial/speculator) utk BTC/DXY/GOLD/SP500."""
    flags = SourceFlags()
    rows: list[dict[str, Any]] = []
    for instrument, contract in COT_CONTRACTS.items():
        result = safe_call(
            f"cot_{instrument.lower()}",
            lambda c=contract: _fetch_cot_row(c),
            flags,
        )
        if result:
            rows.append({
                "date": result["date"], "instrument": instrument,
                "metric": "cot_net_long", "value": result["net_long"],
                "source": "cftc_cot",
            })
    return rows, flags


def _parse_farside_table(html: str) -> list[dict[str, Any]]:
    """Parse tabel farside.co.uk -> list {date, total_flow_musd}.

    Kolom pertama = tanggal ('07 Jul 2026'), kolom TERAKHIR = Total (net
    flow harian, USD juta) -- tidak perlu tahu kolom per-ticker (IBIT/
    FBTC/dll) satu-satu, cuma Total yang dipakai. Baris footer (Total/
    Average/Maximum/Minimum) dilewati karena kolom pertamanya bukan tanggal.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("tabel ETF flow tidak ditemukan (markup situs berubah?)")
    out: list[dict[str, Any]] = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2 or not _DATE_RE.match(cells[0]):
            continue
        total = _parse_farside_number(cells[-1])
        if total is None:
            continue
        date = datetime.strptime(cells[0], "%d %b %Y").strftime("%Y-%m-%d")
        out.append({"date": date, "total_flow_musd": total})
    return out


def fetch_btc_etf_flow() -> tuple[list[dict[str, Any]], SourceFlags]:
    """N hari terakhir net flow ETF BTC (USD juta) dari farside.co.uk."""
    flags = SourceFlags()

    def _do_fetch() -> list[dict[str, Any]]:
        resp = http_get(FARSIDE_BTC_URL, headers=FARSIDE_HEADERS)
        return _parse_farside_table(resp.text)

    parsed = safe_call("farside_btc_etf", _do_fetch, flags, default=[])
    recent = parsed[-FARSIDE_RECENT_DAYS:] if parsed else []
    rows = [
        {
            "date": r["date"], "instrument": "BTC", "metric": "etf_net_flow",
            "value": r["total_flow_musd"], "source": "farside_btc_etf",
        }
        for r in recent
    ]
    return rows, flags


def fetch_positioning() -> dict[str, Any]:
    """Gabungan COT + BTC ETF flow. Return dict 'items' + 'source_flags'.
    Tidak pernah raise."""
    cot_rows, cot_flags = fetch_cot_positioning()
    etf_rows, etf_flags = fetch_btc_etf_flow()
    flags = SourceFlags()
    flags.merge(cot_flags)
    flags.merge(etf_flags)
    return {"items": cot_rows + etf_rows, "source_flags": flags.as_dict()}


if __name__ == "__main__":
    import json

    out = fetch_positioning()
    print(f"{len(out['items'])} row positioning. flags={out['source_flags']}")
    for it in out["items"][:10]:
        print(f"  {it['date']} {it['instrument']:>6} {it['metric']:<14} {it['value']}")
