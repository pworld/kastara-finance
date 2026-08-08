"""Test web/app.py pure helpers (Panel 1 snapshot compare + data-gap detection)."""
import json
import os
import tempfile
from datetime import timedelta

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


# ---------- Telegram bot 2-arah: /api/telegram/webhook ----------
# Dibangun 4 Agustus 2026, diperluas 5-6 Agustus 2026 per spec Giel
# "Telegram Bot Commands v1.0" (allowlist multi chat_id, /status kaya
# per-tabel, lock anti-double-run + rate limit /run_daily) -- TETAP webhook
# di Railway (bukan long-polling+systemd, lihat komentar app.py). Endpoint
# publik (Telegram yang panggil, exempt session auth) -- test fokus ke
# gerbang keamanan (allowlist + secret token opsional) dan guard 3-command,
# BUKAN test run_daily() beneran (network, di-monkeypatch). Tiap test yang
# menyentuh /run_daily WAJIB monkeypatch RUN_DAILY_LOCK_PATH/
# RUN_DAILY_LAST_TRIGGER_PATH ke tmp_path -- constant aslinya nunjuk ke
# tempdir asli, kalau tidak di-isolate test bisa saling bocor state lewat
# lock file yang sama.

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


def _isolate_run_daily_lock_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(web_app_mod, "RUN_DAILY_LOCK_PATH", str(tmp_path / "run_daily.lock"))
    monkeypatch.setattr(web_app_mod, "RUN_DAILY_LAST_TRIGGER_PATH", str(tmp_path / "run_daily_last_trigger.txt"))


def _seed_daily_market(date="2026-08-06", flags=None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO daily_market (date, created_at, source_flags) VALUES (?,?,?)",
            (date, web_app_mod.created_at(), json.dumps(flags or {"btc": "ok"})),
        )
        conn.commit()


def test_telegram_webhook_ignores_unknown_chat_id(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    _isolate_run_daily_lock_paths(monkeypatch, tmp_path)
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


def test_telegram_webhook_accepts_any_id_in_telegram_chat_ids_list(monkeypatch, tmp_path):
    # TELEGRAM_CHAT_IDS (jamak) -- allowlist beberapa chat_id sekaligus,
    # bukan cuma satu (§3.1 spec).
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "111, 222")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    r1 = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 222}, "text": "/start"}})
    r2 = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 333}, "text": "/start"}})
    assert r1.status_code == 200 and r2.status_code == 200
    assert len(sent) == 1
    assert sent[0][1] == 222


