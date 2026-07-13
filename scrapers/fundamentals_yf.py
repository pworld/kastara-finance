"""Scraper fundamentals kuartalan via yfinance (Phase J+ Build Contract
v1.3, J-4 -- Gerbang G3 dijawab Giel 13 Jul 2026: "bisa yfinance atau
langsung idx", yfinance dipakai duluan krn gratis & sudah diprototipe live
saat riset G3 awal (BBCA/BBRI/TLKM).

Target 8 kuartal per instrumen (kontrak §16/J-4). yfinance TERBUKTI cuma
kasih 5-6 kuartal ke belakang (dicek live di sini, sama dgn temuan
prototipe G3 sebelumnya) -- confidence='LOW_CONFIDENCE' otomatis kalau
<8, BUKAN ditolak (kontrak §16 poin 2: "jika hanya 4 -> grade jalan dengan
flag LOW_CONFIDENCE").

Field mapping (row yfinance -> kolom fundamentals_quarterly):
  Total Revenue          -> revenue
  Net Income             -> net_income
  Diluted EPS (fallback Basic EPS) -> eps
  Net Interest Income    -> net_interest_income, TAPI CUMA kalau
                            instrument_metadata.is_financial=1 -- field ini
                            representasi NIM bank (kontrak §3 komentar
                            schema: "khusus bank, NULL utk non-bank").
                            yfinance TERNYATA punya baris ini juga utk
                            perusahaan non-bank (dicek live utk TSLA) --
                            itu bukan NIM bank, jadi sengaja diabaikan utk
                            instrumen non-finansial, bukan bug.
  Stockholders Equity    -> total_equity
  Total Assets           -> total_assets
  Operating Cash Flow    -> operating_cash_flow
  Free Cash Flow         -> free_cash_flow (baris langsung dari yfinance,
                            tidak dihitung manual dari capex)

Pakai:
    python -m scrapers.fundamentals_yf BBCA
"""
from __future__ import annotations

from typing import Any

import yfinance as yf

from scrapers.base import SourceFlags, safe_call
from scrapers.equity_universe import yf_ticker_for

MIN_FULL_CONFIDENCE_QUARTERS = 8


def _is_nan(v: Any) -> bool:
    try:
        return v != v  # NaN != NaN, satu-satunya nilai yang punya sifat ini
    except Exception:  # noqa: BLE001
        return False


def _row(df, *names: str):
    """Ambil baris pertama yang ketemu dari beberapa nama alternatif
    (mis. 'Diluted EPS' lalu fallback 'Basic EPS')."""
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.index:
            return df.loc[name]
    return None


def _fetch_quarterly(ticker: str, is_financial: bool) -> list[dict[str, Any]]:
    t = yf.Ticker(ticker)
    qf = t.quarterly_financials
    qbs = t.quarterly_balance_sheet
    qcf = t.quarterly_cashflow
    if qf is None or qf.empty:
        raise ValueError(f"yfinance quarterly_financials kosong untuk {ticker}")

    revenue = _row(qf, "Total Revenue")
    net_income = _row(qf, "Net Income")
    eps = _row(qf, "Diluted EPS", "Basic EPS")
    nii = _row(qf, "Net Interest Income") if is_financial else None
    equity = _row(qbs, "Stockholders Equity")
    assets = _row(qbs, "Total Assets")
    ocf = _row(qcf, "Operating Cash Flow")
    fcf = _row(qcf, "Free Cash Flow")

    def val(series, col):
        if series is None or col not in series.index:
            return None
        v = series[col]
        return None if _is_nan(v) else float(v)

    quarters = list(qf.columns)
    n_with_data = sum(
        1 for q in quarters if val(revenue, q) is not None or val(net_income, q) is not None
    )
    confidence = "FULL" if n_with_data >= MIN_FULL_CONFIDENCE_QUARTERS else "LOW_CONFIDENCE"

    rows = []
    for q in quarters:
        row_revenue, row_net_income = val(revenue, q), val(net_income, q)
        if row_revenue is None and row_net_income is None:
            continue  # kuartal kosong total (kolom NaN semua) -- skip, bukan simpan 0
        rows.append({
            "quarter_end": q.strftime("%Y-%m-%d"),
            "revenue": row_revenue,
            "net_income": row_net_income,
            "eps": val(eps, q),
            "net_interest_income": val(nii, q),
            "total_equity": val(equity, q),
            "total_assets": val(assets, q),
            "operating_cash_flow": val(ocf, q),
            "free_cash_flow": val(fcf, q),
            "confidence": confidence,
        })
    return rows


def fetch_fundamentals_quarterly(instrument: str, market: str, is_financial: bool) -> dict[str, Any]:
    """Return {'rows': [...], 'source_flags': {...}}. Tidak pernah raise --
    pola SourceFlags/safe_call sama dgn scraper lain di project ini."""
    flags = SourceFlags()
    ticker = yf_ticker_for(instrument, market)
    rows = safe_call(
        f"fundamentals_{instrument}", lambda: _fetch_quarterly(ticker, is_financial), flags
    ) or []
    return {"rows": rows, "source_flags": flags.as_dict()}


if __name__ == "__main__":
    import json
    import sys

    inst = sys.argv[1] if len(sys.argv) > 1 else "BBCA"
    mkt = "IDX" if inst.upper() == "BBCA" else "US"
    print(json.dumps(fetch_fundamentals_quarterly(inst, mkt, is_financial=(inst.upper() == "BBCA")),
                      indent=2, default=str))
