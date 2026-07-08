"""Macro scraper via yfinance (gratis, no key).

Ticker:
  S&P 500 -> ^GSPC   IHSG -> ^JKSE   Gold -> GC=F
  USD/IDR -> IDR=X    USD/JPY -> JPY=X

Output:
  daily_market: sp500_close, sp500_change_pct, ihsg_close, ihsg_change_pct,
                usd_idr, usd_jpy, gold_close
  asset_ohlcv : row tiap instrument (SP500, IHSG, GOLD, USDIDR, USDJPY)

Acceptance:
  - Tiap ticker gagal -> tandai fail, lanjut
  - change_pct dihitung vs close kemarin (ambil 2 hari terakhir)
"""
from __future__ import annotations

from typing import Any

import yfinance as yf

from scrapers.base import SourceFlags, safe_call, today_wib

# instrument -> ticker yfinance
TICKERS = {
    "SP500": "^GSPC",
    "IHSG": "^JKSE",
    "GOLD": "GC=F",
    "USDIDR": "IDR=X",
    "USDJPY": "JPY=X",
}


def _fetch_ticker(ticker: str) -> dict[str, Any]:
    """Ambil 2 baris harian terakhir; return OHLCV + change_pct vs close kemarin."""
    hist = yf.Ticker(ticker).history(period="7d", interval="1d")
    if hist is None or hist.empty:
        raise ValueError(f"yfinance kosong untuk {ticker}")

    hist = hist.dropna(subset=["Close"])
    last = hist.iloc[-1]
    prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else None

    close = float(last["Close"])
    change_pct = None
    if prev_close not in (None, 0):
        change_pct = round((close - prev_close) / prev_close * 100, 4)

    return {
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "open": float(last["Open"]),
        "high": float(last["High"]),
        "low": float(last["Low"]),
        "close": close,
        "volume": float(last["Volume"]) if "Volume" in last else None,
        "change_pct": change_pct,
    }


def fetch_macro_yf(date: str | None = None) -> dict[str, Any]:
    """Return dict: daily_market fields + 'asset_rows' (list) + 'source_flags'."""
    date = date or today_wib()
    flags = SourceFlags()
    market: dict[str, Any] = {
        "date": date,
        "sp500_close": None, "sp500_change_pct": None,
        "ihsg_close": None, "ihsg_change_pct": None,
        "usd_idr": None, "usd_jpy": None, "gold_close": None,
    }
    asset_rows: list[dict[str, Any]] = []

    for instrument, ticker in TICKERS.items():
        data = safe_call(
            f"yf_{instrument}", lambda t=ticker: _fetch_ticker(t), flags
        )
        if not data:
            continue

        asset_rows.append({
            "instrument": instrument,
            "date": data["date"],
            "open": data["open"], "high": data["high"],
            "low": data["low"], "close": data["close"],
            "volume": data["volume"],
        })

        # Map ke kolom daily_market
        if instrument == "SP500":
            market["sp500_close"] = data["close"]
            market["sp500_change_pct"] = data["change_pct"]
        elif instrument == "IHSG":
            market["ihsg_close"] = data["close"]
            market["ihsg_change_pct"] = data["change_pct"]
        elif instrument == "GOLD":
            market["gold_close"] = data["close"]
        elif instrument == "USDIDR":
            market["usd_idr"] = data["close"]
        elif instrument == "USDJPY":
            market["usd_jpy"] = data["close"]

    market["asset_rows"] = asset_rows
    market["source_flags"] = flags.as_dict()
    return market


if __name__ == "__main__":
    import json

    out = fetch_macro_yf()
    print(json.dumps(out, indent=2, default=str))
