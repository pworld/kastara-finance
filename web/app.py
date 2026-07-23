"""Kastara Finance — dashboard (Phase 1 read-only + Phase C write-enabled).

Flask app di atas kastara-finance.db. Endpoint /api/latest,daily_market,
assets,asset_ohlcv,news,health (Phase 1) TETAP read-only. `asset_ohlcv`
limit cap dinaikkan 1000->5000 (Panel 5 chart filter "Semua") -- perilaku
untuk pemanggil lama TIDAK berubah, cuma naikkan batas atas yang bisa diminta.
Endpoint baru Phase C (backfill, articles, policy, reading, signals,
synthesis, journal, prediction) MENULIS — lihat plan_c.txt. Semua tulisan
manual (form Giel) atau reuse fungsi yang sudah ada & teruji
(pipeline.backfill, pipeline.add_article, tools.review_signal, web.writes)
— TIDAK ADA logic AI/LLM atau execution/trading di sini, KECUALI
/api/persona/run (Panel 4, deviasi eksplisit -- lihat llm/persona_analysis.py).

Jalankan:
    cd web/frontend && npm run build   # sekali, atau tiap kali FE berubah
    python -m web.app
    # buka http://127.0.0.1:5000

Frontend Vue (`web/frontend/`, lihat docs/migrationFE.md) di-build ke
`web/frontend/dist/` dan disajikan langsung oleh Flask (route SPA catch-all
di bagian bawah file ini) -- SATU proses, SATU port, tanpa Vite dev server
perlu jalan bareng utk pemakaian sehari-hari (dev aktif FE tetap pakai
`npm run dev` terpisah + proxy, lihat vite.config.js).

Env: WEB_HOST, WEB_PORT (opsional). **DASHBOARD_PASSWORD wajib** (session
auth sederhana, lihat §Auth di bawah -- dashboard ini sekarang bisa dibuka
dari mana saja setelah `/` diproxy/expose, beda dari sebelumnya yang
local-only tanpa auth). FLASK_SECRET_KEY opsional (kalau kosong,
di-generate random tiap start -- sesi akan ke-invalidate tiap restart
proses; isi di .env kalau mau sesi tahan lintas restart).
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory, session

import llm.persona_analysis as persona_analysis
import pipeline.add_article as add_article
import pipeline.backfill as backfill_mod
import tools.review_signal as review_signal
import web.writes as writes
from analysis.sizing import suggest_position_size
from db.connection import get_connection, get_db_path, init_db
from indicators.calc import compare_from_series
from notify.telegram import send_message
from pipeline.compose_briefing import compose_daily_briefing
from pipeline.compose_persona_context import compose_persona_context
from pipeline.run_grader import run_grader
from scrapers.base import today_wib
from scrapers.idx_uma import fetch_uma_announcements, is_recently_flagged, uma_history_for

app = Flask(__name__, static_folder=None)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

# ---------- Auth (session sederhana, ganti dari "tanpa auth" plan_c.txt §6.4
# -- dashboard Vue sekarang satu proses/port dgn API, siap di-expose kalau
# Giel deploy. DASHBOARD_PASSWORD WAJIB diisi manual di .env -- TIDAK PERNAH
# di-generate/default oleh kode (itu kredensial, bukan angka placeholder spt
# RISK_CAPITAL_*). Kosong -> login endpoint menolak dgn pesan jelas, bukan
# diam-diam membolehkan siapa saja masuk. ----------
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "").strip()
AUTH_EXEMPT_API_PATHS = {"/api/auth/login", "/api/auth/status"}
FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


@app.before_request
def _require_auth():
    """Guard SEMUA /api/* (kecuali login/status) di belakang session.
    Route non-API (shell SPA + asset statis) SELALU lolos -- Vue Router yang
    tampilkan halaman login berdasar /api/auth/status, bukan redirect Flask,
    supaya routing client-side (history mode) tetap utuh."""
    if request.path.startswith("/api/") and request.path not in AUTH_EXEMPT_API_PATHS:
        if not session.get("authed"):
            return jsonify({"error": "unauthorized"}), 401

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
    {"label": "OI Agregat (Coinalyze)", "column": "btc_oi_aggregate", "category": "Crypto (BTC)"},
    {"label": "Long/Short Ratio", "column": "btc_long_short_ratio", "category": "Crypto (BTC)"},
    {"label": "Liquidation Long 24h", "column": "btc_liq_long_24h", "category": "Crypto (BTC)"},
    {"label": "Liquidation Short 24h", "column": "btc_liq_short_24h", "category": "Crypto (BTC)"},
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


def _all_instruments_with_gaps(conn) -> list[dict]:
    """Deteksi gap utk SEMUA instrument yang dikenal backfill sekaligus --
    macro (`INSTRUMENT_SOURCE`) + universe ekuitas Phase J+
    (`instrument_metadata`, kalender WEEKDAY -- bursa saham/FX, sama seperti
    entri ekuitas macro yang sudah ada). Dipakai tombol "Cek & Backfill Semua
    Gap" Panel 1 -- info gap per-instrument sudah lengkap dari sistem
    (`/api/data_gaps`), jadi Giel tidak perlu pilih instrument satu-satu di
    dropdown utk tahu apa yang bolong.

    Instrument TANPA histori sama sekali (`total_rows=0`) DILEWATI -- itu
    backfill awal yang butuh keputusan sadar (instrument mana, dari tanggal
    berapa), bukan "isi gap" otomatis. Kalender WEEKLY_WED juga dilewati
    (sama seperti `/api/data_gaps` -- kosong antar-Rabu itu wajar)."""
    macro = [(name, *info) for name, info in INSTRUMENT_SOURCE.items()]
    equity_rows = conn.execute("SELECT instrument FROM instrument_metadata").fetchall()
    equity = [(r["instrument"], "asset_ohlcv", None, "WEEKDAY") for r in equity_rows]

    out = []
    for instrument, source, col, calendar in macro + equity:
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
            continue
        gaps = _detect_gaps(dates, calendar)
        if not gaps:
            continue
        out.append({
            "instrument": instrument,
            "gap_from": min(g["from"] for g in gaps),
            "gap_to": max(g["to"] for g in gaps),
            "gaps_count": len(gaps),
        })
    return out


def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _parse_flags(raw) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


# ---------- Auth endpoints ----------

@app.post("/api/auth/login")
def auth_login():
    if not DASHBOARD_PASSWORD:
        return jsonify({"error": "DASHBOARD_PASSWORD belum di-set di .env -- login tidak bisa dipakai"}), 500
    body = request.get_json(force=True)
    password = body.get("password", "")
    if not secrets.compare_digest(password, DASHBOARD_PASSWORD):
        return jsonify({"error": "Password salah"}), 401
    session.permanent = True
    session["authed"] = True
    return jsonify({"ok": True})


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/auth/status")
def auth_status():
    return jsonify({
        "authenticated": bool(session.get("authed")),
        "password_configured": bool(DASHBOARD_PASSWORD),
    })


# ---------- API ----------

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "db": str(get_db_path())})


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
            "compare": compare_from_series(
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
    date = request.args.get("date")            # exact match (dipakai Panel 4 key news)
    date_from = request.args.get("date_from")  # rentang (Panel 2 filter from/to)
    date_to = request.args.get("date_to")
    # Addendum C §21.2: key_only -> for_reading (rename fungsional dari
    # is_key_trigger -- kurasi "penting utk dibaca", beda dari tag klasifikasi).
    reading_only = request.args.get("for_reading")
    sql = ("SELECT id, date, source, headline, raw_url, impact_level, "
           "display_subtitle, for_reading, rss_summary FROM daily_news")
    where, params = [], []
    if impact:
        where.append("impact_level = ?")
        params.append(impact.upper())
    if date:
        where.append("date = ?")
        params.append(date)
    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to)
    if reading_only and reading_only not in ("0", "false", ""):
        where.append("for_reading = 1")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        rows = _rows_to_dicts(conn.execute(sql, params).fetchall())
        # News Threads N-1 (Addendum B §20.5): tempel info thread_link kalau
        # ada, biar NewsView bisa render chip "Saran: <thread>?" tanpa
        # endpoint terpisah.
        rows = writes.attach_thread_suggestions(conn, rows)
        # Faceted Tagging C-1 (Addendum C §21): tempel tag terpasang per baris.
        rows = writes.attach_content_tags(conn, "daily_news", rows)
    return jsonify(rows)


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


@app.post("/api/backfill/all/preview")
def backfill_all_preview():
    """Preview backfill utk SEMUA instrument yang punya gap sekaligus --
    reuse `_all_instruments_with_gaps()` (DB-only, cepat) utk cari kandidat,
    lalu `backfill_mod.backfill()` (network fetch) per instrument utk range
    gap-nya masing-masing. Instrument yang gagal fetch dicatat error-nya,
    TIDAK menghentikan instrument lain (pola sama `safe_call` scraper)."""
    with get_connection() as conn:
        candidates = _all_instruments_with_gaps(conn)
    results = []
    for c in candidates:
        try:
            r = backfill_mod.backfill(c["instrument"], c["gap_from"], c["gap_to"], preview_only=True)
        except Exception as exc:  # noqa: BLE001
            results.append({"instrument": c["instrument"], "error": str(exc)})
            continue
        if r["new"] > 0:
            results.append({**r, "from": c["gap_from"], "to": c["gap_to"]})
    return jsonify({"results": results})


@app.post("/api/backfill/all/commit")
def backfill_all_commit():
    """Commit backfill utk item yang SUDAH di-preview (body: `{"items":
    [{"instrument","from","to"}, ...]}`) -- BUKAN deteksi ulang gap, supaya
    commit persis sesuai apa yang ditampilkan preview (hindari drift kalau
    gap berubah di antara 2 request)."""
    body = request.get_json(force=True)
    results = []
    for item in body.get("items", []):
        try:
            r = backfill_mod.backfill(item["instrument"], item["from"], item["to"], assume_yes=True)
        except Exception as exc:  # noqa: BLE001
            results.append({"instrument": item["instrument"], "error": str(exc)})
            continue
        results.append(r)
    return jsonify({"results": results})


# ---------- PHASE C: Panel 2 — for_reading curation + manual article
# (Addendum C §21.2: was "flag_key" / is_key_trigger, renamed) ----------

@app.post("/api/news/for_reading")
def news_set_for_reading():
    body = request.get_json(force=True)
    with get_connection() as conn:
        ok = writes.set_for_reading(conn, int(body["id"]), bool(body.get("for_reading", True)))
        conn.commit()
    return jsonify({"ok": ok})


@app.post("/api/news/<int:news_id>/display_subtitle")
def news_set_display_subtitle(news_id):
    body = request.get_json(force=True)
    with get_connection() as conn:
        ok = writes.set_display_subtitle(conn, news_id, body.get("display_subtitle"))
        conn.commit()
    if not ok:
        return jsonify({"error": "berita tidak ditemukan"}), 404
    return jsonify({"ok": True})


# ---------- Faceted Tagging (Addendum C §21, GELOMBANG C-1) ----------

@app.get("/api/tags")
def tags_list():
    with get_connection() as conn:
        rows = writes.list_tags(conn, facet=request.args.get("facet"))
    return jsonify(rows)


@app.post("/api/tags")
def tags_create():
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            row = writes.create_tag(
                conn, body.get("canonical", ""), aliases=body.get("aliases"),
                description=body.get("description"),
            )
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(row)


@app.post("/api/content_tags")
def content_tags_apply():
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            row = writes.apply_tag(
                conn, body.get("ref_table", ""), body.get("ref_id"),
                body.get("tag", ""), source=body.get("source", "MANUAL"),
            )
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(row)


@app.post("/api/content_tags/<int:content_tag_id>/remove")
def content_tags_remove(content_tag_id):
    with get_connection() as conn:
        ok = writes.remove_tag(conn, content_tag_id)
        conn.commit()
    if not ok:
        return jsonify({"error": "tag pada konten ini tidak ditemukan"}), 404
    return jsonify({"ok": True})


@app.get("/api/content_tags/<ref_table>/<int:ref_id>")
def content_tags_list(ref_table, ref_id):
    with get_connection() as conn:
        rows = writes.list_content_tags(conn, ref_table, ref_id)
    return jsonify(rows)


# ---------- Settings -> Tag & Thread Management (Addendum C §21.11, C-1 gap
# ditutup 17 Jul 2026 -- kurasi lambat/reflektif, terpisah dari command-
# palette News/Reading di atas). ----------

@app.get("/api/tags/orphans")
def tags_orphans():
    with get_connection() as conn:
        rows = writes.list_orphan_tags(conn)
    return jsonify(rows)


@app.post("/api/tags/<int:tag_id>")
def tags_update(tag_id):
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            row = writes.update_tag(
                conn, tag_id, description=body.get("description"), facet=body.get("facet"),
            )
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(row)


@app.post("/api/tags/<int:tag_id>/delete")
def tags_delete(tag_id):
    body = request.get_json(force=True) or {}
    try:
        with get_connection() as conn:
            ok = writes.delete_tag(conn, tag_id, force=bool(body.get("force")))
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ok:
        return jsonify({"error": "tag tidak ditemukan"}), 404
    return jsonify({"ok": True})


@app.post("/api/tags/merge")
def tags_merge():
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            row = writes.merge_tag(conn, body.get("from_id"), body.get("into_id"))
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(row)


@app.get("/api/threads/stats")
def threads_stats():
    with get_connection() as conn:
        rows = writes.list_threads_with_stats(conn)
    return jsonify(rows)


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


@app.get("/api/earnings")
def earnings_list():
    """Earnings emiten universe (30 hari lalu s.d. mendatang) -- READ-ONLY,
    diisi scraper J-7. Ditampilkan di Forward panel bareng econ_calendar."""
    with get_connection() as conn:
        rows = writes.list_earnings_calendar(conn, limit=request.args.get("limit", 40, type=int))
    return jsonify(rows)


@app.get("/api/earnings/warnings")
def earnings_warnings():
    """Peringatan earnings utk posisi ONGOING (kontrak §19.5 + §18 keputusan
    #3 no-hold-through-earnings saham AS)."""
    with get_connection() as conn:
        rows = writes.list_earnings_warnings(conn, within_days=request.args.get("within_days", 14, type=int))
    return jsonify(rows)


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


@app.get("/api/persona/status")
def persona_status_route():
    return jsonify(persona_analysis.persona_status())


@app.post("/api/persona/run")
def persona_run():
    """Generate 1 analisa persona via OpenRouter (deviasi eksplisit dari
    plan_c.txt §0 -- lihat llm/persona_analysis.py). Konteks (snapshot pasar
    + berita key hari ini) SAMA utk ke-4 persona; system prompt masing-masing
    yang menentukan sudut pandang."""
    body = request.get_json(force=True)
    lens = (body.get("lens") or "").upper()
    if lens not in persona_analysis.PERSONA_LABELS:
        return jsonify({"error": f"lens tidak dikenal: {lens}"}), 400
    # Addendum C §21.4 (GELOMBANG C-2): opsional, berita pilihan manual Giel
    # (filter tag -> centang -> "Kirim ke Lensa" di NewsView) ditambahkan ke
    # konteks -- TIDAK PERNAH menggantikan slice (guard di compose_persona_
    # context itu sendiri, bukan di sini).
    news_ids = body.get("news_ids") or []
    date = today_wib()
    with get_connection() as conn:
        context_text = compose_persona_context(conn, date, lens, extra_news_ids=news_ids)
    try:
        text = persona_analysis.run_persona_analysis(lens, context_text)
    except persona_analysis.PersonaPromptMissing as exc:
        return jsonify({"error": str(exc), "prompt_missing": True}), 400
    except Exception as exc:  # noqa: BLE001 -- kasih tahu Giel penyebabnya, bukan diam-diam gagal
        return jsonify({"error": f"Gagal panggil OpenRouter: {exc}"}), 502
    with get_connection() as conn:
        writes.save_persona_analysis(conn, date, lens, text)
        conn.commit()
    return jsonify({"lens": lens, "date": date, "text": text})


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


@app.get("/api/synthesis")
def synthesis_get():
    """Teks synthesis terbaru utk 1 tanggal (auto-load Panel 6 saat ganti tanggal)."""
    date = request.args.get("date") or today_wib()
    with get_connection() as conn:
        text = writes.latest_synthesis(conn, date)
    return jsonify({"date": date, "text": text or ""})


@app.get("/api/outlook")
def outlook_get():
    """{instrument: stance} outlook tersimpan utk 1 tanggal (restore dropdown)."""
    date = request.args.get("date") or today_wib()
    with get_connection() as conn:
        result = writes.list_outlook(conn, date)
    return jsonify(result)


@app.post("/api/outlook/save")
def outlook_save():
    body = request.get_json(force=True)
    date = body.get("date") or today_wib()
    with get_connection() as conn:
        writes.save_outlook(conn, date, body["instrument"], body["stance"])
        conn.commit()
    return jsonify({"ok": True})


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
            planned_size=body.get("planned_size"), actual_size=body.get("actual_size"),
            skip_reason=body.get("skip_reason"), return_asset_ccy=body.get("return_asset_ccy"),
            return_idr=body.get("return_idr"),
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


# ---------- Panel 7: Riwayat (arsip input manual — read-only) ----------

@app.get("/api/synthesis/log")
def synthesis_log():
    with get_connection() as conn:
        rows = writes.list_synthesis_log(conn, limit=request.args.get("limit", 200, type=int))
    return jsonify(rows)


@app.get("/api/predictions")
def predictions_all():
    with get_connection() as conn:
        rows = writes.list_predictions(conn, limit=request.args.get("limit", 200, type=int))
    return jsonify(rows)


@app.get("/api/journal")
def journal_all():
    with get_connection() as conn:
        rows = writes.list_trading_journal(conn, limit=request.args.get("limit", 200, type=int))
    return jsonify(rows)


@app.get("/api/reading/history")
def reading_history():
    with get_connection() as conn:
        rows = writes.list_reading_history(conn, limit=request.args.get("limit", 200, type=int))
    return jsonify(rows)


# ---------- PHASE J+: Panel 8 — Universe & Grader (Build Contract v1.3 §19,
# J-14 Gelombang 1). Grader (fund_score/quadrant) belum jalan (J-11) --
# list_universe() balikin None utk kolom itu sampai modulnya dibangun. ----------

@app.get("/api/universe")
def universe_list():
    with get_connection() as conn:
        rows = writes.list_universe(conn)
    return jsonify(rows)


@app.get("/api/instrument_meta")
def instrument_meta_get():
    """1 row instrument_metadata utk badge LANE Panel 5. {} kalau instrumen
    (aset makro/index BTC/GOLD/dll) tidak punya row -- lane cuma berlaku
    utk saham individual Phase J+."""
    instrument = request.args.get("instrument", "")
    with get_connection() as conn:
        meta = writes.get_instrument_meta(conn, instrument)
    return jsonify(meta or {})


@app.post("/api/intake")
def intake_add():
    """Komponen C Gelombang 1: form intake kandidat baru -> instrument_metadata.
    Guard lane (INVEST/NONE only) ada di web.writes.save_intake_metadata,
    bukan cuma di sini -- lihat docstring fungsi itu."""
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            row = writes.save_intake_metadata(
                conn, instrument=body["instrument"], market=body["market"],
                sector=body.get("sector"), asset_class=body.get("asset_class") or "equity",
                market_cap=body.get("market_cap"), free_float=body.get("free_float"),
                lot_size=body.get("lot_size"), lane=body.get("lane") or "INVEST",
                is_financial=bool(body.get("is_financial")),
                has_daily_limit=bool(body.get("has_daily_limit")),
                has_real_volume=body.get("has_real_volume", True),
                accounting_std=body.get("accounting_std"), fx_exposure=body.get("fx_exposure"),
                data_as_of_rule=body.get("data_as_of_rule"),
            )
            conn.commit()
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(row)


# ---------- PHASE J+: Panel 8 Komponen C Gelombang 2 — intake workflow
# penuh (Build Contract v1.3 §19.3/§16, J-12). Rubrik SAMA dgn universe
# existing (reuse run_grader/idx_uma, tidak ada logic terpisah). ----------

@app.get("/api/intake/integrity_check")
def intake_integrity_check():
    """Cek UMA utk 1 ticker -- tombol 'Jalankan Cek Integritas'. Read-only,
    TIDAK menulis apa pun (beda dari /api/intake/grade)."""
    instrument = request.args.get("instrument", "").upper()
    uma_result = fetch_uma_announcements()
    history = uma_history_for(uma_result["items"], instrument)
    return jsonify({
        "instrument": instrument,
        "uma_active": is_recently_flagged(uma_result["items"], instrument),
        "uma_history": history[:5],
        "source_flags": uma_result["source_flags"],
    })


@app.post("/api/intake/grade")
def intake_grade_run():
    """Jalankan grade utk 1 instrumen -- tombol 'Jalankan Grade'. Reuse
    run_grader() (J-11 orchestrator persis, bukan logic terpisah) --
    MENULIS ke emiten_grade/grader_log, sama seperti run_grader biasa."""
    body = request.get_json(force=True)
    instrument = (body.get("instrument") or "").upper()
    if not instrument:
        return jsonify({"error": "instrument wajib diisi"}), 400
    summary = run_grader(instrument=instrument)
    if instrument not in summary:
        return jsonify({"error": f"instrumen {instrument} tidak ditemukan di instrument_metadata"}), 404
    return jsonify({"instrument": instrument, **summary[instrument]})


@app.post("/api/intake/decision")
def intake_decision_save():
    """Catat keputusan Giel (universe/watchlist/tolak) + alasan wajib.
    Guard `reason` non-kosong & `decision` valid ada di web.writes,
    bukan cuma di sini."""
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            new_id = writes.save_intake_decision(
                conn, instrument=body["instrument"], decision=body["decision"],
                reason=body.get("reason", ""), grade_snapshot=body.get("grade_snapshot"),
            )
            conn.commit()
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": new_id})


@app.get("/api/intake/log")
def intake_log_list():
    with get_connection() as conn:
        rows = writes.list_intake_log(conn, limit=request.args.get("limit", 100, type=int))
    return jsonify(rows)


# ---------- PHASE J+: Sizing engine wiring (Build Contract v1.3 §14, J-13)
# ke Trading Journal Panel 6. HANYA utk instrumen di instrument_metadata
# (lot_size diketahui) -- capital dibaca dari .env, TIDAK ditebak/di-
# hardcode. Kalau env kosong, balikin error eksplisit, bukan angka fiktif. ----------

@app.get("/api/sizing/suggest")
def sizing_suggest():
    instrument = request.args.get("instrument", "").upper()
    entry = request.args.get("entry", type=float)
    sl = request.args.get("sl", type=float)
    if not instrument or entry is None or sl is None:
        return jsonify({"error": "instrument, entry, sl wajib diisi"}), 400
    with get_connection() as conn:
        meta = writes.get_instrument_meta(conn, instrument)
    if not meta:
        return jsonify({
            "error": f"{instrument} tidak ada di instrument_metadata -- sizing engine "
                     "(lot quantization) cuma berlaku utk universe Phase J+ (saham individual)",
        }), 404
    env_var = "RISK_CAPITAL_IDR" if meta["market"] == "IDX" else "RISK_CAPITAL_USD"
    capital_raw = os.getenv(env_var, "").strip()
    if not capital_raw:
        return jsonify({
            "error": f"{env_var} belum diisi di .env -- isi modal riil dulu (lihat "
                     ".env.example) sebelum sizing engine bisa hitung apa pun",
        }), 400
    try:
        capital = float(capital_raw)
        result = suggest_position_size(
            entry, sl, capital, meta["lot_size"] or 0,
            has_daily_limit=bool(meta.get("has_daily_limit")),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


# ---------- PHASE J+: Rasio prudential bank (CAR/NPL/NIM/LDR), MANUAL,
# kontrak §2 J7/J-6 (Giel baca dari laporan resmi bank, yfinance tidak
# punya field ini). ----------

@app.post("/api/fundamentals/bank_ratios")
def bank_ratios_save():
    body = request.get_json(force=True)
    with get_connection() as conn:
        writes.save_bank_ratios_manual(
            conn, instrument=body["instrument"], quarter_end=body["quarter_end"],
            car=body.get("car"), npl_gross=body.get("npl_gross"),
            nim=body.get("nim"), ldr=body.get("ldr"),
        )
        conn.commit()
    return jsonify({"ok": True})


@app.get("/api/fundamentals/bank_ratios")
def bank_ratios_list():
    instrument = request.args.get("instrument", "").upper()
    with get_connection() as conn:
        rows = writes.list_bank_ratios(conn, instrument)
    return jsonify(rows)


# ---------- PHASE J+: Panel 8 Komponen B/D — detail emiten, override,
# grader log (Addendum A §19.2/§19.4, J-15). ----------

@app.get("/api/emiten/<ticker>")
def emiten_detail(ticker):
    with get_connection() as conn:
        detail = writes.get_emiten_detail(conn, ticker)
    if detail is None:
        return jsonify({"error": f"{ticker} tidak ada di instrument_metadata"}), 404
    return jsonify(detail)


@app.post("/api/emiten/<ticker>/override")
def emiten_override(ticker):
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            ok = writes.save_grade_override(conn, ticker, body.get("quadrant"), body.get("reason", ""))
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ok:
        return jsonify({"error": f"{ticker} belum pernah digrade -- jalankan grade dulu"}), 404
    return jsonify({"ok": True})


@app.get("/api/grader_log")
def grader_log_list():
    with get_connection() as conn:
        rows = writes.list_grader_log(
            conn, instrument=request.args.get("instrument"),
            limit=request.args.get("limit", 200, type=int),
        )
    return jsonify(rows)


@app.post("/api/grader_log/<int:log_id>/outcome")
def grader_log_outcome(log_id):
    body = request.get_json(force=True)
    with get_connection() as conn:
        ok = writes.save_grader_outcome(
            conn, log_id, outcome_3m=body.get("outcome_3m"), outcome_6m=body.get("outcome_6m"),
            notes=body.get("notes"),
        )
        conn.commit()
    return jsonify({"ok": ok})


# ---------- PHASE J+: Lane validation (bar-replay sign-off, §13.1 poin 5).
# Satu-satunya jalur yang boleh mengubah lane / mengisi lane_validated_at --
# lihat guard di web.writes.validate_lane, TIDAK PERNAH otomatis. ----------

@app.post("/api/emiten/<ticker>/validate_lane")
def emiten_validate_lane(ticker):
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            result = writes.validate_lane(
                conn, instrument=ticker, new_lane=body.get("new_lane", ""),
                evidence=body.get("evidence", ""),
            )
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if result is None:
        return jsonify({"error": f"{ticker} tidak ada di instrument_metadata -- jalankan intake dulu"}), 404
    return jsonify(result)


@app.get("/api/lane_validation_log")
def lane_validation_log_list():
    with get_connection() as conn:
        rows = writes.list_lane_validation_log(
            conn, instrument=request.args.get("instrument"),
            limit=request.args.get("limit", 200, type=int),
        )
    return jsonify(rows)


# ---------- News Threads (Addendum B §20, N-1 fondasi). Auto-suggest jalan
# di pipeline/run_daily.py (writes.suggest_thread_links) -- endpoint di sini
# murni baca + konfirmasi/tolak/patch, tidak ada logic matching di route. ----------

@app.get("/api/threads")
def threads_list():
    with get_connection() as conn:
        rows = writes.list_threads(conn, status=request.args.get("status"))
    return jsonify(rows)


@app.get("/api/threads/<int:thread_id>")
def thread_detail(thread_id):
    with get_connection() as conn:
        thread = writes.get_thread(conn, thread_id)
        if thread is None:
            return jsonify({"error": "thread tidak ditemukan"}), 404
        thread["links"] = writes.list_thread_links(conn, thread_id)
    return jsonify(thread)


@app.post("/api/threads")
def thread_create():
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            row = writes.save_thread(
                conn, title=body.get("title", ""), description=body.get("description"),
                keywords=body.get("keywords"), persona_tags=body.get("persona_tags"),
                current_read=body.get("current_read"),
            )
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(row)


@app.post("/api/threads/<int:thread_id>")
def thread_patch(thread_id):
    # Pola konvensi app ini: SEMUA mutasi lewat POST (bukan PATCH/PUT --
    # lihat POST /api/emiten/<ticker>/override, /api/grader_log/<id>/outcome,
    # dll), meski secara REST-purist ini "update", bukan "create".
    body = request.get_json(force=True)
    fields = {k: v for k, v in body.items() if k in {"title", "current_read", "status", "keywords", "persona_tags", "verdict"}}
    try:
        with get_connection() as conn:
            row = writes.patch_thread(conn, thread_id, **fields)
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if row is None:
        return jsonify({"error": "thread tidak ditemukan"}), 404
    return jsonify(row)


@app.post("/api/threads/<int:thread_id>/links")
def thread_link_add_manual(thread_id):
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            row = writes.add_thread_link_manual(
                conn, thread_id, body.get("ref_table", ""), body.get("ref_id"),
                body.get("stance", ""), note=body.get("note"),
            )
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(row)


@app.post("/api/threads/link/<int:link_id>/confirm")
def thread_link_confirm(link_id):
    body = request.get_json(force=True)
    try:
        with get_connection() as conn:
            ok = writes.confirm_thread_link(
                conn, link_id, body.get("stance", ""),
                also_for_reading=bool(body.get("also_for_reading")),
            )
            conn.commit()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not ok:
        return jsonify({"error": "link tidak ditemukan"}), 404
    return jsonify({"ok": True})


@app.post("/api/threads/link/<int:link_id>/reject")
def thread_link_reject(link_id):
    with get_connection() as conn:
        ok = writes.reject_thread_link(conn, link_id)
        conn.commit()
    if not ok:
        return jsonify({"error": "link tidak ditemukan"}), 404
    return jsonify({"ok": True})


# ---------- SPA (Vue, web/frontend/dist/) — HARUS route PALING TERAKHIR
# didaftarkan (bukan krn urutan penting utk Flask/werkzeug -- literal segment
# spt /api/health selalu menang lawan <path:path> apa pun urutannya -- tapi
# supaya jelas dibaca ini catch-all). Kalau dist/ belum di-build, kasih
# pesan jelas (bukan traceback 500 yang membingungkan). ----------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    if not (FRONTEND_DIST / "index.html").exists():
        return (
            "Frontend belum di-build. Jalankan: cd web/frontend && npm run build",
            503,
        )
    if path and (FRONTEND_DIST / path).is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, "index.html")


def main() -> None:
    init_db()  # pastikan tabel ada (walau kosong) supaya API tidak error
    if not DASHBOARD_PASSWORD:
        print("[web] PERINGATAN: DASHBOARD_PASSWORD kosong -- login tidak akan bisa dipakai. Isi di .env.")
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "5000"))
    print(f"[web] Kastara dashboard -> http://{host}:{port}  (db={get_db_path()})")
    app.run(host=host, port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
