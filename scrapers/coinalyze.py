"""Coinalyze scraper: Open Interest agregat + Liquidation long/short + Long/Short
ratio (BTC perpetual, lintas exchange).

Kenapa Coinalyze (bukan cuma Binance yang sudah dipakai `scrapers/crypto.py`):
Binance API cuma kasih OI single-exchange. Coinalyze agregat lintas exchange lewat
1 API key gratis (rate limit 40 req/menit) -- dites live sebelum ditulis di sini
(lihat plan Track B), no key needed selain daftar gratis di coinalyze.net.

Output:
  daily_market: btc_oi_aggregate, btc_long_short_ratio,
                btc_liq_long_24h, btc_liq_short_24h

Acceptance:
  - fetch_coinalyze() return dict, kolom non-None kecuali API down/key kosong
  - OI aggregate = jumlah OI 3 exchange utama (Binance+OKX+Bybit), BUKAN 1
    exchange saja -- itu beda dari btc_oi (scrapers/crypto.py, Binance-only)
  - liquidation dipisah long vs short (bukan 1 angka gabungan) -- RIVAN persona
    butuh baca komposisi pergerakan, bukan cuma total
"""
from __future__ import annotations

import os
import time
from typing import Any

from scrapers.base import SourceFlags, http_get_json, safe_call, today_wib

COINALYZE_BASE = "https://api.coinalyze.net/v1"

# Simbol Coinalyze BTC perpetual per exchange (dikonfirmasi live -- format
# BEDA per exchange, bukan 1 pola seragam, mis. Binance pakai suffix
# "_PERP", Bybit tidak). "Aggregate" = jumlah value dari exchange-exchange
# ini, API Coinalyze sendiri TIDAK menyediakan simbol gabungan siap pakai.
BTC_SYMBOLS = ["BTCUSDT_PERP.A", "BTCUSDT_PERP.3", "BTCUSDT.6"]  # Binance, OKX, Bybit
BTC_SYMBOLS_QS = ",".join(BTC_SYMBOLS)


def _api_key() -> str:
    return os.getenv("COINALYZE_API_KEY", "").strip()


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_api_key()}"}


def _coinalyze_open_interest() -> float:
    """OI agregat (USD) -- jumlah OI current snapshot 3 exchange utama."""
    data = http_get_json(
        f"{COINALYZE_BASE}/open-interest",
        params={"symbols": BTC_SYMBOLS_QS, "convert_to_usd": "true"},
        headers=_headers(),
        retries=1,
    )
    return sum(float(item["value"]) for item in data)


def _coinalyze_long_short_ratio() -> float:
    """Long/short ratio harian Binance (best-effort, single-exchange --
    rasio tidak bermakna dijumlahkan lintas exchange seperti OI/liquidation)."""
    now = int(time.time())
    data = http_get_json(
        f"{COINALYZE_BASE}/long-short-ratio-history",
        params={
            "symbols": "BTCUSDT_PERP.A", "interval": "daily",
            "from": now - 3 * 86400, "to": now,
        },
        headers=_headers(),
        retries=1,
    )
    history = data[0]["history"]
    return float(history[-1]["r"])


def _coinalyze_liquidation_24h() -> tuple[float, float]:
    """(long_liquidation_usd, short_liquidation_usd) 24 jam terakhir, agregat
    3 exchange utama. Return tuple, BUKAN 1 angka gabungan -- RIVAN persona
    butuh baca komposisi (short-covering vs pembelian spot murni)."""
    now = int(time.time())
    data = http_get_json(
        f"{COINALYZE_BASE}/liquidation-history",
        params={
            "symbols": BTC_SYMBOLS_QS, "interval": "daily",
            "from": now - 3 * 86400, "to": now, "convert_to_usd": "true",
        },
        headers=_headers(),
        retries=1,
    )
    long_total, short_total = 0.0, 0.0
    for item in data:
        history = item.get("history") or []
        if not history:
            continue
        latest = history[-1]
        long_total += float(latest.get("l", 0) or 0)
        short_total += float(latest.get("s", 0) or 0)
    return long_total, short_total


def fetch_coinalyze(date: str | None = None) -> dict[str, Any]:
    """Ambil OI agregat + long/short ratio + liquidation long/short. Return
    dict siap di-merge ke daily_market. Selalu return dict (tidak melempar).
    Sertakan key 'source_flags' dan 'date'."""
    date = date or today_wib()
    flags = SourceFlags()
    result: dict[str, Any] = {
        "date": date,
        "btc_oi_aggregate": None, "btc_long_short_ratio": None,
        "btc_liq_long_24h": None, "btc_liq_short_24h": None,
    }

    if not _api_key():
        flags.skip("coinalyze_oi")
        flags.skip("coinalyze_ls_ratio")
        flags.skip("coinalyze_liquidation")
        print("[scraper:skip] COINALYZE_API_KEY kosong -- OI/liquidation/L-S ratio dilewati")
        result["source_flags"] = flags.as_dict()
        return result

    result["btc_oi_aggregate"] = safe_call("coinalyze_oi", _coinalyze_open_interest, flags)
    result["btc_long_short_ratio"] = safe_call(
        "coinalyze_ls_ratio", _coinalyze_long_short_ratio, flags
    )
    liq = safe_call("coinalyze_liquidation", _coinalyze_liquidation_24h, flags)
    if liq:
        result["btc_liq_long_24h"], result["btc_liq_short_24h"] = liq

    result["source_flags"] = flags.as_dict()
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_coinalyze(), indent=2))
