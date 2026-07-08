-- Kastara Finance — Phase A schema (11 tabel)
-- Yang WAJIB diisi scraper Phase A: daily_market, asset_ohlcv, daily_news.
-- Sisanya dibuat strukturnya saja (dipakai Phase B+).

-- 1. Konteks makro global (1 row per tanggal)
CREATE TABLE IF NOT EXISTS daily_market (
    date TEXT PRIMARY KEY,
    btc_open REAL, btc_high REAL, btc_low REAL, btc_close REAL,
    btc_volume REAL, btc_volume_ma20 REAL,
    btc_dominance REAL, btc_funding_rate REAL, btc_oi REAL,
    dxy_close REAL, dxy_change_pct REAL,
    sp500_close REAL, sp500_change_pct REAL,
    us10y_yield REAL, us10y_change_bps REAL,
    vix_close REAL,
    usd_jpy REAL,
    walcl REAL, rrp REAL, tga REAL, net_liquidity REAL,
    fear_greed_value INTEGER, fear_greed_label TEXT,
    ihsg_close REAL, ihsg_change_pct REAL,
    usd_idr REAL,
    gold_close REAL,
    btc_long_short_ratio REAL, btc_liquidation_24h REAL,
    stablecoin_supply REAL, hy_credit_spread REAL, bi_fed_spread REAL,
    created_at TEXT,
    source_flags TEXT  -- JSON string: {"coingecko":"ok","fred":"fail",...}
);

-- 2. Harga universal semua aset (1 row per aset per tanggal)
CREATE TABLE IF NOT EXISTS asset_ohlcv (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    instrument TEXT,
    open REAL, high REAL, low REAL, close REAL,
    volume REAL, volume_ma20 REAL,
    created_at TEXT,
    UNIQUE(date, instrument)
);

-- 3. News (rule-based scoring, BUKAN AI)
CREATE TABLE IF NOT EXISTS daily_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    source TEXT,
    headline TEXT,
    raw_url TEXT,
    impact_level TEXT,        -- HIGH/MED/LOW
    is_key_trigger INTEGER DEFAULT 0,
    created_at TEXT
);

-- 4. Economic calendar (event MASA DEPAN)
CREATE TABLE IF NOT EXISTS econ_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date TEXT, event_time TEXT, event_name TEXT,
    country TEXT, importance TEXT,
    forecast TEXT, previous TEXT, actual TEXT,
    is_watched INTEGER DEFAULT 0,
    created_at TEXT
);

-- 5. Reading workspace (diisi manual oleh Giel, Phase C)
CREATE TABLE IF NOT EXISTS reading_workspace (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, lens TEXT, notes TEXT,
    external_ai_ref TEXT, verdict TEXT, created_at TEXT
);

-- 6. Trade signals (suggest dari engine, Phase B)
CREATE TABLE IF NOT EXISTS trade_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, instrument TEXT, signal_type TEXT,
    entry_price REAL, sl_price REAL, tp1_price REAL, tp2_price REAL,
    rr_ratio REAL, zone_lower REAL, zone_upper REAL,
    volume_confirmed INTEGER, is_valid INTEGER,
    approved INTEGER DEFAULT 0, notes TEXT, created_at TEXT
);

-- 7. S&R zones (semi-otomatis + validasi manual, Phase B)
CREATE TABLE IF NOT EXISTS sr_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT, zone_lower REAL, zone_upper REAL,
    touch_count INTEGER, zone_type TEXT,
    first_seen TEXT, last_touched TEXT,
    is_active INTEGER, validated INTEGER DEFAULT 0, notes TEXT
);

-- 8. Manual articles (input manual Giel)
CREATE TABLE IF NOT EXISTS manual_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, source TEXT, url TEXT, headline TEXT, full_text TEXT,
    personal_notes TEXT, tags TEXT, is_key_event INTEGER DEFAULT 0,
    created_at TEXT
);

-- 9. Trading journal (record final)
CREATE TABLE IF NOT EXISTS trading_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, instrument TEXT, setup_type TEXT,
    entry_price REAL, sl_price REAL, tp1_price REAL,
    outcome TEXT, personal_notes TEXT, lesson_learned TEXT, created_at TEXT
);

-- 10. Prediction log (jantung mesin prediksi)
CREATE TABLE IF NOT EXISTS prediction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_made TEXT, horizon TEXT, claim TEXT,
    confidence INTEGER, basis TEXT, target_date TEXT,
    outcome TEXT, was_actioned INTEGER, lesson TEXT, created_at TEXT
);

