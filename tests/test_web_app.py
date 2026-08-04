"""Test web/app.py pure helpers (Panel 1 snapshot compare + data-gap detection)."""
import os
import tempfile

import pytest

# web/app.py sekarang panggil init_db() di level modul (bukan cuma di
# main(), lihat komentar di app.py -- perlu jalan juga di bawah gunicorn).
# Set KASTARA_DB_PATH ke file temp SEBELUM import `web.app` di bawah, supaya
# init_db() itu tidak diam-diam kena ke DB produksi asli (nilai KASTARA_DB_PATH
# dari .env lokal) hanya krn test file ini import modulnya -- pola sama
# disiplin keamanan DB produksi yang dipakai di seluruh proyek ini.
os.environ["KASTARA_DB_PATH"] = tempfile.mktemp(suffix=".db")

from db.connection import get_connection, init_db
from indicators.calc import COMPARE_PERIODS
from indicators.calc import compare_from_series as _compare_from_series
import web.app as web_app_mod
from web.app import INSTRUMENT_SOURCE, SNAPSHOT_FIELDS, _all_instruments_with_gaps, _detect_gaps


def test_compare_from_series_all_periods_available():
    # series DESC (baru->lama), 1 titik per hari mundur dari 2026-07-09
    series = [
        ("2026-07-09", 100.0),
        ("2026-07-08", 90.0),
        ("2026-07-02", 80.0),
        ("2026-06-09", 70.0),
        ("2025-07-09", 50.0),
    ]
    result = _compare_from_series(series, "2026-07-09", 100.0)
    assert result["day"]["past_value"] == 90.0
    assert result["day"]["delta"] == 10.0
    assert result["day"]["pct"] == pytest.approx(11.111, abs=0.01)
    assert result["week"]["past_value"] == 80.0
    assert result["month"]["past_value"] == 70.0
    assert result["year"]["past_value"] == 50.0
    assert result["year"]["delta"] == 50.0


def test_compare_from_series_missing_period_returns_none():
    # cuma ada data day (kemarin), tidak ada yang cukup jauh utk week/month/year
    series = [("2026-07-09", 100.0), ("2026-07-08", 90.0)]
    result = _compare_from_series(series, "2026-07-09", 100.0)
    assert result["day"] is not None
    assert result["week"] is None
    assert result["month"] is None
    assert result["year"] is None


def test_compare_from_series_no_current_value_returns_all_none():
    series = [("2026-07-08", 90.0)]
    result = _compare_from_series(series, "2026-07-09", None)
    assert all(v is None for v in result.values())


def test_compare_from_series_skips_null_values_in_series():
    # titik dgn value None (kolom kosong hari itu) dilewati, cari yang valid berikutnya
    series = [
        ("2026-07-09", 100.0),
        ("2026-07-08", None),
        ("2026-07-07", 88.0),
    ]
    result = _compare_from_series(series, "2026-07-09", 100.0)
    assert result["day"]["past_value"] == 88.0
    assert result["day"]["past_date"] == "2026-07-07"


def test_compare_periods_keys():
    assert set(COMPARE_PERIODS) == {"day", "week", "month", "year"}
    assert COMPARE_PERIODS["day"] == 1
    assert COMPARE_PERIODS["week"] == 7
    assert COMPARE_PERIODS["month"] == 30
    assert COMPARE_PERIODS["year"] == 365


# ---------- SNAPSHOT_FIELDS categories ----------

def test_snapshot_fields_all_have_category():
    for field in SNAPSHOT_FIELDS:
        assert field["category"] in {"Crypto (BTC)", "Makro Global", "Ekuitas & FX"}


# ---------- Data gap detection ----------

def test_detect_gaps_no_gap_daily():
    dates = ["2026-07-07", "2026-07-08", "2026-07-09"]
    assert _detect_gaps(dates, "DAILY") == []


