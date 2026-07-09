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
from datetime import datetime, timedelta
from typing import Any

from flask import Flask, jsonify, render_template, request

import pipeline.add_article as add_article
import pipeline.backfill as backfill_mod
import tools.review_signal as review_signal
import web.writes as writes
from db.connection import get_connection, get_db_path, init_db
from notify.telegram import send_message
from pipeline.compose_briefing import compose_daily_briefing
from scrapers.base import today_wib

app = Flask(__name__)

# Instrumen dengan data asli utk Panel 6 outlook (plan_c.txt keputusan #5 --
# USDJPY dikecualikan atas permintaan eksplisit Giel).
OUTLOOK_INSTRUMENTS = ["BTC", "SP500", "IHSG", "GOLD", "USDIDR"]

# Kolom daily_market yang ditampilkan di snapshot, dikelompokkan per
# kategori (dashboard render per-grup, bukan 1 grid rata biar tidak menumpuk).
SNAPSHOT_FIELDS = [
    {"label": "BTC Close", "column": "btc_close", "category": "Crypto (BTC)"},
    {"label": "BTC Vol MA20", "column": "btc_volume_ma20", "category": "Crypto (BTC)"},
    {"label": "BTC Dominance %", "column": "btc_dominance", "category": "Crypto (BTC)"},
    {"label": "Funding Rate", "column": "btc_funding_rate", "category": "Crypto (BTC)"},
    {"label": "DXY", "column": "dxy_close", "category": "Makro Global"},
    {"label": "US10Y %", "column": "us10y_yield", "category": "Makro Global"},
    {"label": "VIX", "column": "vix_close", "category": "Makro Global"},
    {"label": "Fear & Greed", "column": "fear_greed_value", "category": "Makro Global"},
    {"label": "Net Liquidity", "column": "net_liquidity", "category": "Makro Global"},
    {"label": "S&P 500", "column": "sp500_close", "category": "Ekuitas & FX"},
    {"label": "IHSG", "column": "ihsg_close", "category": "Ekuitas & FX"},
    {"label": "USD/IDR", "column": "usd_idr", "category": "Ekuitas & FX"},
    {"label": "USD/JPY", "column": "usd_jpy", "category": "Ekuitas & FX"},
    {"label": "Gold", "column": "gold_close", "category": "Ekuitas & FX"},
]

# Perbandingan snapshot Panel 1 (kartu Hari/Minggu/Bulan/Tahun) — offset
# kalender kasar (bukan minggu/bulan/tahun ISO presisi), cukup utk "berapa
# hari lalu" sebagai titik pembanding. Cari row daily_market TERDEKAT
# <= tanggal target (bukan exact match) karena tidak tiap kalender hari
# pasti ada row (run_daily jalan manual, bisa ada jeda).
COMPARE_PERIODS = {"day": 1, "week": 7, "month": 30, "year": 365}

# Kolom snapshot yang instrument-nya juga ada di asset_ohlcv (histori JAUH
# lebih panjang di sana -- mis. BTC ~4300 baris sejak 2014 -- dibanding
# daily_market yang cuma punya 4-5 baris utk kolom2 ini krn baru mulai
# terisi sejak run_daily beneran jalan). Dipakai KHUSUS utk cari nilai masa
# lalu (week/month/year); nilai "saat ini" yang ditampilkan tetap dari
# daily_market seperti biasa.
COLUMN_TO_INSTRUMENT = {
    "btc_close": "BTC", "sp500_close": "SP500", "ihsg_close": "IHSG",
    "usd_idr": "USDIDR", "usd_jpy": "USDJPY", "gold_close": "GOLD",
}

# Data gap detection (Manual Backfill Panel 1) — tiap instrument dari
# pipeline.backfill.py, dipetakan ke (tabel sumber, kolom [None utk
# asset_ohlcv], kalender). Kalender menentukan tanggal mana yang "seharusnya
# ada": DAILY = tiap hari kalender (crypto, RRP -- dicek: RRP rilis harian
# per FRED), WEEKDAY = Senin-Jumat (ekuitas/forex/FRED harian biasa),
# WEEKLY_WED = rilis mingguan tiap Rabu (WALCL/TGA, dicek langsung ke FRED
# metadata) -- TIDAK di-gap-check krn "kosong" antar-Rabu itu NORMAL, bukan
# gap, cuma akan bikin false-positive kalau dipaksa cek harian.
INSTRUMENT_SOURCE = {
    "BTC": ("asset_ohlcv", None, "DAILY"),
    "SP500": ("asset_ohlcv", None, "WEEKDAY"),
    "IHSG": ("asset_ohlcv", None, "WEEKDAY"),
    "GOLD": ("asset_ohlcv", None, "WEEKDAY"),
    "USDIDR": ("asset_ohlcv", None, "WEEKDAY"),
    "USDJPY": ("asset_ohlcv", None, "WEEKDAY"),
    "DXY": ("daily_market", "dxy_close", "WEEKDAY"),
    "US10Y": ("daily_market", "us10y_yield", "WEEKDAY"),
    "VIX": ("daily_market", "vix_close", "WEEKDAY"),
    "HY": ("daily_market", "hy_credit_spread", "WEEKDAY"),
    "WALCL": ("daily_market", "walcl", "WEEKLY_WED"),
    "TGA": ("daily_market", "tga", "WEEKLY_WED"),
    "RRP": ("daily_market", "rrp", "DAILY"),
}


