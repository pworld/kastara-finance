"""Orchestrator harian: panggil semua scraper, tulis ke DB (idempotent).

Jalankan:
    python -m pipeline.run_daily              # tanggal hari ini (WIB)
    python -m pipeline.run_daily 2026-06-24   # tanggal tertentu

Idempotent: pakai UPSERT (ON CONFLICT). Run 2x untuk tanggal sama = update,
bukan duplikat row.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from typing import Any

from db.connection import get_connection, init_db
from indicators.calc import net_liquidity, volume_ma20_for_instrument
from scrapers.base import SourceFlags, created_at, today_wib
from scrapers.coinalyze import fetch_coinalyze
from scrapers.crypto import fetch_btc
from scrapers.econ_calendar import fetch_econ_calendar
from scrapers.equity_universe import fetch_equity_universe
from scrapers.idx_foreign_flow import fetch_idx_foreign_flow
from scrapers.idx_stock_foreign_flow import fetch_idx_stock_foreign_flow
from scrapers.macro_fred import fetch_macro_fred
from scrapers.macro_yf import fetch_macro_yf
from scrapers.news import fetch_all_news
from web.writes import (
    STALE_THREAD_DAYS,
    auto_dormant_stale_threads,
    suggest_tags_for_news,
    suggest_thread_links,
)
from scrapers.positioning import fetch_positioning

# Kolom daily_market yang boleh ditulis pipeline (sisanya untuk Phase B+).
DAILY_MARKET_COLS = [
    "btc_open", "btc_high", "btc_low", "btc_close", "btc_volume",
    "btc_volume_ma20", "btc_dominance", "btc_funding_rate", "btc_oi",
    "dxy_close", "dxy_change_pct", "sp500_close", "sp500_change_pct",
    "us10y_yield", "us10y_change_bps", "vix_close", "usd_jpy",
    "walcl", "rrp", "tga", "net_liquidity",
    "fear_greed_value", "fear_greed_label",
    "ihsg_close", "ihsg_change_pct", "usd_idr", "gold_close",
    "hy_credit_spread",
    "btc_oi_aggregate", "btc_long_short_ratio", "btc_liq_long_24h", "btc_liq_short_24h",
]


# ---------- WRITE HELPERS (dipakai run_daily + backfill) ----------

def upsert_daily_market(conn: sqlite3.Connection, date: str, fields: dict[str, Any]) -> None:
    """UPSERT 1 row daily_market by date. Hanya set kolom yang ada di `fields`.

    Pakai ON CONFLICT(date) DO UPDATE supaya kolom dari scraper lain tidak ketimpa.
    """
    cols = [c for c in fields if c in DAILY_MARKET_COLS]
    cols += ["source_flags", "created_at"]
    values = [fields.get(c) for c in cols]
    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols)
    conn.execute(
        f"INSERT INTO daily_market (date, {col_list}) VALUES (?, {placeholders}) "
        f"ON CONFLICT(date) DO UPDATE SET {updates}",
        [date, *values],
    )


def upsert_asset_ohlcv(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    """UPSERT 1 row asset_ohlcv by (date, instrument)."""
    conn.execute(
        "INSERT INTO asset_ohlcv "
        "(date, instrument, open, high, low, close, volume, volume_ma20, created_at) "
        "VALUES (:date, :instrument, :open, :high, :low, :close, :volume, "
        ":volume_ma20, :created_at) "
        "ON CONFLICT(date, instrument) DO UPDATE SET "
        "open=excluded.open, high=excluded.high, low=excluded.low, "
        "close=excluded.close, volume=excluded.volume, "
        "volume_ma20=excluded.volume_ma20",
        {
            "date": row["date"], "instrument": row["instrument"],
            "open": row.get("open"), "high": row.get("high"),
            "low": row.get("low"), "close": row.get("close"),
            "volume": row.get("volume"), "volume_ma20": row.get("volume_ma20"),
            "created_at": row.get("created_at") or created_at(),
        },
    )


def upsert_econ_calendar(conn: sqlite3.Connection, items: list[dict[str, Any]]) -> int:
    """UPSERT event ke econ_calendar by (event_date, event_name, country).

    Natural key ini (bukan id) ditegakkan oleh UNIQUE INDEX
    idx_econ_calendar_dedup (db/schema.sql) -> event yang sama di-refresh
    (forecast bisa berubah mendekati rilis), bukan duplikat baris.

    Pakai INSERT OR IGNORE + UPDATE terpisah (bukan "ON CONFLICT DO UPDATE"
    satu statement) karena rowcount SQLite untuk ON CONFLICT DO UPDATE selalu
    1 baik jalur insert maupun update -> tidak bisa dipakai membedakan
    "baris baru" vs "baris di-refresh" untuk ringkasan run.
    """
    inserted = 0
    for it in items:
        params = {**it, "created_at": created_at()}
        cur = conn.execute(
            "INSERT OR IGNORE INTO econ_calendar "
            "(event_date, event_time, event_name, country, importance, "
            "forecast, previous, actual, is_watched, created_at) "
            "VALUES (:event_date, :event_time, :event_name, :country, "
            ":importance, :forecast, :previous, :actual, 0, :created_at)",
            params,
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            conn.execute(
                "UPDATE econ_calendar SET event_time=:event_time, "
                "importance=:importance, forecast=:forecast, previous=:previous "
                "WHERE event_date=:event_date AND event_name=:event_name "
                "AND country=:country",
                params,
            )
    return inserted


def upsert_positioning(conn: sqlite3.Connection, items: list[dict[str, Any]]) -> int:
    """UPSERT row ke positioning by (date, instrument, metric).

    Natural key ditegakkan oleh UNIQUE INDEX idx_positioning_dedup
    (db/schema.sql) -> COT yang direvisi atau ETF flow yang dikoreksi
    ter-update, bukan duplikat baris. Pola sama dengan upsert_econ_calendar.
    """
    inserted = 0
    for it in items:
        params = {**it, "created_at": created_at()}
        cur = conn.execute(
            "INSERT OR IGNORE INTO positioning "
            "(date, instrument, metric, value, source, created_at) "
            "VALUES (:date, :instrument, :metric, :value, :source, :created_at)",
            params,
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            conn.execute(
                "UPDATE positioning SET value=:value, source=:source "
                "WHERE date=:date AND instrument=:instrument AND metric=:metric",
                params,
            )
    return inserted


def insert_news_dedup(conn: sqlite3.Connection, items: list[dict[str, Any]]) -> int:
    """INSERT news, skip kalau (date, headline) sudah ada. Return jumlah baru.

    Dedup ditegakkan oleh UNIQUE INDEX idx_daily_news_dedup(date, headline)
    (db/schema.sql) -> pakai INSERT OR IGNORE (1 statement), bukan SELECT
    dulu baru INSERT (2 round-trip/headline). Penting begitu volume tahunan
    ratusan ribu baris.
    """
    inserted = 0
    for it in items:
        cur = conn.execute(
            # Addendum C §21.2: for_reading gantikan is_key_trigger secara
            # fungsional -- baris baru cuma set for_reading=0 (is_key_trigger
            # beku sejak migrasi, biarkan DEFAULT 0 bawaan schema, jangan
            # di-set lagi di sini). Addendum D §22.3 (D-1): rss_summary --
            # `.get` krn item dari sumber selain scrapers/news.py (mis.
            # pipeline/add_article.py) tidak selalu sertakan field ini.
            "INSERT OR IGNORE INTO daily_news "
            "(date, source, headline, raw_url, impact_level, rss_summary, for_reading, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
            (it["date"], it["source"], it["headline"], it["raw_url"],
             it["impact_level"], it.get("rss_summary"), created_at()),
        )
        inserted += cur.rowcount
    return inserted


# ---------- ORCHESTRATION ----------

def run_daily(date: str | None = None, db_path=None) -> dict[str, Any]:
    """Jalankan full pipeline untuk satu tanggal. Return ringkasan."""
    date = date or today_wib()
    init_db(db_path)

    print(f"[run_daily] target date (WIB) = {date}")

    crypto = fetch_btc(date)
    coinalyze = fetch_coinalyze(date)
    yf = fetch_macro_yf(date)
    fred = fetch_macro_fred(date)
    news_items, news_health = fetch_all_news(date)
    econ = fetch_econ_calendar()
    positioning = fetch_positioning()
    idx_flow = fetch_idx_foreign_flow(date)
    equity = fetch_equity_universe(date, db_path)

    # J-8: foreign flow per-saham -- HANYA utk instrumen market=IDX di
    # instrument_metadata (TSLA/US tidak relevan, endpoint ini murni IDX).
    with get_connection(db_path) as conn:
        idx_tickers = [
            r["instrument"] for r in
            conn.execute("SELECT instrument FROM instrument_metadata WHERE market = 'IDX'").fetchall()
        ]
    stock_flow = fetch_idx_stock_foreign_flow(idx_tickers)

    flags = SourceFlags()
    for part in (crypto, coinalyze, yf, fred, econ, positioning, idx_flow, equity, stock_flow):
        flags.merge(part.get("source_flags", {}))
    # health_report RSS digabung ke source_flags dgn prefix "rss_" (pola sama
    # dengan scraper lain) -- feed mati langsung kelihatan di log tiap run.
    flags.merge({f"rss_{name}": status for name, status in news_health.items()})

    # Gabungkan asset_ohlcv rows: BTC (dari crypto) + rows dari yfinance.
    asset_rows: list[dict[str, Any]] = []
    if crypto.get("btc_close") is not None:
        asset_rows.append({
            "instrument": "BTC", "date": crypto["date"],
            "open": crypto.get("btc_open"), "high": crypto.get("btc_high"),
            "low": crypto.get("btc_low"), "close": crypto.get("btc_close"),
            "volume": crypto.get("btc_volume"),
        })
    asset_rows.extend(yf.get("asset_rows", []))
    asset_rows.extend(equity.get("asset_rows", []))

    with get_connection(db_path) as conn:
        # 1) tulis asset_ohlcv dulu (supaya volume hari ini masuk MA20)
        for row in asset_rows:
            row.setdefault("created_at", created_at())
            upsert_asset_ohlcv(conn, row)

        # 2) hitung volume_ma20 per instrument, update kembali
        for row in asset_rows:
            ma20 = volume_ma20_for_instrument(row["instrument"], row["date"], db_path)
            if ma20 is not None:
                conn.execute(
                    "UPDATE asset_ohlcv SET volume_ma20 = ? "
                    "WHERE date = ? AND instrument = ?",
                    (ma20, row["date"], row["instrument"]),
                )

        # 3) susun daily_market merge crypto + coinalyze + yf + fred
        market: dict[str, Any] = {}
        for part in (crypto, coinalyze, yf, fred):
            for k, v in part.items():
                if k in DAILY_MARKET_COLS:
                    market[k] = v

        # calculated fields
        market["net_liquidity"] = net_liquidity(
            fred.get("walcl"), fred.get("rrp"), fred.get("tga")
        )
        market["btc_volume_ma20"] = volume_ma20_for_instrument("BTC", date, db_path)

        market["source_flags"] = json.dumps(flags.as_dict())
        market["created_at"] = created_at()
        upsert_daily_market(conn, date, market)

        # 4) news
        n_news = insert_news_dedup(conn, news_items)

        # 4a) Faceted Tagging auto-suggest (Addendum C §21.9, GELOMBANG C-2)
        # -- rule-based keyword->tag dari kamus, SELALU cuma SUGGESTED source
        # (human gate sama seperti thread links). Butuh row id asli
        # daily_news, jadi SETELAH insert_news_dedup. HARUS sebelum 4b, biar
        # tag-match §21.5 di suggest_thread_links lihat tag yang baru
        # disarankan di run yang sama (bukan nunggu run besok).
        n_tags_suggested = suggest_tags_for_news(conn, news_items)

        # 4b) News Threads N-1 auto-suggest (Addendum B §20.2, extended §21.5)
        # -- keyword match ke thread ACTIVE ATAU tag-overlap (thread facet
        # tags vs berita facet tags, dari 4a), SELALU cuma SUGGESTED (human
        # gate, tidak pernah auto-CONFIRMED).
        n_thread_links = suggest_thread_links(conn, news_items)

        # 4c) Auto-DORMANT thread ACTIVE yang stale (Addendum C §21.8 C-2) --
        # tidak menghapus, cuma turunkan status supaya tidak ikut hitungan
        # 7/ACTIVE & auto-suggest lagi sampai diaktifkan manual.
        n_auto_dormant = auto_dormant_stale_threads(conn)

        # 5) economic calendar (event masa depan, upsert by natural key)
        n_econ = upsert_econ_calendar(conn, econ.get("items", []))

        # 6) positioning (Phase D — COT + BTC ETF flow, upsert by natural key)
        #    + IHSG foreign flow (Track C, IDX) + foreign flow per-saham
        #    (J-8) -- item list yang sama, natural key (date,instrument,
        #    metric) dedupe otomatis.
        n_positioning = upsert_positioning(
            conn, positioning.get("items", []) + idx_flow.get("items", []) + stock_flow.get("items", [])
        )

        conn.commit()

    summary = {
        "date": date,
        "sources_ok": flags.count("ok"),
        "sources_fail": flags.count("fail"),
        "sources_skip": flags.count("skip"),
        "asset_rows": len(asset_rows),
        "news_inserted": n_news,
        "tags_suggested": n_tags_suggested,
        "thread_links_suggested": n_thread_links,
        "threads_auto_dormant": n_auto_dormant,
        "rss_ok": sum(1 for v in news_health.values() if v == "ok"),
        "rss_dead": [name for name, status in news_health.items() if status == "dead"],
        "econ_events_new": n_econ,
        "positioning_new": n_positioning,
        "source_flags": flags.as_dict(),
    }
    _print_summary(summary)
    return summary


def run_news_only(date: str | None = None, db_path=None) -> dict[str, Any]:
    """Subset `run_daily()` -- CUMA fetch+simpan berita (news+tags+thread-
    suggest+auto-dormant), TIDAK sentuh market/crypto/econ/positioning sama
    sekali. Dibangun 6 Agustus 2026 utk tombol "Get News" di `/m` (Giel
    minta trigger terpisah dari harga -- kadang cuma mau lihat berita
    terbaru tanpa nunggu semua scraper market ikut jalan). Transaksi
    SENDIRI (bukan bagian transaksi run_daily()) -- sengaja, supaya trigger
    scoped ini benar2 independen, tidak numpang commit pipeline penuh.
    Reuse helper yang SAMA PERSIS dgn run_daily() (insert_news_dedup dst) --
    bukan reimplementasi, murni subset urutan langkah."""
    date = date or today_wib()
    init_db(db_path)
    news_items, news_health = fetch_all_news(date)
    with get_connection(db_path) as conn:
        n_news = insert_news_dedup(conn, news_items)
        n_tags_suggested = suggest_tags_for_news(conn, news_items)
        n_thread_links = suggest_thread_links(conn, news_items)
        n_auto_dormant = auto_dormant_stale_threads(conn)
        conn.commit()
    return {
        "date": date,
        "news_inserted": n_news,
        "tags_suggested": n_tags_suggested,
        "thread_links_suggested": n_thread_links,
        "threads_auto_dormant": n_auto_dormant,
        "rss_ok": sum(1 for v in news_health.values() if v == "ok"),
        "rss_dead": [name for name, status in news_health.items() if status == "dead"],
    }


def run_price_only(date: str | None = None, db_path=None) -> dict[str, Any]:
    """Subset `run_daily()` -- CUMA fetch+simpan data market/harga (crypto,
    coinalyze, yfinance macro, FRED, equity universe, IDX flow, econ
    calendar, positioning), TIDAK sentuh berita/tags/thread sama sekali.
    Pasangan `run_news_only()` utk tombol "Get Price" di `/m`. Transaksi
    SENDIRI, sama alasan seperti run_news_only()."""
    date = date or today_wib()
    init_db(db_path)

    crypto = fetch_btc(date)
    coinalyze = fetch_coinalyze(date)
    yf = fetch_macro_yf(date)
    fred = fetch_macro_fred(date)
    econ = fetch_econ_calendar()
    positioning = fetch_positioning()
    idx_flow = fetch_idx_foreign_flow(date)
    equity = fetch_equity_universe(date, db_path)

    with get_connection(db_path) as conn:
        idx_tickers = [
            r["instrument"] for r in
            conn.execute("SELECT instrument FROM instrument_metadata WHERE market = 'IDX'").fetchall()
        ]
    stock_flow = fetch_idx_stock_foreign_flow(idx_tickers)

    flags = SourceFlags()
    for part in (crypto, coinalyze, yf, fred, econ, positioning, idx_flow, equity, stock_flow):
        flags.merge(part.get("source_flags", {}))

    asset_rows: list[dict[str, Any]] = []
    if crypto.get("btc_close") is not None:
        asset_rows.append({
            "instrument": "BTC", "date": crypto["date"],
            "open": crypto.get("btc_open"), "high": crypto.get("btc_high"),
            "low": crypto.get("btc_low"), "close": crypto.get("btc_close"),
            "volume": crypto.get("btc_volume"),
        })
    asset_rows.extend(yf.get("asset_rows", []))
    asset_rows.extend(equity.get("asset_rows", []))

    with get_connection(db_path) as conn:
        for row in asset_rows:
            row.setdefault("created_at", created_at())
            upsert_asset_ohlcv(conn, row)
        for row in asset_rows:
            ma20 = volume_ma20_for_instrument(row["instrument"], row["date"], db_path)
            if ma20 is not None:
                conn.execute(
                    "UPDATE asset_ohlcv SET volume_ma20 = ? WHERE date = ? AND instrument = ?",
                    (ma20, row["date"], row["instrument"]),
                )
        market: dict[str, Any] = {}
        for part in (crypto, coinalyze, yf, fred):
            for k, v in part.items():
                if k in DAILY_MARKET_COLS:
                    market[k] = v
        market["net_liquidity"] = net_liquidity(fred.get("walcl"), fred.get("rrp"), fred.get("tga"))
        market["btc_volume_ma20"] = volume_ma20_for_instrument("BTC", date, db_path)
        market["source_flags"] = json.dumps(flags.as_dict())
        market["created_at"] = created_at()
        upsert_daily_market(conn, date, market)
        n_econ = upsert_econ_calendar(conn, econ.get("items", []))
        n_positioning = upsert_positioning(
            conn, positioning.get("items", []) + idx_flow.get("items", []) + stock_flow.get("items", [])
        )
        conn.commit()

    return {
        "date": date,
        "sources_ok": flags.count("ok"),
        "sources_fail": flags.count("fail"),
        "sources_skip": flags.count("skip"),
        "asset_rows": len(asset_rows),
        "econ_events_new": n_econ,
        "positioning_new": n_positioning,
        "source_flags": flags.as_dict(),
    }


def _print_summary(s: dict[str, Any]) -> None:
    print("\n========== RINGKASAN RUN ==========")
    print(f"  date          : {s['date']}")
    print(f"  source ok     : {s['sources_ok']}")
    print(f"  source fail   : {s['sources_fail']}")
    print(f"  source skip   : {s['sources_skip']}")
    print(f"  asset rows    : {s['asset_rows']}")
    print(f"  news inserted : {s['news_inserted']}")
    print(f"  tags suggest  : {s['tags_suggested']} tag baru (Faceted Tagging C-2)")
    print(f"  thread suggest: {s['thread_links_suggested']} link baru (News Threads, keyword+tag-match)")
    print(f"  auto-dormant  : {s['threads_auto_dormant']} thread (stale >{STALE_THREAD_DAYS}d)")
    rss_line = f"  RSS           : {s['rss_ok']} ok, {len(s['rss_dead'])} dead"
    if s["rss_dead"]:
        rss_line += f" → {s['rss_dead']}"
    print(rss_line)
    print(f"  econ events   : {s['econ_events_new']} baru")
    print(f"  positioning   : {s['positioning_new']} baru")
    print("  flags:")
    for k, v in sorted(s["source_flags"].items()):
        mark = {"ok": "✓", "fail": "✗", "skip": "·"}.get(v, "?")
        print(f"    {mark} {k} = {v}")
    print("===================================\n")


if __name__ == "__main__":
    arg_date = sys.argv[1] if len(sys.argv) > 1 else None
    run_daily(arg_date)
