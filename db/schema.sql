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
    btc_oi_aggregate REAL, btc_liq_long_24h REAL, btc_liq_short_24h REAL,
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
-- Ekstensi Phase J+ (Build Contract v1.3 §3): planned_size/actual_size (audit
-- selisih kuantisasi lot), skip_reason (RR_BELOW_MIN/RISK_CAPACITY_EXCEEDED/dll),
-- return_asset_ccy/return_idr (P&L ganda utk aset USD, eksposur kurs).
CREATE TABLE IF NOT EXISTS trading_journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, instrument TEXT, setup_type TEXT,
    entry_price REAL, sl_price REAL, tp1_price REAL,
    outcome TEXT, personal_notes TEXT, lesson_learned TEXT, created_at TEXT,
    planned_size REAL, actual_size REAL, skip_reason TEXT,
    return_asset_ccy REAL, return_idr REAL
);

-- 10. Prediction log (jantung mesin prediksi)
CREATE TABLE IF NOT EXISTS prediction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_made TEXT, horizon TEXT, claim TEXT,
    confidence INTEGER, basis TEXT, target_date TEXT,
    outcome TEXT, was_actioned INTEGER, lesson TEXT, created_at TEXT
);

-- 11. Asset context weight (pembobotan driver per aset, Phase D)
-- Ekstensi Phase J+ (Build Contract v1.3 §3): level menandai di tingkat apa
-- row ini berlaku (INDEX/SECTOR/INSTRUMENT) -- lookup cek instrument dulu,
-- jatuh ke sector, jatuh ke index kalau tidak ketemu (pewarisan bobot).
CREATE TABLE IF NOT EXISTS asset_context_weight (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT, driver TEXT, weight TEXT, notes TEXT,
    level TEXT DEFAULT 'INSTRUMENT'   -- INDEX / SECTOR / INSTRUMENT
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
-- Ekstensi Phase J+ (Build Contract v1.3 §3): sector_tags (JSON list, mis.
-- '["bank"]' utk OJK, '["tambang"]' utk Minerba -- dipakai LEON slice utk
-- filter statement yang relevan ke sektor emiten yang lagi dianalisa).
CREATE TABLE IF NOT EXISTS policy_tracker (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, speaker TEXT, institution TEXT, source_url TEXT,
    literal_statement TEXT,   -- apa yang BENAR-BENAR dikatakan (testable)
    stance_score INTEGER,     -- skala arah, mis. -2 dovish s/d +2 hawkish
    inference TEXT,           -- pembacaan arah/intent (subjektif)
    inference_flag TEXT,      -- TESTABLE / SPEKULATIF
    drift_note TEXT,
    sector_tags TEXT,         -- JSON list, mis. '["bank"]', '["tambang"]'
    created_at TEXT
);

-- 15. Instrument metadata (Phase J+ Build Contract v1.3 §3) -- 1 row per
-- instrumen ekuitas/index/fx/commodity yang di-track di luar BTC/makro inti.
-- lane menentukan apakah trade_signals di-generate (TRADE/BOTH) atau tidak
-- (INVEST/NONE) -- lihat Section 13.1 poin 5: instrumen baru masuk
-- INVEST/NONE dulu, naik ke TRADE cuma setelah validasi bar-replay
-- (lane_validated_at terisi).
CREATE TABLE IF NOT EXISTS instrument_metadata (
    instrument TEXT PRIMARY KEY,
    market TEXT,              -- IDX / US / CRYPTO / FX / COMMODITY
    asset_class TEXT,         -- equity / index / crypto / fx / commodity
    sector TEXT,              -- IDX-IC / GICS / NA
    market_cap REAL,
    free_float REAL,
    avg_volume_20d REAL,
    lot_size INTEGER,         -- IDX=100, US=1 (IBKR fractional -> 0), crypto=0
    lane TEXT,                -- TRADE / INVEST / BOTH / NONE (Gerbang G1)
    lane_validated_at TEXT,   -- tanggal validasi bar-replay sebelum naik ke TRADE
    accounting_std TEXT,      -- PSAK / US_GAAP / NA
    is_financial INTEGER DEFAULT 0,   -- true -> playbook CAR/NPL/NIM/LDR (RIVAN)
    fx_exposure TEXT,         -- eksportir / domestik / global
    has_daily_limit INTEGER DEFAULT 0,   -- true utk IDX (ARA/ARB) -- sizing buffer
    has_real_volume INTEGER DEFAULT 1,   -- false utk FX/Gold spot -- proxy range/ATR
    data_as_of_rule TEXT,
    created_at TEXT
);

-- 16. Fundamentals quarterly (Phase J+ §2 J3/J4) -- 1 row per instrumen per
-- kuartal. `confidence` = LOW_CONFIDENCE kalau histori yang tersedia < 8
-- kuartal target (lihat riset G3: yfinance .JK baru kasih ~4-5 kuartal utk
-- BBCA/BBRI/TLKM, bukan 8) -- grade tetap jalan, cuma diberi tahu tidak
-- ditolak (kontrak §16). Field draft -- BELUM final, dokumen v1.1 asli
-- (yang jadi rujukan "tidak berubah" di kontrak v1.3) tidak tersedia saat
-- draft ini ditulis; koreksi kalau meleset dari spesifikasi asli Giel.
CREATE TABLE IF NOT EXISTS fundamentals_quarterly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT, quarter_end TEXT,
    revenue REAL, net_income REAL, eps REAL,
    net_interest_income REAL,   -- khusus bank (is_financial), NULL utk non-bank
    total_equity REAL, total_assets REAL,
    operating_cash_flow REAL, free_cash_flow REAL,
    -- Rasio prudential bank (Phase J+ §2 J7/J-6) -- khusus is_financial=1,
    -- NULL utk non-bank. yfinance TIDAK PUNYA field ini (dikonfirmasi saat
    -- prototipe G3) -- MANUAL SAJA, dibaca Giel dari laporan resmi bank
    -- (OJK/laporan tahunan), tidak pernah disentuh upsert otomatis
    -- backfill_fundamentals.py (lihat guard di web/writes.py::save_bank_
    -- ratios_manual -- fungsi TERPISAH dari upsert_fundamentals_quarterly).
    car REAL,          -- Capital Adequacy Ratio (%)
    npl_gross REAL,    -- Non-Performing Loan gross (%)
    nim REAL,          -- Net Interest Margin (%)
    ldr REAL,          -- Loan to Deposit Ratio (%)
    source TEXT,                -- yfinance / manual upload / dll
    confidence TEXT DEFAULT 'FULL',   -- FULL / LOW_CONFIDENCE
    created_at TEXT,
    UNIQUE(instrument, quarter_end)
);

