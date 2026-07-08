"""Kastara Finance — dashboard (Phase 1 read-only + Phase C write-enabled).

Flask app di atas kastara-finance.db. Endpoint /api/latest,daily_market,
assets,asset_ohlcv,news,health (Phase 1) TETAP read-only. `asset_ohlcv`
limit cap dinaikkan 1000->5000 (Panel 5 chart filter "Semua") -- perilaku
untuk pemanggil lama TIDAK berubah, cuma naikkan batas atas yang bisa diminta.
Endpoint baru Phase C (backfill, articles, policy, reading, signals,
synthesis, journal, prediction) MENULIS — lihat plan_c.txt. Semua tulisan
manual (form Giel) atau reuse fungsi yang sudah ada & teruji
(pipeline.backfill, pipeline.add_article, tools.review_signal, web.writes)
— TIDAK ADA logic AI/LLM atau execution/trading di sini.

Jalankan:
    python -m web.app
    # buka http://127.0.0.1:5000

Env (opsional): WEB_HOST, WEB_PORT. Tanpa auth (plan_c.txt §6.4 -- local-only).
"""
from __future__ import annotations

import json
import os

from flask import Flask, jsonify, render_template, request

import pipeline.add_article as add_article
import pipeline.backfill as backfill_mod
import tools.review_signal as review_signal
import web.writes as writes
from db.connection import get_connection, get_db_path, init_db
from scrapers.base import today_wib

app = Flask(__name__)

# Instrumen dengan data asli utk Panel 6 outlook (plan_c.txt keputusan #5 --
# USDJPY dikecualikan atas permintaan eksplisit Giel).
OUTLOOK_INSTRUMENTS = ["BTC", "SP500", "IHSG", "GOLD", "USDIDR"]

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
    # cap dinaikkan dari 1000 -> 5000 supaya filter chart "Semua" (Panel 5)
    # bisa tarik seluruh histori BTC (~4.300 baris) tanpa terpotong.
    # Perilaku untuk pemanggil lama (limit <=1000) tidak berubah.
    limit = min(request.args.get("limit", 90, type=int), 5000)
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
    sql = "SELECT id, date, source, headline, raw_url, impact_level, is_key_trigger FROM daily_news"
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


# ---------- PHASE C: Panel 1 — Manual Backfill ----------

@app.post("/api/backfill/preview")
def backfill_preview():
    body = request.get_json(force=True)
    result = backfill_mod.backfill(
        body["instrument"], body["from"], body["to"], preview_only=True,
    )
    return jsonify(result)


@app.post("/api/backfill/commit")
def backfill_commit():
    body = request.get_json(force=True)
    result = backfill_mod.backfill(
        body["instrument"], body["from"], body["to"], assume_yes=True,
    )
    return jsonify(result)


# ---------- PHASE C: Panel 2 — key trigger + manual article ----------

@app.post("/api/news/flag_key")
def news_flag_key():
    body = request.get_json(force=True)
    with get_connection() as conn:
        ok = writes.flag_key_trigger(conn, int(body["id"]), bool(body.get("is_key", True)))
        conn.commit()
    return jsonify({"ok": ok})


@app.post("/api/articles/add")
def articles_add():
    body = request.get_json(force=True)
    with get_connection() as conn:
        new_id = add_article.insert_article(
            conn,
            date=body.get("date") or today_wib(),
            source=body.get("source"), url=body.get("url"),
            headline=body["headline"], full_text=body.get("full_text"),
            personal_notes=body.get("notes"), tags=body.get("tags"),
            is_key_event=bool(body.get("key_event", False)),
        )
        conn.commit()
    return jsonify({"id": new_id})


# ---------- PHASE C: Panel 3 — Forward Panel ----------

