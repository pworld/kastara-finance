"""Scraper OHLCV harian untuk universe saham individual (Phase J+ Build
Contract v1.3, J-2 -- "OHLCV universe -> asset_ohlcv, extend scraper
yfinance .JK").

Beda dari scrapers/macro_yf.py: universe DINAMIS, dibaca dari
`instrument_metadata` tiap kali dipanggil -- nambah emiten baru lewat
Panel 8 intake (web/writes.py::save_intake_metadata) TIDAK butuh ubah kode
di sini. Cuma tulis ke `asset_ohlcv` (BUKAN `daily_market` -- saham
individual bukan konteks makro global yang dibagi semua aset, lihat Master
Plan §4).

Ticker yfinance per `instrument_metadata.market`:
  IDX -> f"{instrument}.JK"   US (dan lainnya) -> instrument apa adanya

Pakai:
    python -m scrapers.equity_universe
"""
from __future__ import annotations

from typing import Any

import yfinance as yf

from db.connection import get_connection
from scrapers.base import SourceFlags, safe_call, today_wib


def yf_ticker_for(instrument: str, market: str | None) -> str:
    """Derive ticker yfinance dari instrument + market. IDX butuh suffix
    `.JK`; US (dan market lain yang belum di-map) dipakai apa adanya."""
    if (market or "").upper() == "IDX":
        return f"{instrument.upper()}.JK"
    return instrument.upper()


def _fetch_ticker(ticker: str) -> dict[str, Any]:
    """1 baris OHLCV terakhir yang tersedia (pola sama macro_yf._fetch_ticker,
    tanpa change_pct -- asset_ohlcv tidak punya kolom itu)."""
    hist = yf.Ticker(ticker).history(period="7d", interval="1d")
    if hist is None or hist.empty:
        raise ValueError(f"yfinance kosong untuk {ticker}")
    hist = hist.dropna(subset=["Close"])
    last = hist.iloc[-1]
    return {
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "open": float(last["Open"]), "high": float(last["High"]),
        "low": float(last["Low"]), "close": float(last["Close"]),
        "volume": float(last["Volume"]) if "Volume" in last else None,
    }


def fetch_equity_universe(date: str | None = None, db_path=None) -> dict[str, Any]:
    """Return {'asset_rows': [...], 'source_flags': {...}}. Universe dibaca
    dari `instrument_metadata` (semua instrumen, bukan cuma yang lane=TRADE
    -- INVEST/NONE tetap butuh harga historis buat validasi bar-replay J-3
    nanti). `date` diterima buat konsistensi signature dgn scraper lain,
    tidak dipakai filter (yfinance selalu balikin baris TERBARU yang ada)."""
    date = date or today_wib()
    flags = SourceFlags()
    with get_connection(db_path) as conn:
        instruments = conn.execute(
            "SELECT instrument, market FROM instrument_metadata"
        ).fetchall()

    asset_rows: list[dict[str, Any]] = []
    for row in instruments:
        instrument, market = row["instrument"], row["market"]
        ticker = yf_ticker_for(instrument, market)
        data = safe_call(f"equity_{instrument}", lambda t=ticker: _fetch_ticker(t), flags)
        if not data:
            continue
        asset_rows.append({"instrument": instrument, **data})

    return {"asset_rows": asset_rows, "source_flags": flags.as_dict()}


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_equity_universe(), indent=2, default=str))