def test_detect_gaps_weekly_wed_always_empty():
    # WALCL/TGA -- rilis mingguan, "kosong" antar-Rabu itu wajar, bukan gap
    dates = ["2026-06-24", "2026-07-01"]
    assert _detect_gaps(dates, "WEEKLY_WED") == []


def test_detect_gaps_single_missing_day_not_reported():
    # gap 1 hari (mis. libur biasa) sengaja TIDAK dilaporkan -- cuma noise
    dates = ["2026-07-06", "2026-07-08"]  # 07-07 kosong, cuma 1 hari
    assert _detect_gaps(dates, "DAILY") == []


def test_detect_gaps_daily_calendar_detects_multi_day_gap():
    dates = ["2026-07-01", "2026-07-02", "2026-07-06"]  # 03-05 kosong (3 hari)
    gaps = _detect_gaps(dates, "DAILY")
    assert gaps == [{"from": "2026-07-03", "to": "2026-07-05", "days": 3}]


def test_detect_gaps_weekday_calendar_ignores_weekends():
    # Jumat -> Senin (lompat weekend) TIDAK dianggap gap utk kalender WEEKDAY
    dates = ["2026-07-03", "2026-07-06"]  # Jum'at 07-03, Senin 07-06
    assert _detect_gaps(dates, "WEEKDAY") == []


def test_detect_gaps_weekday_calendar_detects_real_gap():
    # Senin 06-29 s.d Jumat 07-10, hilang Senin 07-06 s.d Jumat 07-10 (5 hari kerja)
    dates = ["2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-13"]
    gaps = _detect_gaps(dates, "WEEKDAY")
    assert gaps == [{"from": "2026-07-06", "to": "2026-07-10", "days": 5}]


def test_detect_gaps_empty_dates_returns_empty():
    assert _detect_gaps([], "DAILY") == []


def test_instrument_source_covers_all_backfill_instruments():
    expected = {"BTC", "SP500", "IHSG", "GOLD", "USDIDR", "USDJPY",
                "DXY", "US10Y", "VIX", "WALCL", "RRP", "TGA", "HY"}
    assert set(INSTRUMENT_SOURCE) == expected
    for source, col, calendar in INSTRUMENT_SOURCE.values():
        assert source in {"asset_ohlcv", "daily_market"}
        assert (col is None) == (source == "asset_ohlcv")
        assert calendar in {"DAILY", "WEEKDAY", "WEEKLY_WED"}


# ---------- _all_instruments_with_gaps (Panel 1 "Cek & Backfill Semua Gap") ----------

def _seed_asset_ohlcv(conn, instrument, dates):
    for d in dates:
        conn.execute(
            "INSERT INTO asset_ohlcv (date, instrument, open, high, low, close, volume, created_at) "
            "VALUES (?, ?, 1, 1, 1, 1, 1, '')", (d, instrument),
        )