def _detect_gaps(dates: list[str], calendar: str) -> list[dict]:
    """Cari rentang tanggal yang "seharusnya ada" (sesuai `calendar`) tapi
    kosong di `dates`. Grup gap dihitung dari kerapatan tanggal EXPECTED
    (bukan kalender mentah), jadi weekend otomatis tidak dianggap gap utk
    kalender WEEKDAY. Cuma gap >= 2 hari expected berturut-turut yang
    dilaporkan (gap 1 hari = wajar/hari libur biasa, bukan tanda-tanda
    perlu backfill)."""
    if not dates or calendar == "WEEKLY_WED":
        return []
    existing = set(dates)
    date_objs = sorted(datetime.strptime(d, "%Y-%m-%d") for d in dates)
    start, end = date_objs[0], date_objs[-1]

    expected = []
    d = start
    while d <= end:
        if calendar == "DAILY" or d.weekday() < 5:
            expected.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)

    gaps = []
    run_start, run_len = None, 0
    for i, ds in enumerate(expected):
        if ds not in existing:
            if run_start is None:
                run_start = ds
            run_len += 1
        else:
            if run_start is not None and run_len >= 2:
                gaps.append({"from": run_start, "to": expected[i - 1], "days": run_len})
            run_start, run_len = None, 0
    if run_start is not None and run_len >= 2:
        gaps.append({"from": run_start, "to": expected[-1], "days": run_len})
    return gaps


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


