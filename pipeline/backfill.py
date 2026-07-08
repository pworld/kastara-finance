"""Manual backfill tool — tarik data historis sebelum sistem live.

Pakai:
    python -m pipeline.backfill --instrument BTC --from 2025-01-01 --to 2025-06-01
    python -m pipeline.backfill --instrument SP500 --from 2025-01-01 --to 2025-06-01 --yes

Mapping source:
    BTC                         -> Binance (fallback yfinance BTC-USD kalau ke-block)
    DXY/US10Y/VIX/WALCL/RRP/TGA -> FRED (butuh FRED_API_KEY)  -> daily_market
    SP500/IHSG/GOLD/USDIDR/USDJPY -> yfinance                 -> asset_ohlcv

Selalu PREVIEW dulu (berapa baru, berapa duplikat di-skip), minta konfirmasi [y/N].
Duplikat (date+instrument sudah ada) -> skip, bukan error.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

from db.connection import get_connection, init_db
from scrapers.base import created_at, http_get_json
from pipeline.run_daily import upsert_asset_ohlcv, upsert_daily_market

# instrument -> ticker yfinance (BTC pakai BTC-USD sbg fallback Binance)
YF_TICKERS = {
    "BTC": "BTC-USD",
    "SP500": "^GSPC",
    "IHSG": "^JKSE",
    "GOLD": "GC=F",
    "USDIDR": "IDR=X",
    "USDJPY": "JPY=X",
}

# instrument FRED -> (series_id, kolom daily_market)
FRED_INSTRUMENTS = {
    "DXY": ("DTWEXBGS", "dxy_close"),
    "US10Y": ("DGS10", "us10y_yield"),
    "VIX": ("VIXCLS", "vix_close"),
    "WALCL": ("WALCL", "walcl"),
    "RRP": ("RRPONTSYD", "rrp"),
    "TGA": ("WTREGEN", "tga"),
    "HY": ("BAMLH0A0HYM2", "hy_credit_spread"),
}

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def _to_ms(date_str: str) -> int:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _binance_klines_range(date_from: str, date_to: str) -> list[dict[str, Any]]:
    """BTC daily OHLCV dari Binance untuk range tanggal."""
    rows: list[dict[str, Any]] = []
    start = _to_ms(date_from)
    end = _to_ms(date_to) + 86_400_000  # inklusif hari terakhir
    while start < end:
        data = http_get_json(
            BINANCE_KLINES,
            params={
                "symbol": "BTCUSDT", "interval": "1d",
                "startTime": start, "endTime": end, "limit": 1000,
            },
        )
        if not data:
            break
        for k in data:
            d = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            rows.append({
                "instrument": "BTC", "date": d,
                "open": float(k[1]), "high": float(k[2]),
                "low": float(k[3]), "close": float(k[4]), "volume": float(k[5]),
            })
        start = data[-1][0] + 86_400_000
        if len(data) < 1000:
            break
    return rows


def _yf_history_range(instrument: str, ticker: str, date_from: str, date_to: str) -> list[dict[str, Any]]:
    """OHLCV historis dari yfinance. yfinance `end` eksklusif -> +1 hari supaya inklusif."""
    from datetime import timedelta

    end_plus = (datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    hist = yf.Ticker(ticker).history(start=date_from, end=end_plus, interval="1d")
    if hist is None or hist.empty:
        return []
    hist = hist.dropna(subset=["Close"])
    rows: list[dict[str, Any]] = []
    for idx, r in hist.iterrows():
        rows.append({
            "instrument": instrument,
            "date": idx.strftime("%Y-%m-%d"),
            "open": float(r["Open"]), "high": float(r["High"]),
            "low": float(r["Low"]), "close": float(r["Close"]),
            "volume": float(r["Volume"]) if "Volume" in r else None,
        })
    return rows


def _fred_range(series_id: str, date_from: str, date_to: str) -> list[dict[str, Any]]:
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("FRED_API_KEY kosong — set di .env untuk backfill makro FRED.")
    data = http_get_json(
        FRED_BASE,
        params={
            "series_id": series_id, "api_key": api_key, "file_type": "json",
            "observation_start": date_from, "observation_end": date_to,
        },
    )
    return [
        {"date": o["date"], "value": float(o["value"])}
        for o in data.get("observations", [])
        if o.get("value") not in (".", "", None)
    ]


def _fetch_rows(instrument: str, date_from: str, date_to: str) -> tuple[str, list[dict[str, Any]]]:
    """Return (kind, rows). kind = 'asset' atau 'fred'."""
    instrument = instrument.upper()
    if instrument == "BTC":
        try:
            rows = _binance_klines_range(date_from, date_to)
            if rows:
                return "asset", rows
            raise ValueError("Binance kosong")
        except Exception as exc:  # noqa: BLE001
            print(f"[backfill] Binance gagal ({exc}); fallback yfinance BTC-USD.")
            return "asset", _yf_history_range("BTC", "BTC-USD", date_from, date_to)
    if instrument in YF_TICKERS:
        return "asset", _yf_history_range(instrument, YF_TICKERS[instrument], date_from, date_to)
    if instrument in FRED_INSTRUMENTS:
        series_id, _ = FRED_INSTRUMENTS[instrument]
        return "fred", _fred_range(series_id, date_from, date_to)
    raise SystemExit(f"Instrument tidak dikenal: {instrument}. "
                     f"Pilihan: {', '.join(list(YF_TICKERS) + list(FRED_INSTRUMENTS))}")


def _existing_dates_asset(instrument: str, dates: list[str], db_path=None) -> set[str]:
    if not dates:
        return set()
    with get_connection(db_path) as conn:
        qmarks = ", ".join("?" for _ in dates)
        rows = conn.execute(
            f"SELECT date FROM asset_ohlcv WHERE instrument = ? AND date IN ({qmarks})",
            (instrument, *dates),
        ).fetchall()
    return {r["date"] for r in rows}


def _existing_dates_market(col: str, dates: list[str], db_path=None) -> set[str]:
    if not dates:
        return set()
    with get_connection(db_path) as conn:
        qmarks = ", ".join("?" for _ in dates)
        rows = conn.execute(
            f"SELECT date FROM daily_market WHERE {col} IS NOT NULL AND date IN ({qmarks})",
            tuple(dates),
        ).fetchall()
    return {r["date"] for r in rows}


def backfill(
    instrument: str, date_from: str, date_to: str,
    assume_yes: bool = False, db_path=None,
) -> dict[str, Any]:
    """Tarik historis -> preview -> konfirmasi -> upsert. Return ringkasan."""
    instrument = instrument.upper()
    init_db(db_path)
    kind, rows = _fetch_rows(instrument, date_from, date_to)

    if not rows:
        print(f"[backfill] Tidak ada data untuk {instrument} {date_from}..{date_to}.")
        return {"instrument": instrument, "fetched": 0, "new": 0, "dup": 0, "committed": False}

    dates = [r["date"] for r in rows]
    if kind == "asset":
        existing = _existing_dates_asset(instrument, dates, db_path)
    else:
        _, col = FRED_INSTRUMENTS[instrument]
        existing = _existing_dates_market(col, dates, db_path)

    new_rows = [r for r in rows if r["date"] not in existing]
    n_new, n_dup = len(new_rows), len(rows) - len(new_rows)

    # PREVIEW
    print(f"\n[backfill PREVIEW] instrument={instrument} kind={kind}")
    print(f"  range          : {date_from} .. {date_to}")
    print(f"  fetched        : {len(rows)} baris")
    print(f"  akan insert    : {n_new} baris BARU")
    print(f"  duplikat(skip) : {n_dup} baris (date sudah ada)")
    if new_rows:
        print(f"  contoh         : {new_rows[0]['date']} ... {new_rows[-1]['date']}")

    if n_new == 0:
        print("[backfill] Tidak ada baris baru. Selesai (tidak ada yang ditulis).")
        return {"instrument": instrument, "fetched": len(rows), "new": 0,
                "dup": n_dup, "committed": False}

    if not assume_yes:
        ans = input("\nLanjut commit? [y/N] ").strip().lower()
        if ans != "y":
            print("[backfill] Dibatalkan. Tidak ada yang ditulis.")
            return {"instrument": instrument, "fetched": len(rows), "new": n_new,
                    "dup": n_dup, "committed": False}

    # COMMIT (upsert; duplikat aman karena ON CONFLICT)
    with get_connection(db_path) as conn:
        if kind == "asset":
            for r in rows:
                r["created_at"] = created_at()
                upsert_asset_ohlcv(conn, r)
        else:
            _, col = FRED_INSTRUMENTS[instrument]
            for r in rows:
                upsert_daily_market(conn, r["date"], {
                    col: r["value"], "source_flags": None,
                })
        conn.commit()

    print(f"[backfill] OK — {n_new} baris baru ditulis ({n_dup} duplikat di-skip).")
    return {"instrument": instrument, "fetched": len(rows), "new": n_new,
            "dup": n_dup, "committed": True}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Kastara backfill tool (Phase A)")
    p.add_argument("--instrument", required=True, help="BTC, SP500, IHSG, GOLD, USDIDR, USDJPY, DXY, US10Y, VIX, WALCL, RRP, TGA, HY")
    p.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
    p.add_argument("--yes", action="store_true", help="skip konfirmasi (untuk script/test)")
    args = p.parse_args(argv)
    backfill(args.instrument, args.date_from, args.date_to, assume_yes=args.yes)


if __name__ == "__main__":
    main()
