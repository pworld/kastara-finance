"""Macro scraper via FRED API (gratis, butuh FRED_API_KEY di .env).

Series id FRED kadang berubah/deprecate. Kalau satu series gagal -> tandai
fail di source_flags, JANGAN crash. Log series mana yang gagal.

Output:
  daily_market: dxy_close, dxy_change_pct, us10y_yield, us10y_change_bps,
                vix_close, walcl, rrp, tga, hy_credit_spread
  (net_liquidity dihitung di indicators/calc.py, bukan di sini)
"""
from __future__ import annotations

import os
from typing import Any

from scrapers.base import SourceFlags, http_get_json, safe_call, today_wib

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# label internal -> series id FRED.
# CATATAN: verifikasi series aktif saat fetch; jangan asumsi kalau gagal.
SERIES = {
    "dxy": "DTWEXBGS",      # Trade-weighted USD index (broad)
    "us10y": "DGS10",       # 10Y treasury yield
    "vix": "VIXCLS",        # VIX
    "walcl": "WALCL",       # Fed balance sheet
    "rrp": "RRPONTSYD",     # Reverse repo
    "tga": "WTREGEN",       # Treasury general account
    "hy_spread": "BAMLH0A0HYM2",  # HY credit spread (optional)
}


def _fetch_series(series_id: str, api_key: str, n: int = 2) -> list[dict[str, Any]]:
    """Ambil n observasi terakhir non-missing (FRED pakai '.' untuk missing)."""
    data = http_get_json(
        FRED_BASE,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 30,
        },
    )
    obs = [
        {"date": o["date"], "value": float(o["value"])}
        for o in data.get("observations", [])
        if o.get("value") not in (".", "", None)
    ]
    if not obs:
        raise ValueError(f"FRED {series_id}: tidak ada observasi valid")
    return obs[:n]


def fetch_macro_fred(date: str | None = None) -> dict[str, Any]:
    """Return dict daily_market fields + 'source_flags'.

    Kalau FRED_API_KEY kosong -> semua series ditandai 'skip', return None values.
    """
    date = date or today_wib()
    flags = SourceFlags()
    result: dict[str, Any] = {
        "date": date,
        "dxy_close": None, "dxy_change_pct": None,
        "us10y_yield": None, "us10y_change_bps": None,
        "vix_close": None,
        "walcl": None, "rrp": None, "tga": None,
        "hy_credit_spread": None,
    }

    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        for label in SERIES:
            flags.skip(f"fred_{label}")
        print("[fred] FRED_API_KEY kosong — semua series di-skip.")
        result["source_flags"] = flags.as_dict()
        return result

    fetched: dict[str, list[dict[str, Any]]] = {}
    for label, series_id in SERIES.items():
        obs = safe_call(
            f"fred_{label}",
            lambda sid=series_id: _fetch_series(sid, api_key),
            flags,
        )
        if obs:
            fetched[label] = obs

    # Map ke kolom daily_market + hitung perubahan
    if "dxy" in fetched:
        result["dxy_close"] = fetched["dxy"][0]["value"]
        if len(fetched["dxy"]) >= 2:
            cur, prev = fetched["dxy"][0]["value"], fetched["dxy"][1]["value"]
            if prev:
                result["dxy_change_pct"] = round((cur - prev) / prev * 100, 4)

    if "us10y" in fetched:
        result["us10y_yield"] = fetched["us10y"][0]["value"]
        if len(fetched["us10y"]) >= 2:
            cur, prev = fetched["us10y"][0]["value"], fetched["us10y"][1]["value"]
            # yield dalam persen -> selisih dalam basis points
            result["us10y_change_bps"] = round((cur - prev) * 100, 2)

    if "vix" in fetched:
        result["vix_close"] = fetched["vix"][0]["value"]
    if "walcl" in fetched:
        result["walcl"] = fetched["walcl"][0]["value"]
    if "rrp" in fetched:
        result["rrp"] = fetched["rrp"][0]["value"]
    if "tga" in fetched:
        result["tga"] = fetched["tga"][0]["value"]
    if "hy_spread" in fetched:
        result["hy_credit_spread"] = fetched["hy_spread"][0]["value"]

    result["source_flags"] = flags.as_dict()
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_macro_fred(), indent=2))