def _compare_from_series(series: list[tuple[str, float]], latest_date: str, cur_val) -> dict:
    """Bandingkan `cur_val` (hari ini) vs D-1/W-1/M-1/Y-1 dari `series`
    ([(date, value), ...] terurut DESC baru->lama). Cari titik pertama
    dengan date <= target (bukan exact match) -- gap kalender wajar krn
    run_daily manual / weekend tidak ada data equity."""
    compare: dict[str, Any] = {}
    latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
    for period, days_ago in COMPARE_PERIODS.items():
        target = (latest_dt - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        past_date, past_val = None, None
        for d, v in series:
            if d <= target and v is not None:
                past_date, past_val = d, v
                break
        if cur_val is None or past_val is None:
            compare[period] = None
            continue
        delta = cur_val - past_val
        compare[period] = {
            "past_value": past_val,
            "past_date": past_date,
            "delta": delta,
            "pct": (delta / past_val * 100) if past_val else None,
        }
    return compare


@app.get("/api/latest")
def latest():
    """Snapshot daily_market terbaru + source_flags terurai + perbandingan
    Hari/Minggu/Bulan/Tahun per metric (utk kartu Panel 1). Kolom yang ada
    padanan instrument-nya di asset_ohlcv (lihat COLUMN_TO_INSTRUMENT) pakai
    histori dari sana utk pembanding (jauh lebih panjang dari daily_market)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM daily_market ORDER BY date DESC LIMIT 1"
        ).fetchone()
        news_count = conn.execute(
            "SELECT COUNT(*) c FROM daily_news WHERE date = "
            "(SELECT MAX(date) FROM daily_news)"
        ).fetchone()["c"]
        series_by_col: dict[str, list[tuple[str, float]]] = {}
        if row is not None:
            hist_rows = conn.execute(
                "SELECT * FROM daily_market WHERE date <= ? "
                "ORDER BY date DESC LIMIT 400",
                (row["date"],),
            ).fetchall()
            market_hist = _rows_to_dicts(hist_rows)
            for field in SNAPSHOT_FIELDS:
                col = field["column"]
                if col not in COLUMN_TO_INSTRUMENT:
                    series_by_col[col] = [(r["date"], r.get(col)) for r in market_hist]
            for col, instrument in COLUMN_TO_INSTRUMENT.items():
                ohlcv_rows = conn.execute(
                    "SELECT date, close FROM asset_ohlcv WHERE instrument = ? "
                    "AND date <= ? ORDER BY date DESC LIMIT 2000",
                    (instrument, row["date"]),
                ).fetchall()
                series_by_col[col] = [(r["date"], r["close"]) for r in ohlcv_rows]
    if row is None:
        return jsonify({"empty": True})
    data = dict(row)
    flags = _parse_flags(data.get("source_flags"))
    snapshot = [
        {
            "label": field["label"], "column": field["column"], "category": field["category"],
            "value": data.get(field["column"]),
            "compare": _compare_from_series(
                series_by_col.get(field["column"], []), data["date"], data.get(field["column"])
            ),
        }
        for field in SNAPSHOT_FIELDS
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

@app.get("/api/data_gaps")
def data_gaps():
    """Cek data bolong utk 1 instrument (dipanggil dashboard Manual Backfill
    tiap instrument dropdown berubah) — biar kelihatan ada gap SEBELUM
    Giel harus tebak sendiri lewat trial-and-error backfill."""
    instrument = request.args.get("instrument", "BTC").upper()
    if instrument not in INSTRUMENT_SOURCE:
        return jsonify({"error": f"instrument tidak dikenal: {instrument}"}), 400
    source, col, calendar = INSTRUMENT_SOURCE[instrument]
    with get_connection() as conn:
        if source == "asset_ohlcv":
            rows = conn.execute(
                "SELECT date FROM asset_ohlcv WHERE instrument = ? ORDER BY date", (instrument,)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT date FROM daily_market WHERE {col} IS NOT NULL ORDER BY date"
            ).fetchall()
    dates = [r["date"] for r in rows]

    if not dates:
        return jsonify({
            "instrument": instrument, "calendar": calendar, "total_rows": 0,
            "date_from": None, "date_to": None, "gaps": [], "gaps_total_count": 0,
        })

    gaps = _detect_gaps(dates, calendar)
    gaps.sort(key=lambda g: g["days"], reverse=True)
    return jsonify({
        "instrument": instrument, "calendar": calendar, "total_rows": len(dates),
        "date_from": dates[0], "date_to": dates[-1],
        "gaps": gaps[:20], "gaps_total_count": len(gaps),
    })


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


@app.get("/api/expectations")
def expectations_list():
    with get_connection() as conn:
        rows = writes.list_expectations(conn, limit=request.args.get("limit", 20, type=int))
    return jsonify(rows)


@app.post("/api/expectations/add")
def expectations_add():
    """Manual entry (Layer B): CME FedWatch cut probability, Dot Plot median,
    dll — tidak ada sumber gratis yang scrape-able (lihat plan_d.txt)."""
    body = request.get_json(force=True)
    with get_connection() as conn:
        new_id = writes.insert_expectation(
            conn, date=body.get("date") or today_wib(), metric=body["metric"],
            value=body["value"], horizon=body.get("horizon"), source=body.get("source"),
        )
        conn.commit()
    return jsonify({"id": new_id})


@app.get("/api/positioning")
def positioning_list():
    with get_connection() as conn:
        rows = writes.list_positioning(conn, limit=request.args.get("limit", 30, type=int))
    return jsonify(rows)


@app.post("/api/positioning/add")
def positioning_add():
    """Manual entry/override (Layer C): SBN foreign flow (sumber DJPPR tidak
    scrape-able), atau koreksi manual atas row COT/ETF hasil scrape."""
    body = request.get_json(force=True)
    with get_connection() as conn:
        writes.insert_positioning_manual(
            conn, date=body.get("date") or today_wib(), instrument=body["instrument"],
            metric=body["metric"], value=body["value"], source=body.get("source") or "manual",
        )
        conn.commit()
    return jsonify({"ok": True})


@app.get("/api/disonansi")
def disonansi_get():
    with get_connection() as conn:
        result = writes.compute_disonansi(conn)
    return jsonify(result)


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


@app.post("/api/briefing/send")
def briefing_send():
    """Rakit Daily Briefing (Phase E) + kirim ke Telegram. Dipicu manual
    dari tombol Panel 6 setelah Giel selesai isi Panel 4-6 — lihat
    plan_e.txt. Return teks yang dirakit + status kirim, supaya tetap
    kelihatan hasilnya walau TELEGRAM_BOT_TOKEN belum di-set (ok=False)."""
    body = request.get_json(force=True) if request.data else {}
    date = body.get("date") or today_wib()
    with get_connection() as conn:
        text = compose_daily_briefing(conn, date)
    ok = send_message(text)
    return jsonify({"text": text, "sent": ok})


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
