"""Crypto scraper: CoinGecko + Binance + Alternative.me (semua gratis, no key).

Output:
  daily_market: btc_open/high/low/close/volume, btc_dominance,
                btc_funding_rate, btc_oi, fear_greed_value, fear_greed_label
  asset_ohlcv : row instrument='BTC'

Acceptance:
  - fetch_btc() return dict, kolom non-None kecuali API down
  - fear_greed value 0-100
  - funding_rate desimal (mis. 0.0001), bukan persen
"""
from __future__ import annotations

import os
from typing import Any

from scrapers.base import SourceFlags, http_get_json, safe_call, today_wib

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
ALT_FNG = "https://api.alternative.me/fng/"

# Binance base URL bisa di-override lewat .env (untuk VPN / domain alternatif).
#   BINANCE_BASE      -> spot/market data (default api.binance.com;
#                        alternatif tanpa VPN: https://data-api.binance.vision)
#   BINANCE_FAPI_BASE -> futures (funding rate, open interest)
#   BINANCE_ENABLED   -> "0"/"false" untuk matikan Binance total (langsung fallback)
# Proxy global diatur via KASTARA_PROXY (lihat scrapers/base.py).
BINANCE_BASE = os.getenv("BINANCE_BASE", "https://api.binance.com").rstrip("/")
BINANCE_FAPI_BASE = os.getenv("BINANCE_FAPI_BASE", "https://fapi.binance.com").rstrip("/")


def binance_enabled() -> bool:
    """True kecuali BINANCE_ENABLED di-set ke 0/false/no."""
    return os.getenv("BINANCE_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def _binance_ohlcv() -> dict[str, float]:
    """BTCUSDT 1D candle terakhir yang sudah close (pakai 2 candle, ambil index -2)."""
    data = http_get_json(
        f"{BINANCE_BASE}/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "1d", "limit": 2},
        retries=1,  # fail fast — kalau VPN block, langsung ke fallback
    )
    # kline: [open_time, open, high, low, close, volume, close_time, ...]
    k = data[-1]
    return {
        "btc_open": float(k[1]),
        "btc_high": float(k[2]),
        "btc_low": float(k[3]),
        "btc_close": float(k[4]),
        "btc_volume": float(k[5]),
    }


def _binance_funding_rate() -> float:
    """Funding rate terakhir BTCUSDT perpetual (desimal, mis. 0.0001)."""
    data = http_get_json(
        f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate",
        params={"symbol": "BTCUSDT", "limit": 1},
        retries=1,
    )
    return float(data[-1]["fundingRate"])


def _binance_open_interest() -> float:
    """Open interest BTCUSDT perpetual (kontrak / BTC notional)."""
    data = http_get_json(
        f"{BINANCE_FAPI_BASE}/fapi/v1/openInterest",
        params={"symbol": "BTCUSDT"},
        retries=1,
    )
    return float(data["openInterest"])


def _coingecko_dominance() -> float:
    """BTC dominance (% dari total market cap)."""
    data = http_get_json(f"{COINGECKO_BASE}/global")
    return float(data["data"]["market_cap_percentage"]["btc"])


def _coingecko_ohlcv() -> dict[str, float]:
    """Fallback BTC OHLC + volume dari CoinGecko (kalau Binance ke-block).

    OHLC dari /coins/bitcoin/ohlc (days=1, granularity ~30m) diagregasi jadi
    1 candle harian. Volume (USD, 24h) dari /market_chart.
    """
    ohlc = http_get_json(
        f"{COINGECKO_BASE}/coins/bitcoin/ohlc",
        params={"vs_currency": "usd", "days": 1},
    )
    if not ohlc:
        raise ValueError("CoinGecko ohlc kosong")
    # tiap entri: [ts, open, high, low, close]
    opens = float(ohlc[0][1])
    highs = max(float(c[2]) for c in ohlc)
    lows = min(float(c[3]) for c in ohlc)
    closes = float(ohlc[-1][4])

    chart = http_get_json(
        f"{COINGECKO_BASE}/coins/bitcoin/market_chart",
        params={"vs_currency": "usd", "days": 1},
    )
    vols = chart.get("total_volumes") or []
    volume = float(vols[-1][1]) if vols else None

    return {
        "btc_open": opens, "btc_high": highs,
        "btc_low": lows, "btc_close": closes, "btc_volume": volume,
    }


def _fear_greed() -> dict[str, Any]:
    data = http_get_json(ALT_FNG, params={"limit": 1})
    item = data["data"][0]
    value = int(item["value"])
    if not 0 <= value <= 100:
        raise ValueError(f"fear_greed value di luar 0-100: {value}")
    return {
        "fear_greed_value": value,
        "fear_greed_label": item["value_classification"],
    }


def fetch_btc(date: str | None = None) -> dict[str, Any]:
    """Ambil semua data crypto BTC. Return dict siap di-merge ke daily_market.

    Selalu return dict (tidak melempar). Sertakan key 'source_flags' dan 'date'.
    """
    date = date or today_wib()
    flags = SourceFlags()
    result: dict[str, Any] = {
        "date": date,
        "btc_open": None, "btc_high": None, "btc_low": None,
        "btc_close": None, "btc_volume": None,
        "btc_dominance": None, "btc_funding_rate": None, "btc_oi": None,
        "fear_greed_value": None, "fear_greed_label": None,
    }

    if binance_enabled():
        ohlcv = safe_call("binance_ohlcv", _binance_ohlcv, flags)
    else:
        flags.skip("binance_ohlcv")
        print("[scraper:skip] Binance dimatikan (BINANCE_ENABLED=0) — pakai CoinGecko")
        ohlcv = None
    binance_reachable = ohlcv is not None
    if binance_reachable:
        result.update(ohlcv)
    else:
        # Binance ke-block/mati -> fallback CoinGecko untuk OHLC + volume.
        if binance_enabled():
            print("[scraper:switch] Binance tidak terjangkau — pakai CoinGecko (VPN?)")
        cg_ohlcv = safe_call("coingecko_ohlcv", _coingecko_ohlcv, flags)
        if cg_ohlcv:
            result.update(cg_ohlcv)

    if binance_reachable:
        result["btc_funding_rate"] = safe_call(
            "binance_funding", _binance_funding_rate, flags
        )
        result["btc_oi"] = safe_call("binance_oi", _binance_open_interest, flags)
    else:
        flags.skip("binance_funding")
        flags.skip("binance_oi")
        print("[scraper:skip] binance_funding, binance_oi — Binance dilewati")
    result["btc_dominance"] = safe_call(
        "coingecko_dominance", _coingecko_dominance, flags
    )

    fng = safe_call("alternative_fng", _fear_greed, flags)
    if fng:
        result.update(fng)

    result["source_flags"] = flags.as_dict()
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(fetch_btc(), indent=2))