def test_telegram_webhook_triggers_run_daily_for_allowed_chat(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(web_app_mod, "threading", type("T", (), {"Thread": _ImmediateThread})())
    _isolate_run_daily_lock_paths(monkeypatch, tmp_path)

    def _fake_run_daily():
        _seed_daily_market()  # simulasi efek nyata run_daily() -- isi daily_market

    monkeypatch.setattr(web_app_mod, "run_daily_mod", type("M", (), {"run_daily": staticmethod(_fake_run_daily)})())
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/run_daily"}})
    assert resp.status_code == 200
    # _ImmediateThread jalankan target() SYNCHRONOUS saat .start() dipanggil --
    # jadi pesan hasil (dikirim di dalam target) terkirim SEBELUM pesan ack
    # (dikirim setelah .start() return di handler) -- beda dari urutan runtime
    # asli (thread beneran, ack duluan). Cuma pastikan KEDUANYA terkirim & isinya benar.
    assert len(sent) == 2
    texts = [t for t, _ in sent]
    assert any("run_daily dimulai" in t for t in texts)
    assert any("run_daily selesai" in t and "daily_market" in t for t in texts)
    assert all(chat_id == 111 for _, chat_id in sent)
    # lock WAJIB terlepas setelah selesai (finally di _run_daily_via_telegram).
    assert not os.path.exists(web_app_mod.RUN_DAILY_LOCK_PATH)


def test_telegram_webhook_run_daily_blocked_when_already_locked(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    _isolate_run_daily_lock_paths(monkeypatch, tmp_path)
    web_app_mod._acquire_run_daily_lock()  # simulasi run_daily lain SEDANG jalan
    calls = []
    monkeypatch.setattr(web_app_mod, "run_daily_mod", type("M", (), {"run_daily": lambda: calls.append("ran")})())
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/run_daily"}})
    assert resp.status_code == 200
    assert calls == []  # TIDAK jalan lagi krn masih terkunci
    assert len(sent) == 1
    assert "sedang berjalan sejak" in sent[0][0]


def test_telegram_webhook_run_daily_stale_lock_taken_over(monkeypatch, tmp_path):
    # Lock berumur > 30 menit dianggap stale (proses lama kemungkinan crash
    # tanpa sempat hapus lock) -- diambil alih, BUKAN mengunci selamanya.
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    monkeypatch.setattr(web_app_mod, "threading", type("T", (), {"Thread": _ImmediateThread})())
    _isolate_run_daily_lock_paths(monkeypatch, tmp_path)
    stale_time = web_app_mod.now_wib() - timedelta(minutes=45)
    with open(web_app_mod.RUN_DAILY_LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(f"99999|{stale_time.strftime('%Y-%m-%d %H:%M:%S%z')}")

    def _fake_run_daily():
        _seed_daily_market()

    monkeypatch.setattr(web_app_mod, "run_daily_mod", type("M", (), {"run_daily": staticmethod(_fake_run_daily)})())
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/run_daily"}})
    assert resp.status_code == 200
    texts = [t for t, _ in sent]
    assert any("run_daily dimulai" in t for t in texts)  # bukan "sedang berjalan"


def test_telegram_webhook_run_daily_rate_limited(monkeypatch, tmp_path):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    _isolate_run_daily_lock_paths(monkeypatch, tmp_path)
    with open(web_app_mod.RUN_DAILY_LAST_TRIGGER_PATH, "w", encoding="utf-8") as f:
        f.write(web_app_mod.created_at())  # trigger "baru saja"
    calls = []
    monkeypatch.setattr(web_app_mod, "run_daily_mod", type("M", (), {"run_daily": lambda: calls.append("ran")})())
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/run_daily"}})
    assert resp.status_code == 200
    assert calls == []
    assert len(sent) == 1
    assert "5 menit" in sent[0][0]


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


def test_telegram_webhook_start_sends_help_text(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/start"}})
    assert resp.status_code == 200
    assert len(sent) == 1
    assert "/run_daily" in sent[0][0]
    assert "/status" in sent[0][0]
    assert sent[0][1] == 111


def test_telegram_webhook_status_reports_last_run(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    with get_connection() as conn:
        # DB file di-share SATU utk seluruh test file ini (module-level
        # KASTARA_DB_PATH) -- bersihkan dulu supaya row daily_market dari
        # test lain (mis. seed /run_daily bertanggal hari ini) tidak
        # ngalahin MAX(date) row test ini.
        conn.execute("DELETE FROM daily_market")
        conn.commit()
        conn.execute(
            "INSERT INTO daily_market (date, created_at, source_flags) VALUES (?,?,?)",
            ("2026-08-05", web_app_mod.created_at(), json.dumps({"btc": "ok", "yf": "fail"})),
        )
        conn.execute(
            "INSERT INTO daily_news (date, source, headline, raw_url, impact_level) VALUES (?,?,?,?,?)",
            ("2026-08-05", "CNBC Indonesia", "Test headline", "https://x.test", "LOW"),
        )
        conn.commit()
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/status"}})
    assert resp.status_code == 200
    assert len(sent) == 1
    text, chat_id = sent[0]
    assert "1 ok" in text
    assert "1 fail" in text
    assert "1 berita" in text
    assert "daily_market" in text
    assert "asset_ohlcv" in text
    assert "econ_calendar" in text
    assert "Sinyal pending approve" in text
    assert chat_id == 111


def test_telegram_webhook_status_with_no_pipeline_data_yet(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(web_app_mod, "TELEGRAM_WEBHOOK_SECRET", "")
    with get_connection() as conn:
        conn.execute("DELETE FROM daily_market")
        conn.commit()
    sent = []
    monkeypatch.setattr(web_app_mod, "send_message", lambda text, chat_id=None: sent.append((text, chat_id)))
    client = web_app_mod.app.test_client()
    resp = client.post("/api/telegram/webhook", json={"message": {"chat": {"id": 111}, "text": "/status"}})
    assert resp.status_code == 200
    assert sent == [("Belum ada data pipeline sama sekali.", 111)]