-- 11. Asset context weight (pembobotan driver per aset, Phase D)
CREATE TABLE IF NOT EXISTS asset_context_weight (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT, driver TEXT, weight TEXT, notes TEXT
);

-- 12-14. Forward-looking layer (Master Plan §4.2) — struktur saja,
-- diisi bertahap saat Phase D (Stage 1/2/3). Ditambahkan di Phase A supaya
-- schema lengkap sesuai checklist Master Plan §10 ("+ tabel forward layer").

-- 12. Expectations (Stage 1 — angka: CME FedWatch, Dot Plot, dll)
CREATE TABLE IF NOT EXISTS expectations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, metric TEXT, value REAL, horizon TEXT,
    source TEXT, created_at TEXT
);

-- 13. Positioning (Stage 2 — arah uang besar: COT, ETF flow, SBN flow)
CREATE TABLE IF NOT EXISTS positioning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, instrument TEXT, metric TEXT, value REAL,
    source TEXT, created_at TEXT
);

-- 14. Policy tracker (Stage 3 — retorika pembuat kebijakan, literal vs
-- inferensi WAJIB terpisah; lihat disiplin editorial di Master Plan §4.2)
CREATE TABLE IF NOT EXISTS policy_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, speaker TEXT, institution TEXT, source_url TEXT,
    literal_statement TEXT,   -- apa yang BENAR-BENAR dikatakan (testable)
    stance_score INTEGER,     -- skala arah, mis. -2 dovish s/d +2 hawkish
    inference TEXT,           -- pembacaan arah/intent (subjektif)
    inference_flag TEXT,      -- TESTABLE / SPEKULATIF
    drift_note TEXT,
    created_at TEXT
);

-- Index untuk performa query range-tanggal saat histori membesar (5 tahun+).

-- asset_ohlcv: query utama selalu "WHERE instrument = ? ORDER BY date" (chart,
-- volume_ma20, backfill dedup-check). UNIQUE(date, instrument) di atas
-- kolomnya urutan (date, instrument) sehingga kurang optimal untuk pola ini;
-- index terpisah (instrument, date) mengisi celah itu.
CREATE INDEX IF NOT EXISTS idx_asset_ohlcv_instrument_date
    ON asset_ohlcv(instrument, date);

-- daily_news: (date, headline) dipakai untuk dedup saat insert. Dibuat UNIQUE
-- supaya dedup terjamin di level DB (bukan cuma cek SELECT dulu di app code),
-- sekaligus jadi index untuk query by date/date-range.
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_news_dedup
    ON daily_news(date, headline);

-- Filter by impact_level dipakai dashboard (/api/news?impact=HIGH), selalu
-- diikuti "ORDER BY date DESC" -> index composite biar filter+sort satu pass,
-- gak perlu temp b-tree buat sort.
DROP INDEX IF EXISTS idx_daily_news_impact;  -- superseded by versi composite di bawah
CREATE INDEX IF NOT EXISTS idx_daily_news_impact_date
    ON daily_news(impact_level, date DESC);

-- econ_calendar: sumber (ForexFactory) me-refresh event yang sama tiap kali
-- di-scrape (rolling window "minggu ini"); (event_date, event_name, country)
-- dipakai sebagai natural key untuk UPSERT — forecast bisa berubah mendekati
-- rilis, event yang sama harus ter-update, bukan duplikat baris.
CREATE UNIQUE INDEX IF NOT EXISTS idx_econ_calendar_dedup
    ON econ_calendar(event_date, event_name, country);

-- Phase B (plan_b.txt): sr_zones di-lookup by (instrument, zone_type) saat
-- cari zona existing untuk UPSERT (natural key = bucket relatif, dihitung
-- di Python dari zone_lower/zone_upper — lihat analysis/sr_zones.py
-- zone_bucket_key() — bukan kolom tersimpan, jadi index di sini cuma
-- mempercepat filter awal, bukan constraint UNIQUE).
CREATE INDEX IF NOT EXISTS idx_sr_zones_instrument_type
    ON sr_zones(instrument, zone_type);

-- trade_signals: append-only per event (plan_b.txt §5 — tidak perlu UNIQUE,
-- dedup dicek di pipeline/run_analysis.py sebelum INSERT). Index buat query
-- dashboard/CLI review by instrument+tanggal.
CREATE INDEX IF NOT EXISTS idx_trade_signals_instrument_date
    ON trade_signals(instrument, date DESC);