-- 17. Earnings & corporate action calendar (Phase J+ §2 J5) -- dipakai
-- AKELA (logika surprise forecast-vs-actual) dan rule SOP "no hold through
-- earnings" saham AS (kontrak §18 keputusan #3, earnings_calendar =
-- penegak aturan). Draft, sama seperti fundamentals_quarterly.
CREATE TABLE IF NOT EXISTS earnings_calendar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT, earnings_date TEXT,
    eps_forecast REAL, eps_actual REAL,   -- actual NULL sampai rilis
    event_type TEXT,   -- EARNINGS / CORPORATE_ACTION
    notes TEXT, created_at TEXT
);

-- 18. Sector benchmark (Phase J+ §2 J6) -- dihitung dari fundamentals_quarterly
-- per sektor per kuartal, dipakai RIVAN slice (playbook bank & pembanding
-- sektor). Draft, sama seperti di atas.
CREATE TABLE IF NOT EXISTS sector_benchmark (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector TEXT, quarter_end TEXT,
    avg_net_margin REAL, avg_pe REAL, median_revenue_growth REAL,
    created_at TEXT,
    UNIQUE(sector, quarter_end)
);

-- 19. Emiten grade (Phase J+ §16 Modul Grader) -- hasil rubrik dua sumbu
-- (fund_score vs integrity flags) + kuadran, per emiten per tanggal grading.
-- Draft, sama seperti di atas.
CREATE TABLE IF NOT EXISTS emiten_grade (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT, graded_at TEXT,
    fund_score REAL,
    integrity_flags TEXT,   -- JSON list, mis. '["UMA_ACTIVE"]'
    quadrant TEXT,
    -- Addendum A §19.2 Komponen B -- override manual Giel atas kuadran
    -- mesin. JSON: {"quadrant","reason","overridden_at"}. Kuadran mesin
    -- ASLI di kolom `quadrant` TIDAK ditimpa -- keduanya tampil bareng
    -- di UI ("(override Giel)"), bukan salah satu hilang.
    giel_override TEXT,
    notes TEXT, created_at TEXT
);

-- 20. Grader log (Phase J+ §16) -- audit trail perubahan grade dari waktu ke
-- waktu (anti-overtuning, review berkala per kontrak §17 J-11e). Draft,
-- sama seperti di atas.
CREATE TABLE IF NOT EXISTS grader_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT, date TEXT,
    old_grade TEXT, new_grade TEXT, reason TEXT,
    -- Addendum A §19.4 Komponen D -- widget "Nilai Outcome" 3/6 bulan
    -- setelah grade (pola sama prediction_log skor BENAR/SALAH/PARTIAL).
    outcome_3m TEXT, outcome_6m TEXT, outcome_notes TEXT,
    created_at TEXT
);

-- 21. Intake log (Phase J+ Build Contract v1.3 §19.3 Komponen C Gelombang 2,
-- J-12) -- padanan prediction_log utk keputusan intake kandidat: kandidat di
-- luar universe diuji pakai rubrik SAMA (tidak ada jalur istimewa, kontrak
-- §16), keputusan Giel (universe/watchlist/tolak) TERCATAT + alasan WAJIB
-- (reason NOT NULL) -- bisa diaudit nanti, bukan hilang begitu saja.
CREATE TABLE IF NOT EXISTS intake_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT,
    decided_at TEXT,
    decision TEXT,          -- UNIVERSE / WATCHLIST / TOLAK
    reason TEXT NOT NULL,
    grade_snapshot TEXT,     -- JSON: {fund_score, integrity_flags, quadrant} saat keputusan diambil
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

-- positioning (Phase D, plan_d.txt): COT/ETF-flow di-refresh tiap run (nilai
-- COT bisa direvisi, ETF flow bisa dikoreksi manual) -> (date, instrument,
-- metric) sebagai natural key UPSERT, sama pola dengan idx_econ_calendar_dedup.
CREATE UNIQUE INDEX IF NOT EXISTS idx_positioning_dedup
    ON positioning(date, instrument, metric);

-- earnings_calendar (Phase J+ Build Contract v1.3, J-7): eps_actual berubah
-- dari NULL -> terisi begitu earnings resmi rilis (kolom estimate juga bisa
-- direvisi analis sebelum tanggalnya) -> (instrument, earnings_date,
-- event_type) natural key UPSERT, sama pola dgn idx_econ_calendar_dedup.
CREATE UNIQUE INDEX IF NOT EXISTS idx_earnings_calendar_dedup
    ON earnings_calendar(instrument, earnings_date, event_type);
