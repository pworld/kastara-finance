"""Scraper earnings calendar via yfinance (Phase J+ Build Contract v1.3, J-7).

Dipakai AKELA (logika surprise forecast-vs-actual, kontrak §1 Gap Analysis)
dan rule SOP terkunci "no hold through earnings VERSI PENUH" utk saham AS
(kontrak §18 keputusan #3) — `earnings_calendar` adalah data penegak aturan
itu (Panel 3 warning posisi ONGOING mendekati earnings, J-15, belum dibangun
di modul ini).

`Ticker.earnings_dates` (butuh dependency `lxml`, ditambah ke requirements.txt)
kasih histori earnings TERLAPOR (EPS Estimate, Reported EPS, Surprise%) DAN
tanggal earnings berikutnya (Reported EPS = NaN utk yang belum rilis) --
lebih lengkap dari `Ticker.calendar` (cuma kasih 1 tanggal ke depan, tanpa
histori surprise).

Pakai:
    python -m scrapers.earnings_yf BBCA
"""
from __future__ import annotations

from typing import Any

import yfinance as yf

from scrapers.base import SourceFlags, safe_call
from scrapers.equity_universe import yf_ticker_for


def _is_nan(v: Any) -> bool:
    try:
        return v != v
    except Exception:  # noqa: BLE001
        return False


def _fetch_earnings(ticker: str) -> list[dict[str, Any]]:
    t = yf.Ticker(ticker)
    df = t.earnings_dates
    if df is None or df.empty:
        raise ValueError(f"yfinance earnings_dates kosong untuk {ticker}")

    rows = []
    for idx, r in df.iterrows():
        forecast = r.get("EPS Estimate")
        actual = r.get("Reported EPS")
        rows.append({
            "earnings_date": idx.strftime("%Y-%m-%d"),
            "eps_forecast": None if forecast is None or _is_nan(forecast) else float(forecast),
            "eps_actual": None if actual is None or _is_nan(actual) else float(actual),
            "event_type": "EARNINGS",
        })
    return rows


def fetch_earnings_calendar(instrument: str, market: str) -> dict[str, Any]:
    """Return {'rows': [...], 'source_flags': {...}}. Tidak pernah raise --
    pola SourceFlags/safe_call sama dgn scraper lain di project ini."""
    flags = SourceFlags()
    ticker = yf_ticker_for(instrument, market)
    rows = safe_call(f"earnings_{instrument}", lambda: _fetch_earnings(ticker), flags) or []
    return {"rows": rows, "source_flags": flags.as_dict()}


if __name__ == "__main__":
    import json
    import sys

    inst = sys.argv[1] if len(sys.argv) > 1 else "TSLA"
    mkt = "IDX" if inst.upper() == "BBCA" else "US"
    print(json.dumps(fetch_earnings_calendar(inst, mkt), indent=2, default=str))
