"""Kastara Finance — dashboard read-only (Phase 1 FE/BE).

Flask app kecil di atas kastara-finance.db. HANYA baca (SELECT), tidak menulis.
Pipeline tetap satu-satunya penulis DB.

Jalankan:
    python -m web.app
    # buka http://127.0.0.1:5000

Env (opsional): WEB_HOST, WEB_PORT.
"""
from __future__ import annotations

import json
import os

from flask import Flask, jsonify, render_template, request

from db.connection import get_connection, get_db_path, init_db

app = Flask(__name__)

# Kolom daily_market yang ditampilkan di snapshot (label -> kolom).
SNAPSHOT_FIELDS = {
    "BTC Close": "btc_close",
    "BTC Vol MA20": "btc_volume_ma20",
    "BTC Dominance %": "btc_dominance",
    "Funding Rate": "btc_funding_rate",
    "Fear & Greed": "fear_greed_value",
    "DXY": "dxy_close",
    "S&P 500": "sp500_close",
    "US10Y %": "us10y_yield",
    "VIX": "vix_close",
    "IHSG": "ihsg_close",
    "USD/IDR": "usd_idr",
    "USD/JPY": "usd_jpy",
    "Gold": "gold_close",
    "Net Liquidity": "net_liquidity",
}


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _parse_flags(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


# ---------- PAGES ----------

@app.route("/")
def index():
    return render_template("index.html")


# ---------- API ----------

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "db": str(get_db_path())})


@app.get("/api/latest")
def latest():
    """Snapshot daily_market terbaru + source_flags terurai."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM daily_market ORDER BY date DESC LIMIT 1"
        ).fetchone()
        news_count = conn.execute(
            "SELECT COUNT(*) c FROM daily_news WHERE date = "
            "(SELECT MAX(date) FROM daily_news)"
        ).fetchone()["c"]
    if row is None:
        return jsonify({"empty": True})
    data = dict(row)
    flags = _parse_flags(data.get("source_flags"))
    snapshot = [
        {"label": label, "column": col, "value": data.get(col)}
        for label, col in SNAPSHOT_FIELDS.items()
    ]
    return jsonify({
        "empty": False,
        "date": data["date"],
        "fear_greed_label": data.get("fear_greed_label"),
        "snapshot": snapshot,
        "source_flags": flags,
        "flag_summary": {
            "ok": sum(1 for v in flags.values() if v == "ok"),
            "fail": sum(1 for v in flags.values() if v == "fail"),
            "skip": sum(1 for v in flags.values() if v == "skip"),
        },
        "news_today": news_count,
    })


@app.get("/api/daily_market")
def daily_market():
    limit = min(request.args.get("limit", 60, type=int), 500)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM daily_market ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
    return jsonify(_rows_to_dicts(rows))


@app.get("/api/assets")
def assets():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT instrument FROM asset_ohlcv ORDER BY instrument"
        ).fetchall()
    return jsonify([r["instrument"] for r in rows])


@app.get("/api/asset_ohlcv")
def asset_ohlcv():
    instrument = request.args.get("instrument", "BTC")
    limit = min(request.args.get("limit", 90, type=int), 1000)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume, volume_ma20 "
            "FROM asset_ohlcv WHERE instrument = ? ORDER BY date DESC LIMIT ?",
            (instrument, limit),
        ).fetchall()
    # balik ke urutan lama->baru untuk chart
    return jsonify(list(reversed(_rows_to_dicts(rows))))


@app.get("/api/news")
def news():
    limit = min(request.args.get("limit", 50, type=int), 500)
    impact = request.args.get("impact")  # HIGH/MED/LOW filter opsional
    date = request.args.get("date")
    sql = "SELECT date, source, headline, raw_url, impact_level FROM daily_news"
    where, params = [], []
    if impact:
        where.append("impact_level = ?")
        params.append(impact.upper())
    if date:
        where.append("date = ?")
        params.append(date)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return jsonify(_rows_to_dicts(rows))


def main() -> None:
    init_db()  # pastikan tabel ada (walau kosong) supaya API tidak error
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "5000"))
    print(f"[web] Kastara dashboard -> http://{host}:{port}  (db={get_db_path()})")
    app.run(host=host, port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
