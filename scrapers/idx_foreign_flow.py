"""IDX (Bursa Efek Indonesia) foreign flow scraper -- IHSG foreign net buy/sell
harian, lewat internal JSON API "Digital Statistic" idx.co.id (BUKAN API resmi
publik -- tidak ada dokumentasi, ditemukan lewat source code proyek open-source
NeaByteLab/IDX-API dan dikonfirmasi LIVE sebelum dipakai di sini, lihat plan
Track C). TIDAK butuh API key -- cukup session cookie (1x GET idx.co.id/id).

PENTING -- pakai `curl_cffi`, BUKAN `requests` biasa (`scrapers.base.http_get`):
idx.co.id ada di belakang Cloudflare bot-management. Header browser-realistis
SAJA tidak cukup -- dikonfirmasi lewat testing langsung: curl CLI tembus
konsisten (3/3 percobaan), tapi `requests`/urllib3 Python KONSISTEN kena
halaman JS-challenge Cloudflare ("Just a moment...", HTTP 403) walau header
IDENTIK dengan curl. Ini soal TLS fingerprint (JA3) yang beda antara stack
TLS Python vs curl, bukan soal header sama sekali -- `curl_cffi` (dependency
baru, lihat requirements.txt) meniru TLS handshake browser asli dan
dikonfirmasi tembus konsisten. Ini SATU-SATUNYA scraper di project ini yang
butuh ini -- semua scraper lain (termasuk farside.co.uk yang juga di
belakang Cloudflare, lihat scrapers/positioning.py) cukup dengan
`requests` + header browser-realistis, tidak kena JS-challenge (tier
proteksi Cloudflare yang lebih ringan).

PENTING -- koreksi atas library referensi (NeaByteLab/IDX-API salah baca field
ini sebagai buy/sell langsung): field asli dari IDX (dikonfirmasi dari
`columns[].Title` di response, BUKAN asumsi):
  foreignForeign*  = "Foreign Investor Sell - Foreign Investor Buy" (F2F,
                     transaksi asing-ke-asing, BUKAN sinyal arah)
  foreignDomestic* = "Foreign Investor Sell - Domestic Investor Buy" (F2D,
                     asing jual ke domestik -- sisi distribusi)
  domesticForeign* = "Domestic Investor Sell - Foreign Investor Buy" (D2F,
                     domestik jual ke asing -- sisi akumulasi asing)
Foreign Net Buy = domesticForeignValue (D2F) - foreignDomesticValue (F2D).
Ketiga komponen disimpan TERPISAH (bukan cuma net) -- GEMA/LEON persona butuh
baca F2F vs F2D vs D2F sendiri-sendiri (lihat prompts/persona_gema.txt).

Output ke `positioning` (instrument='IHSG'): metric ihsg_ff_foreign_foreign,
ihsg_ff_foreign_domestic, ihsg_ff_domestic_foreign, foreign_net_buy_value.
"""
from __future__ import annotations

import base64
import json as jsonlib
from typing import Any

from curl_cffi import requests as cffi_requests

from scrapers.base import SourceFlags, safe_call, today_wib

IDX_BASE = "https://www.idx.co.id"
FOREIGN_URL_NAME = "LINK_TABLE_DAILY_TRADING_INVESTOR_FOREIGN"
DOMESTIC_URL_NAME = "LINK_TABLE_DAILY_TRADING_INVESTOR_DOMESTIC"
IDX_SOURCE = "idx_digital_statistic"
IDX_TIMEOUT = 20


def _idx_fetch_investor_table(
    session: cffi_requests.Session, url_name: str, year: str, month: str,
) -> list[dict[str, Any]]:
    """1 baris per hari bursa dalam bulan yang diminta (skip weekend
    otomatis dari sisi IDX)."""
    query_obj = {"year": year, "month": month, "quarter": 0, "type": "monthly"}
    query_b64 = base64.b64encode(jsonlib.dumps(query_obj).encode()).decode()
    resp = session.get(
        f"{IDX_BASE}/primary/DigitalStatistic/GetApiData",
        params={
            "urlName": url_name, "query": query_b64,
            "isPrint": "False", "cumulative": "false",
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=IDX_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("data") or []


def fetch_idx_foreign_flow(date: str | None = None) -> dict[str, Any]:
    """Foreign flow IHSG utk SELURUH hari bursa di bulan `date` (pola sama
    scrapers/positioning.py::fetch_btc_etf_flow -- tarik rentang, UPSERT by
    natural key (date,instrument,metric) yang dedupe, bukan cuma 1 hari.
    Ini juga yang membuat pipeline tahan lag: kalau data 'hari ini' belum
    terbit saat run_daily jalan, hari-hari sebelumnya di bulan yang sama
    tetap ke-backfill). Tidak pernah raise; return {'items', 'source_flags'}."""
    date = date or today_wib()
    year, month = date[:4], str(int(date[5:7]))
    flags = SourceFlags()

    session = cffi_requests.Session(impersonate="chrome")

    def _warm_session() -> bool:
        resp = session.get(f"{IDX_BASE}/id", timeout=IDX_TIMEOUT)
        resp.raise_for_status()
        return True

    if not safe_call("idx_session", _warm_session, flags):
        flags.skip("idx_foreign_flow")
        flags.skip("idx_domestic_flow")
        return {"items": [], "source_flags": flags.as_dict()}

    foreign_rows = safe_call(
        "idx_foreign_flow",
        lambda: _idx_fetch_investor_table(session, FOREIGN_URL_NAME, year, month),
        flags, default=[],
    )
    domestic_rows = safe_call(
        "idx_domestic_flow",
        lambda: _idx_fetch_investor_table(session, DOMESTIC_URL_NAME, year, month),
        flags, default=[],
    )
    domestic_by_date = {r["date"]: r for r in domestic_rows}

    items: list[dict[str, Any]] = []
    for frow in foreign_rows:
        d = frow["date"]
        drow = domestic_by_date.get(d)

        f2f = frow.get("foreignForeignValue")
        f2d = frow.get("foreignDomesticValue")
        d2f = drow.get("domesticForeignValue") if drow else None

        if f2f is not None:
            items.append({
                "date": d, "instrument": "IHSG", "metric": "ihsg_ff_foreign_foreign",
                "value": f2f, "source": IDX_SOURCE,
            })
        if f2d is not None:
            items.append({
                "date": d, "instrument": "IHSG", "metric": "ihsg_ff_foreign_domestic",
                "value": f2d, "source": IDX_SOURCE,
            })
        if d2f is not None:
            items.append({
                "date": d, "instrument": "IHSG", "metric": "ihsg_ff_domestic_foreign",
                "value": d2f, "source": IDX_SOURCE,
            })
        if d2f is not None and f2d is not None:
            items.append({
                "date": d, "instrument": "IHSG", "metric": "foreign_net_buy_value",
                "value": d2f - f2d, "source": IDX_SOURCE,
            })

    return {"items": items, "source_flags": flags.as_dict()}


if __name__ == "__main__":
    out = fetch_idx_foreign_flow()
    print(f"{len(out['items'])} row IHSG foreign flow. flags={out['source_flags']}")
    for it in out["items"][:12]:
        print(f"  {it['date']} {it['metric']:<26} {it['value']:,.0f}")