def test_all_instruments_with_gaps_finds_macro_gap(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        # BTC pakai kalender DAILY -- gap 3 hari (07-03..07-05) jelas terdeteksi
        _seed_asset_ohlcv(conn, "BTC", ["2026-07-01", "2026-07-02", "2026-07-06"])
        conn.commit()
        results = _all_instruments_with_gaps(conn)
    btc = next((r for r in results if r["instrument"] == "BTC"), None)
    assert btc is not None
    assert btc["gap_from"] == "2026-07-03"
    assert btc["gap_to"] == "2026-07-05"
    assert btc["gaps_count"] == 1


def test_all_instruments_with_gaps_skips_instrument_without_any_data(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        results = _all_instruments_with_gaps(conn)
    # Tanpa histori sama sekali -- dilewati (backfill awal butuh keputusan
    # sadar, bukan "isi gap" otomatis).
    assert results == []


def test_all_instruments_with_gaps_skips_weekly_wed_calendar(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        conn.execute("INSERT INTO daily_market (date, walcl, created_at) VALUES ('2026-06-24', 1, '')")
        conn.execute("INSERT INTO daily_market (date, walcl, created_at) VALUES ('2026-07-08', 1, '')")
        conn.commit()
        results = _all_instruments_with_gaps(conn)
    assert not any(r["instrument"] == "WALCL" for r in results)


def test_all_instruments_with_gaps_includes_equity_universe(tmp_path):
    """Instrumen Phase J+ (instrument_metadata, mis. BBCA) ikut dicek dgn
    kalender WEEKDAY (bursa saham), sama seperti ekuitas macro existing."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        conn.execute(
            "INSERT INTO instrument_metadata (instrument, market, created_at) VALUES ('BBCA', 'IDX', '')"
        )
        # Senin-Jumat penuh, lalu Senin-Jumat berikutnya hilang total (5 hari kerja)
        _seed_asset_ohlcv(conn, "BBCA", [
            "2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-13",
        ])
        conn.commit()
        results = _all_instruments_with_gaps(conn)
    bbca = next((r for r in results if r["instrument"] == "BBCA"), None)
    assert bbca is not None
    assert bbca["gap_from"] == "2026-07-06"
    assert bbca["gap_to"] == "2026-07-10"


def test_all_instruments_with_gaps_no_gap_returns_empty(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _seed_asset_ohlcv(conn, "BTC", ["2026-07-07", "2026-07-08", "2026-07-09"])
        conn.commit()
        results = _all_instruments_with_gaps(conn)
    assert results == []


# ---------- Telegram bot 2-arah: /api/telegram/webhook (4 Agustus 2026) ----------
# Endpoint publik (Telegram yang panggil, exempt session auth) -- test fokus
# ke 2 gerbang keamanan (chat_id + secret token opsional) dan guard
# command-tunggal (`/run_daily`), BUKAN test run_daily() beneran (network,
# di-monkeypatch).

class _ImmediateThread:
    """Pengganti threading.Thread di test -- jalankan target() LANGSUNG
    (synchronous), bukan di thread beneran, supaya efeknya bisa langsung
    di-assert tanpa race/sleep."""
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


def test_telegram_webhook_ignores_unknown_chat_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    calls = []
    monkeypatch.setattr(web_app_mod, "run_daily_mod", type("M", (), {"run_daily": lambda: calls.append("ran")})())
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 999}, "text": "/run_daily"}})
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert calls == []


def test_telegram_webhook_ignores_unknown_command(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    calls = []
    monkeypatch.setattr(web_app_mod, "run_daily_mod", type("M", (), {"run_daily": lambda: calls.append("ran")})())
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/halo"}})
    assert resp.status_code == 200
    assert calls == []


def test_telegram_webhook_triggers_run_daily_for_allowed_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(web_app_mod, "threading", type("T", (), {"Thread": _ImmediateThread})())
    fake_summary = {"news_inserted": 5, "sources_ok": 8, "sources_fail": 0, "sources_skip": 1}
    monkeypatch.setattr(
        web_app_mod, "run_daily_mod", type("M", (), {"run_daily": staticmethod(lambda: fake_summary)})()
    )
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/run_daily"}})
    assert resp.status_code == 200
    # _ImmediateThread jalankan target() SYNCHRONOUS saat .start() dipanggil --
    # jadi pesan ringkasan (dikirim di dalam target) terkirim SEBELUM pesan ack
    # (dikirim setelah .start() return di handler) -- beda dari urutan runtime
    # asli (thread beneran, ack duluan). Cuma pastikan KEDUANYA terkirim & isinya benar.
    assert len(sent) == 2
    texts = [t for t, _ in sent]
    assert any("5 berita baru" in t for t in texts)
    assert any("Menjalankan pipeline harian" in t for t in texts)
    assert all(chat_id == 111 for _, chat_id in sent)


def test_telegram_webhook_requires_secret_token_when_configured(monkeypatch):
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "rahasia123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    client = web_app_mod.app.test_client()
    wrong = client.post(
        "/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/run_daily"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "salah"},
    )
    assert wrong.status_code == 403
    missing = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/run_daily"}})
    assert missing.status_code == 403
