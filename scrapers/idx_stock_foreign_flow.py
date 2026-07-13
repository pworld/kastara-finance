"""Scraper foreign flow PER-SAHAM individual IDX (Phase J+ Build Contract
v1.3, J-8). BEDA dari scrapers/idx_foreign_flow.py (Track C, level IHSG/
pasar) -- ini granularitas PER TICKER, malah lebih detail dari "per
sektor" yang diminta kontrak J-8 (bisa diagregasi ke sektor nanti kalau
perlu, tapi angka per-ticker sendiri sudah sinyal yang berguna).

Endpoint BARU, BEDA family dari "Digital Statistic" (Track C):
  https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=9999&start=0
Ditemukan lewat OBSERVASI NETWORK REQUEST BROWSER SUNGGUHAN (bukan tebak
nama urlName spt yang gagal total utk financial-ratio/papan-pemantauan-
khusus di riset sebelumnya) -- dikonfirmasi live: 965 saham termasuk BBCA
(ForeignBuy=105.752.900, ForeignSell=120.664.900 lembar, tanggal 2026-07-10).
TIDAK butuh session-cookie warmup (beda dari idx_foreign_flow.py) -- 1x GET
langsung 200. curl_cffi tetap dipakai (Cloudflare, sama seperti scraper IDX
lain di project ini).

Field asli (dikonfirmasi dari response, bukan asumsi): `ForeignBuy`/
`ForeignSell` = VOLUME (lembar saham), BUKAN value Rupiah -- beda dari
idx_foreign_flow.py (Track C) yang pakai Value. Foreign Net Buy Volume =
ForeignBuy - ForeignSell.

Endpoint TIDAK punya parameter tanggal -- selalu balikin hari bursa
TERAKHIR yang tersedia (field `Date` sama utk semua row dlm 1 response).

Output ke `positioning` (instrument=<ticker>): metric
stock_ff_foreign_buy_vol, stock_ff_foreign_sell_vol, stock_ff_foreign_net_vol.
"""
from __future__ import annotations

from typing import Any

from curl_cffi import requests as cffi_requests

from scrapers.base import SourceFlags, safe_call

IDX_STOCK_SUMMARY_URL = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary"
IDX_SOURCE = "idx_trading_summary"
IDX_TIMEOUT = 20


def _fetch_stock_summary() -> list[dict[str, Any]]:
    session = cffi_requests.Session(impersonate="chrome")
    resp = session.get(IDX_STOCK_SUMMARY_URL, params={"length": 9999, "start": 0}, timeout=IDX_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("data") or []


def fetch_idx_stock_foreign_flow(tickers: list[str]) -> dict[str, Any]:
    """Foreign flow (volume) per-saham utk `tickers` yang diminta (caller
    yang filter, biasanya instrumen market=IDX di instrument_metadata --
    scraper ini generic, tidak baca DB sendiri). Tidak pernah raise;
    return {'items', 'source_flags'}."""
    flags = SourceFlags()
    wanted = {t.upper() for t in tickers}
    if not wanted:
        return {"items": [], "source_flags": flags.as_dict()}

    rows = safe_call("idx_stock_summary", _fetch_stock_summary, flags, default=[])

    items: list[dict[str, Any]] = []
    for row in rows:
        code = row.get("StockCode")
        if code not in wanted:
            continue
        date = (row.get("Date") or "")[:10]
        buy, sell = row.get("ForeignBuy"), row.get("ForeignSell")
        if not date:
            continue
        if buy is not None:
            items.append({"date": date, "instrument": code, "metric": "stock_ff_foreign_buy_vol",
                          "value": buy, "source": IDX_SOURCE})
        if sell is not None:
            items.append({"date": date, "instrument": code, "metric": "stock_ff_foreign_sell_vol",
                          "value": sell, "source": IDX_SOURCE})
        if buy is not None and sell is not None:
            items.append({"date": date, "instrument": code, "metric": "stock_ff_foreign_net_vol",
                          "value": buy - sell, "source": IDX_SOURCE})
    return {"items": items, "source_flags": flags.as_dict()}


if __name__ == "__main__":
    out = fetch_idx_stock_foreign_flow(["BBCA"])
    print(f"{len(out['items'])} row. flags={out['source_flags']}")
    for it in out["items"]:
        print(f"  {it['date']} {it['instrument']} {it['metric']:<26} {it['value']:,.0f}")