@app.get("/api/econ_calendar")
def econ_calendar_list():
    """Event HIGH/MED, dari 7 hari lalu s.d. mendatang (dengan countdown hari).
    Window 7-hari-lalu ikut disertakan supaya event yang barusan rilis (mis.
    CPI kemarin) masih muncul buat diisi `actual`-nya secara manual --
    ForexFactory tidak pernah menyediakan kolom ini (lihat
    scrapers/econ_calendar.py)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM econ_calendar WHERE event_date >= date(?, '-7 days') "
            "AND importance IN ('HIGH','MED') ORDER BY event_date ASC LIMIT 40",
            (today_wib(),),
        ).fetchall()
    return jsonify(_rows_to_dicts(rows))


@app.post("/api/econ_calendar/actual")
def econ_calendar_set_actual():
    """Isi manual `actual` (hasil rilis) untuk 1 event by id."""
    body = request.get_json(force=True)
    event_id = body.get("id")
    actual = (body.get("actual") or "").strip()
    if not event_id or not actual:
        return jsonify({"error": "id dan actual wajib diisi"}), 400
    with get_connection() as conn:
        ok = writes.set_econ_actual(conn, event_id, actual)
        conn.commit()
    if not ok:
        return jsonify({"error": "event tidak ditemukan"}), 404
    return jsonify({"ok": True})


@app.get("/api/policy")
def policy_list():
    with get_connection() as conn:
        rows = writes.list_policy_notes(conn, limit=request.args.get("limit", 20, type=int))
    return jsonify(rows)


@app.post("/api/policy/add")
def policy_add():
    body = request.get_json(force=True)
    with get_connection() as conn:
        new_id = writes.insert_policy_note(
            conn, date=body.get("date") or today_wib(),
            speaker=body.get("speaker"), institution=body.get("institution"),
            source_url=body.get("source_url"), literal_statement=body["literal_statement"],
            stance_score=body.get("stance_score"), inference=body.get("inference"),
            inference_flag=body.get("inference_flag"), drift_note=body.get("drift_note"),
        )
        conn.commit()
    return jsonify({"id": new_id})


# ---------- PHASE C: Panel 4 — Reading Workspace ----------

@app.get("/api/reading")
def reading_list():
    date = request.args.get("date") or today_wib()
    with get_connection() as conn:
        rows = writes.list_reading_entries(conn, date)
    return jsonify(rows)


@app.post("/api/reading/save")
def reading_save():
    body = request.get_json(force=True)
    date = body.get("date") or today_wib()
    with get_connection() as conn:
        ids = writes.save_panel4(
            conn, date, gema=body.get("gema"), leon=body.get("leon"),
            akela=body.get("akela"), rivan=body.get("rivan"),
            external_ai=body.get("external_ai"), conflict=body.get("conflict"),
        )
        conn.commit()
    return jsonify({"ids": ids})


# ---------- PHASE C: Panel 5 — S&R zones, signals, approve/reject ----------

@app.get("/api/sr_zones")
def sr_zones_list():
    instrument = request.args.get("instrument", "BTC").upper()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sr_zones WHERE instrument = ? AND is_active = 1 "
            "ORDER BY zone_lower", (instrument,),
        ).fetchall()
    return jsonify(_rows_to_dicts(rows))


@app.get("/api/signals")
def signals_list():
    instrument = request.args.get("instrument", "BTC").upper()
    with get_connection() as conn:
        rows = review_signal.list_signals(conn, instrument=instrument, show_all=True, limit=200)
    return jsonify(rows)


@app.post("/api/signals/review")
def signals_review():
    body = request.get_json(force=True)
    with get_connection() as conn:
        ok = review_signal.set_review(
            conn, int(body["id"]), approved=bool(body["approved"]), notes=body.get("notes"),
        )
        conn.commit()
    return jsonify({"ok": ok})


# ---------- PHASE C: Panel 6 — Synthesis, journal, prediction log ----------

@app.get("/api/outlook_instruments")
def outlook_instruments():
    return jsonify(OUTLOOK_INSTRUMENTS)


@app.post("/api/synthesis/save")
def synthesis_save():
    body = request.get_json(force=True)
    date = body.get("date") or today_wib()
    with get_connection() as conn:
        new_id = writes.save_synthesis(conn, date, body.get("text", ""))
        conn.commit()
    return jsonify({"id": new_id})


@app.post("/api/journal/add")
def journal_add():
    body = request.get_json(force=True)
    with get_connection() as conn:
        new_id = writes.insert_trading_journal(
            conn, date=body.get("date") or today_wib(), instrument=body["instrument"],
            setup_type=body.get("setup_type"), entry_price=body.get("entry_price"),
            sl_price=body.get("sl_price"), tp1_price=body.get("tp1_price"),
            outcome=body.get("outcome"), personal_notes=body.get("personal_notes"),
            lesson_learned=body.get("lesson_learned"),
        )
        conn.commit()
    return jsonify({"id": new_id})


@app.post("/api/prediction/add")
def prediction_add():
    body = request.get_json(force=True)
    with get_connection() as conn:
        new_id = writes.insert_prediction(
            conn, date_made=body.get("date_made") or today_wib(), horizon=body["horizon"],
            claim=body["claim"], confidence=body.get("confidence"),
            basis=body.get("basis"), target_date=body["target_date"],
        )
        conn.commit()
    return jsonify({"id": new_id})


@app.get("/api/prediction/due")
def prediction_due():
    with get_connection() as conn:
        rows = writes.list_due_predictions(conn, today_wib())
    return jsonify(rows)


@app.post("/api/prediction/score")
def prediction_score():
    body = request.get_json(force=True)
    with get_connection() as conn:
        ok = writes.score_prediction(conn, int(body["id"]), body["outcome"], body.get("lesson"))
        conn.commit()
    return jsonify({"ok": ok})


def main() -> None:
    init_db()  # pastikan tabel ada (walau kosong) supaya API tidak error
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "5000"))
    print(f"[web] Kastara dashboard -> http://{host}:{port}  (db={get_db_path()})")
    app.run(host=host, port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
