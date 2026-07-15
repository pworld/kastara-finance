# Kastara Finance — Data Layer + Analysis Engine + Dashboard + Equity Expansion

Personal finance/trading intelligence stack. **Mesin men-suggest, Giel
memutuskan** — tidak ada execution/trading logic otomatis di mana pun.

**Status per Juli 2026 (detail lengkap di [`docs/ROADMAP.md`](docs/ROADMAP.md)):**
- **Phase A** ✅ — kumpulkan data mentah makro/berita ke SQLite lokal (no paid API).
- **Phase B** ✅ — engine S&R + breakout/retest + R:R (BTC).
- **Phase C** ✅ — dashboard **write-enabled**, sekarang **8 panel/tab**.
- **Phase D** ✅ — forward layer (FedWatch/Dot Plot manual, COT + BTC ETF flow
  otomatis, Policy Tracker, Disonansi Flag).
- **Phase E** ✅ — Daily Briefing → Telegram (push satu arah, manual trigger).
- **Phase F+** ✅ — engine direplikasi ke GOLD/IHSG/SP500/USDIDR/USDJPY, +
  4 Analisa Persona (Panel 4, OpenRouter, shared-core + slice v4).
- **Phase J+** 🔶 — **ekspansi ekuitas (saham individual)**, universe = **BBCA +
  TSLA**. Build Contract v1.3 selesai di sisi kode (universe OHLCV, fundamentals,
  bank ratios, earnings, foreign-flow per-saham, Emiten Grader, sizing engine
  2.5% + buffer ARA/ARB, fraksi-harga zone calibration, lane-validation
  sign-off, Tab 8 Universe & Grader). Sisa = keputusan manual Giel (bar-replay,
  kalibrasi §13 final, prompt persona J-9) — bukan pekerjaan kode.

> **Berikutnya:** migrasi frontend vanilla HTML/CSS/JS → **Vue 3 + Vite** (rencana
> di [`docs/migrationFE.md`](docs/migrationFE.md)) supaya bisa menambah
> login/sidebar/dll tanpa beban stack mentah. Backend/API tidak berubah.

> Scope Phase A dikunci di `plan.txt`. Execution plan Phase B-E
> (`plan_b.txt`-`plan_e.txt`) dihapus setelah masing-masing selesai
> dieksekusi — ringkasan hasilnya ada di `docs/ROADMAP.md`.

Default password adalah 12345 gunakan untuk login

📄 **Dokumen lengkap ada di [`docs/`](docs/):**
[ARCHITECTURE.md](docs/ARCHITECTURE.md) (desain teknis & rationale),
[FLOW.md](docs/FLOW.md) (alur data, diagram),
[ROADMAP.md](docs/ROADMAP.md) (status tiap phase),
[SOP.md](docs/SOP.md) (kapan buka panel apa + **cara baca tiap item panel**),
[Master Plan.md](docs/Master%20Plan.md) (strategi, v1.6),
[migrationFE.md](docs/migrationFE.md) (rencana migrasi FE → Vue).

---

## 1. Apa yang dikerjakan

- **SQLite** `kastara-finance.db` dengan **22 tabel** (`db/schema.sql`) — 11
  tabel Phase A + 3 forward-layer (Phase D) + 7 ekuitas Phase J+
  (`instrument_metadata`, `fundamentals_quarterly`, `earnings_calendar`,
  `sector_benchmark`, `emiten_grade`, `grader_log`, `intake_log`) + 1
  `lane_validation_log` (bar-replay sign-off). `db/connection.py::EXPECTED_TABLES`
  adalah daftar otoritatifnya.
- **Scraper** modular (tiap source bisa jalan sendiri):
  - `scrapers/crypto.py` — CoinGecko + Binance + Alternative.me (BTC OHLCV,
    dominance, funding, OI, Fear & Greed). *Binance ke-block? otomatis fallback
    CoinGecko untuk OHLC.*
  - `scrapers/macro_yf.py` — yfinance (S&P 500, IHSG, Gold, USD/IDR, USD/JPY).
  - `scrapers/macro_fred.py` — FRED (DXY, US10Y, VIX, WALCL, RRP, TGA, HY spread).
    Butuh `FRED_API_KEY`.
  - `scrapers/news.py` — RSS (7 feed aktif: Fed FOMC, CNBC Finance/Economy/
    Indonesia, Investing ID, ANTARA, Bisnis.com — daftar di
    `scrapers/feeds_config.py`) + scoring rule-based HIGH/MED/LOW (bukan
    AI). `check_feed_health()` per feed tiap run — feed mati kelihatan
    langsung di `source_flags`/log, bukan backlog tersembunyi.
  - `scrapers/econ_calendar.py` — ForexFactory (event ekonomi masa depan:
    FOMC/CPI/dll), endpoint JSON gratis tidak resmi. Forecast/previous ikut
    tersimpan; `actual` (hasil rilis) sumber ini tidak pernah menyediakan
    kolom itu — diisi manual ATAU otomatis lewat pass kedua di bawah.
  - `scrapers/investing_calendar.py` — pass KEDUA, HANYA importance HIGH
    (bintang 3), isi `actual` yang tidak dipunyai ForexFactory. investing.com
    via `curl_cffi` (Cloudflare, pola sama `idx_foreign_flow.py`) — TAPI jauh
    lebih agresif rate-limit, jadi SENGAJA cuma 1x GET/run, dijadwalkan
    terpisah dari `run_daily` lewat `pipeline/run_investing_actual.py`
    (cron sore/malam sendiri, bukan ditambah ke cron pagi — lihat
    [ROADMAP.md](docs/ROADMAP.md) soal kenapa "grab semua cron 2x" tidak
    dipakai). Matching ke baris `econ_calendar` existing pakai fuzzy-match
    nama event (`difflib`) + `country`/`event_date` window, SKIP kalau
    ambigu — konservatif, tidak pernah menebak.
  - `scrapers/positioning.py` (Phase D) — COT report (CFTC Socrata API,
    gratis tanpa key: BTC/DXY/GOLD/SP500 net-long spekulan) + BTC ETF net
    flow (farside.co.uk, HTML scrape tak-resmi, butuh header browser-
    realistis krn situs di belakang Cloudflare — lihat
    [ARCHITECTURE.md §6.11](docs/ARCHITECTURE.md#611-scraperspositioningpy--cloudflare-butuh-header-browser-realistis)).
  - `scrapers/coinalyze.py` (Track B) — OI agregat lintas-exchange +
    liquidation long/short 24h + long/short ratio (Coinalyze REST, free key).
  - `scrapers/idx_foreign_flow.py` (Track C) — IHSG foreign flow level pasar
    (F2F/F2D/D2F + net), idx.co.id via `curl_cffi` (Cloudflare TLS fingerprint).
  - `scrapers/idx_stock_foreign_flow.py` (J-8) — foreign flow **per-saham**
    (volume beli/jual/net asing) dari `TradingSummary/GetStockSummary`.
  - `scrapers/idx_uma.py` (J-11) — cek flag integritas UMA (Unusual Market
    Activity) per emiten, input Emiten Grader.
  - `scrapers/equity_universe.py` (J-2) — OHLCV harian saham universe (yfinance
    `.JK`/US) untuk instrumen di `instrument_metadata`.
- **Pipeline** `pipeline/run_daily.py` — orchestrator harian, idempotent (UPSERT).
- **Pipeline (sore/malam, terpisah)** `pipeline/run_investing_actual.py` —
  cron KEDUA, isi `actual` HIGH-importance dari investing.com (lihat
  `scrapers/investing_calendar.py`). Belum ada di crontab — jalankan manual
  atau tambah baris cron sendiri (contoh: `0 21 * * *`, WIB).
- **Backfill** `pipeline/backfill.py` — tarik data historis (BTC/macro), preview-before-commit.
- **Manual article** `pipeline/add_article.py` — isi `manual_articles` untuk riset
  historis (RSS tidak bisa backfill — lihat [Artikel manual](#artikel-manual-riset-historis)).
- **Indikator Phase A** `indicators/calc.py` — `net_liquidity`, `volume_ma20`.
- **Analysis engine** (`analysis/`, generic sejak Phase B), aktif utk
  **BTC/GOLD/IHSG/SP500/USDIDR/USDJPY** (Phase F+ expansion):
  - `analysis/sr_zones.py` — deteksi zona support/resistance (swing
    high/low + clustering + touch count).
  - `analysis/signals.py` — deteksi breakout/retest + R:R calculator.
  - `pipeline/run_analysis.py` — orchestrator, tulis ke `sr_zones` +
    `trade_signals`. **Suggestion only** — `approved` selalu 0 dari kode.
    Tanpa `--instrument`, proses ke-6 instrument sekaligus.
  - `tools/review_signal.py` — CLI approve/reject sinyal by id eksplisit.
  - `pipeline/seed_context_weight.py` — seed pembobotan driver per aset
    (persis contoh Master Plan §4.3, mis. GOLD: real_yield/dxy/geopolitik).
- **Telegram Daily Briefing Phase E** (`notify/`, `pipeline/`):
  - `notify/telegram.py` — `send_message()` (push satu arah, bukan bot
    dua-arah) + `get_latest_chat_id()` (helper setup sekali pakai).
  - `pipeline/compose_briefing.py` — rakit teks briefing dari data yang
    SUDAH kamu isi manual (4 lensa, sinyal approved) — tidak generate
    apa pun sendiri.
  - `pipeline/send_briefing.py` — CLI, dipicu manual (lihat
    [Daily Briefing](#daily-briefing-ke-telegram-phase-e)).
- **Ekspansi ekuitas Phase J+** (saham individual, universe **BBCA + TSLA** —
  Build Contract v1.3, detail per J-step di `docs/ROADMAP.md`):
  - `analysis/grader.py` — Emiten Grader dua-sumbu (fund_score × integrity
    flags → kuadran INVESTABLE/WATCH/SPECULATIVE/AVOID), log ke `emiten_grade`/
    `grader_log`.
  - `analysis/sizing.py` — position sizing MAX_RISK 2.5% (locked), kuantisasi
    lot pembulatan-bawah, skip `RISK_CAPACITY_EXCEEDED` (tanpa geser SL), buffer
    **ARA/ARB 1.5×** (§18, locked) via `has_daily_limit`.
  - `analysis/calibration.py` — toleransi zona S&R per-market dari **fraksi
    harga IDX** resmi (Peraturan No. II-A BEI); dipakai `run_analysis` khusus
    instrumen `market='IDX'` (**DRAFT** pending validasi bar-replay Giel, §13.1).
  - `pipeline/backfill_fundamentals.py` — fundamentals kuartalan (yfinance);
    rasio bank CAR/NPL/NIM/LDR diisi **manual** (Panel 8), tak tertimpa scraper.
  - `web/writes.py::validate_lane()` — satu-satunya jalur yang mengisi
    `lane_validated_at` / menaikkan lane ke TRADE, murni manual (bar-replay
    sign-off), log ke `lane_validation_log`.
  - Tab 8 **Universe & Grader** (Panel 8) — intake kandidat, uji kelayakan,
    detail emiten + override kuadran, rasio bank, validasi lane, grader log.

Semua scraper **tahan API-fail**: kalau satu source mati, ditandai `fail` di
`source_flags` dan pipeline tetap lanjut (tidak crash, tidak silent).

---

## 2. Setup

Butuh Python 3.11+.

```bash
# 1. virtualenv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. dependencies
pip install -r requirements.txt

# 3. konfigurasi (opsional, hanya untuk FRED & Telegram)
cp .env.example .env
# edit .env, isi FRED_API_KEY (gratis: https://fred.stlouisfed.org/docs/api/api_key.html)
```

FRED opsional — tanpa key, series FRED akan di-`skip` (bukan error), sisanya
tetap jalan.

**Setup Telegram (opsional, untuk Daily Briefing Phase E):**
1. Chat ke `@BotFather` di Telegram, kirim `/newbot`, ikuti instruksi -> dapat `TELEGRAM_BOT_TOKEN`.
2. Kirim 1 pesan apa saja (mis. `/start`) ke bot barumu dari akun Telegram-mu sendiri.
3. `python -m notify.telegram` -> print `chat_id` dari update terakhir.
4. Isi `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` di `.env`.

Tanpa setup ini, tombol "Kirim ke Telegram" / `pipeline.send_briefing` tetap
menampilkan teks briefing-nya, cuma `sent: false` (tidak benar-benar terkirim).

**Setup OpenRouter (opsional, untuk Panel 4 "4 Analisa (AI)"):**
1. Daftar di https://openrouter.ai, generate API key.
2. Isi `OPENROUTER_API_KEY` (dan opsional `OPENROUTER_MODEL`, default
   `anthropic/claude-sonnet-5` — cek model id yang masih aktif di
   https://openrouter.ai/models, model lama sering di-deprecate) di `.env`.
3. Tulis system prompt tiap persona di `prompts/persona_<gema|leon|akela|rivan>.txt`
   (lihat `prompts/README.md`) — file ini TIDAK dibuat otomatis & TIDAK
   di-commit. Tanpa ini, tombol "Jalankan Analisa" akan kasih tahu di UI
   kalau prompt-nya belum diisi.

**Setup Coinalyze (opsional, untuk Panel 1 OI agregat/liquidation/L-S ratio):**
1. Daftar gratis di https://coinalyze.net, generate API key.
2. Isi `COINALYZE_API_KEY` di `.env`.

Tanpa ini, 4 field baru (OI Agregat, Long/Short Ratio, Liquidation Long/Short 24h)
di kategori "Crypto (BTC)" Panel 1 tetap `n/a` (di-`skip`, bukan error) — sisanya
tetap jalan seperti biasa.

**IHSG Foreign Flow (Panel 3 Positioning) — otomatis, TANPA setup:** sumbernya
idx.co.id (bukan API resmi publik), tidak butuh API key. Satu catatan teknis:
scraper-nya (`scrapers/idx_foreign_flow.py`) pakai `curl_cffi` (bukan `requests`
biasa) karena idx.co.id di belakang Cloudflare bot-management yang mendeteksi
TLS fingerprint Python — kalau field ini kosong terus di Panel 3, cek dulu apa
`curl_cffi` ke-install (`pip show curl_cffi`) sebelum curiga API-nya berubah.

---

## 3. Cara pakai

### Inisialisasi DB (otomatis dipanggil pipeline, tapi bisa manual)
```bash
python -m db.connection
# -> bikin kastara-finance.db + 22 tabel
```

### Jalankan pipeline harian
```bash
python -m pipeline.run_daily              # tanggal hari ini (WIB)
python -m pipeline.run_daily 2026-06-24   # tanggal tertentu
python -m pipeline.run_investing_actual   # Evening Cron
```
Idempotent — aman dijalankan berkali-kali untuk tanggal sama (UPSERT, bukan
duplikat). Akhir run mencetak ringkasan `source ok / fail / skip` per API.

### Backfill data historis (preview dulu, baru commit)
```bash
python -m pipeline.backfill --instrument BTC   --from 2025-01-01 --to 2025-06-01
python -m pipeline.backfill --instrument SP500 --from 2025-01-01 --to 2025-06-01
python -m pipeline.backfill --instrument DXY   --from 2025-01-01 --to 2025-06-01  # butuh FRED_API_KEY
python -m pipeline.backfill --instrument BTC   --from 2025-01-01 --to 2025-06-01 --yes  # skip konfirmasi
```
Instrument yang didukung:
- yfinance / asset_ohlcv: `BTC` `SP500` `IHSG` `GOLD` `USDIDR` `USDJPY`
- FRED / daily_market: `DXY` `US10Y` `VIX` `WALCL` `RRP` `TGA` `HY`

Backfill selalu menampilkan **preview** (berapa baris baru, berapa duplikat
di-skip) dan minta konfirmasi `[y/N]` sebelum menulis.

Backfill itu bootstrap **sekali**, bukan job berulang — jangan taruh di cron
yang sama dengan `run_daily`. Aman dipanggil back-to-back untuk banyak
instrument sekaligus (yfinance/FRED balikin seluruh rentang tanggal dalam
1 request, jumlah request tidak berubah walau rentang tahunnya lebih jauh,
mis. dari 2010 vs dari 2021).

### Artikel manual (riset historis)

RSS (`scrapers/news.py`) cuma nampilin berita **terkini** — tidak ada cara
narik headline lama (mis. dari 2010) dari RSS, itu keterbatasan struktural
sumbernya, bukan sesuatu yang bisa di-backfill. Untuk riset historis, isi
`manual_articles` manual:

```bash
# Tambah artikel yang kamu temukan/kurasi sendiri
python -m pipeline.add_article add --date 2015-06-19 --source CNBC \
    --url "https://..." --headline "Fed hints at rate hike" \
    --notes "Titik balik penting buat DXY tahun itu" \
    --tags fed,rate,dxy --key-event

# Cari lagi buat riset nanti
python -m pipeline.add_article list --tag dxy
python -m pipeline.add_article list --from 2015-01-01 --to 2015-12-31
python -m pipeline.add_article list --search "rate hike"
```
Kalau URL yang sama sudah pernah ditambah, tool cuma **kasih tahu** (bukan
blok) lalu minta konfirmasi — re-visit artikel yang sama dengan catatan baru
itu valid.

### Analysis engine (S&R + breakout/retest, 6 instrument sejak Phase F+)

```bash
# Jalankan deteksi zona S&R + sinyal breakout/retest untuk SEMUA instrument
# (BTC, GOLD, IHSG, SP500, USDIDR, USDJPY)
python -m pipeline.run_analysis

# Atau 1 instrument saja
python -m pipeline.run_analysis --instrument GOLD
```
Idempotent (re-run tidak duplikat zona/sinyal, tidak menimpa
`validated`/`notes` yang sudah direview manual). **Manual trigger**
untuk sekarang, belum di-cron (lokal cuma dev).

```bash
# Review sinyal (WAJIB by id eksplisit — tidak ada mode approve-semua)
python -m tools.review_signal list
python -m tools.review_signal list --instrument BTC --valid-only
python -m tools.review_signal approve --id 42 --notes "setup bagus, volume kuat"
python -m tools.review_signal reject  --id 42 --notes "DXY breakout barengan, skip"

# Seed pembobotan driver per aset (sekali, idempotent)
python -m pipeline.seed_context_weight
```

Semua sinyal dari `run_analysis` **suggestion only** — `approved`
selalu 0 dari kode, cuma berubah lewat `review_signal approve`. Tidak ada
execution/trading logic di mana pun.

### Dashboard web (8 panel, write-enabled sejak Phase C)
```bash
python -m web.app
# buka http://127.0.0.1:5000
```
Navigasi 8 tab: **1 Snapshot** (cards +
source_flags + form Manual Backfill preview→confirm), **2 News** (list +
filter impact + flag key trigger + Add Manual Article), **3 Forward**
(Economic Calendar data asli + forecast/previous/actual manual, Expectations
manual FedWatch/Dot Plot, Positioning COT+ETF otomatis & SBN manual, Policy
Tracker manual, Disonansi Flag rule-based), **4 Reading**
(4 lensa GEMA/LEON/AKELA/RIVAN via OpenRouter + External AI Check manual +
Conflict Notes), **5 Chart** (candlestick + S&R zone overlay + marker
breakout/retest + Approve/Reject sinyal + MA50/100/200 + filter rentang +
badge lane), **6 Synthesis** (textarea + outlook instrumen + Trading Journal +
position sizing + Prediction Log + skor prediksi + Daily Briefing), **7
Riwayat** (arsip synthesis/prediksi/jurnal/lensa, sub-tab), **8 Universe &
Grader** (Phase J+: universe saham, intake kandidat, uji kelayakan + grade,
detail emiten + override kuadran, rasio bank manual, validasi lane bar-replay,
grader log). Panel 1–6 = ritme harian TRADE lane; Panel 8 = ritme mingguan/
kuartalan INVEST lane (lihat [SOP.md](docs/SOP.md)).

**Tanpa autentikasi** (local-only, `WEB_HOST`/`WEB_PORT` bisa diatur via
`.env`). **Tidak ada pemanggilan AI/LLM otomatis di mana pun** — "External
AI Check" di Panel 4 itu kolom paste manual (kamu banding hasil tool lain
sendiri), bukan Kastara yang manggil AI.

API: **57 endpoint `/api/*`** (33 GET + 24 POST), semuanya `jsonify(...)` —
`/` cuma render shell statis, semua data client-side fetch. Read-only Phase 1
(`/api/latest`, `/api/daily_market`, `/api/asset_ohlcv`, `/api/news`,
`/api/assets`, `/api/health`) tidak berubah. Grup lain: Phase C write
(`/api/backfill/*`, `/api/reading/save`, `/api/signals/review`,
`/api/synthesis/save`, `/api/journal/add`, `/api/prediction/*`), Phase D
(`/api/expectations`, `/api/positioning`, `/api/disonansi`), Phase E
(`/api/briefing/send`), Persona (`/api/persona/{run,status}`), dan Phase J+
(`/api/universe`, `/api/intake/*`, `/api/emiten/<t>{,/override,/validate_lane}`,
`/api/sizing/suggest`, `/api/fundamentals/bank_ratios`, `/api/grader_log`,
`/api/lane_validation_log`). Daftar otoritatif = route di `web/app.py`.

### Daily Briefing ke Telegram (Phase E)
```bash
python -m pipeline.send_briefing --dry-run     # print teks, tidak kirim
python -m pipeline.send_briefing               # kirim ke Telegram hari ini
python -m pipeline.send_briefing --date 2026-07-08
```
Dijalankan **manual** oleh kamu sendiri setelah selesai Panel 4-6 (4 lensa +
approve sinyal terisi) — bukan bagian dari `run_daily`, karena isi briefing
baru lengkap setelah rutinitas pagi selesai (~07:20), bukan pas data pull
jam 07:00. Ada juga tombol "Kirim ke Telegram" di Panel 6 dashboard yang
melakukan hal sama. Section yang belum kamu isi tampil `(belum diisi)` —
bukan disembunyikan — supaya kelihatan kalau ada yang kelewat.

### Test
```bash
python -m pytest -q
```

---

## 4. Skema data (ringkas)

| Tabel | Diisi? | Isi |
|---|---|---|
| `daily_market` | ✅ otomatis | 1 row/tanggal — konteks makro global (BTC, DXY, S&P, IHSG, Fear&Greed, net liquidity, dll) + `source_flags` JSON |
| `asset_ohlcv` | ✅ otomatis | 1 row/aset/tanggal — OHLCV universal + `volume_ma20` |
| `daily_news` | ✅ otomatis | headline + `impact_level` (HIGH/MED/LOW) |
| `econ_calendar` | ✅ otomatis | event ekonomi masa depan (ForexFactory), UPSERT by natural key |
| `manual_articles` | 🖊️ manual (ada tool) | riset historis — isi via `python -m pipeline.add_article`, RSS tidak bisa backfill |
| `positioning` | ✅ otomatis + 🖊️ manual | COT (CFTC) + BTC ETF flow otomatis tiap `run_daily`; SBN foreign flow & koreksi manual via dashboard |
| `expectations` | 🖊️ manual | CME FedWatch cut probability, Fed Dot Plot median — tidak ada sumber gratis, isi via dashboard Panel 3 |
| `policy_tracker` | 🖊️ manual | pernyataan pembuat kebijakan, `literal_statement` vs `inference` terpisah tegas, via dashboard Panel 3 |
| `reading_workspace`, `trade_signals`, `sr_zones`, `trading_journal`, `prediction_log`, `asset_context_weight` | 🖊️/⚙️ | dipakai Phase B/C (lihat bagian masing-masing di atas) |
| `instrument_metadata` | ✅ + 🖊️ | 1 row/saham universe Phase J+ — lane, lot_size, sektor, `has_daily_limit`, `lane_validated_at` (bar-replay) |
| `fundamentals_quarterly` | ✅ + 🖊️ | fundamentals kuartalan (yfinance) + rasio bank CAR/NPL/NIM/LDR (manual) |
| `earnings_calendar` | ✅ | jadwal earnings/corporate action (yfinance), penegak rule no-hold-through-earnings saham AS |
| `emiten_grade`, `grader_log`, `intake_log` | ⚙️ + 🖊️ | hasil Emiten Grader + audit log + keputusan intake kandidat |
| `lane_validation_log` | 🖊️ | jejak validasi lane bar-replay (append-only, hanya lewat `validate_lane()`) |
| `sector_benchmark` | ⚙️ | struktur pembanding sektor (J-5, belum diisi — 1 ticker/sektor belum worth) |

`source_flags` (JSON di `daily_market`) mencatat status tiap API per run, mis:
```json
{"coingecko_ohlcv": "ok", "binance_ohlcv": "fail", "fred_dxy": "skip", "yf_SP500": "ok"}
```

Semua tanggal disimpan `YYYY-MM-DD`, waktu dalam **WIB (UTC+7)**.

---

## 5. Otomatisasi (cron)

**Crontab sudah terinstall** untuk user saat ini (`crontab -l` untuk lihat),
jadwal `0 0 * * *` (00:00 WIB — TZ sistem WSL ini sudah `Asia/Jakarta`, tidak
perlu konversi). Log ditulis ke `logs/run.log` (gitignored).

```cron
MAILTO=""
0 0 * * *  cd /path/ke/kastara-finance && .venv/bin/python -m pipeline.run_daily >> logs/run.log 2>&1
```

**Yang masih perlu 1 langkah manual (butuh password sudo, tidak bisa
dijalankan otomatis):**

```bash
# 1. Nyalakan cron daemon (sekali, sampai WSL instance di-restart)
sudo service cron start

# 2. (opsional, direkomendasikan) supaya cron ikut nyala otomatis tiap kali
#    instance WSL ini start — edit /etc/wsl.conf, tambah:
#    [boot]
#    command = service cron start
sudo nano /etc/wsl.conf
```

**Catatan penting soal WSL:** cron cuma jalan selama instance WSL ini aktif.
WSL **tidak otomatis start** saat Windows boot kecuali ada yang memicunya
(buka terminal WSL, atau Windows Task Scheduler diatur menjalankan
`wsl.exe` saat logon). Kalau butuh jadwal yang benar-benar tidak pernah
mati, pertimbangkan VPS kecil untuk cron ini nanti (bukan prioritas
sekarang — lihat `plan.txt` §9, scheduler library belum dipakai di Phase A).

Scheduler library (APScheduler dll) tetap belum dipakai — cron OS cukup.

---

## 6. Catatan implementasi

- **Binance sering ke-block** di sebagian jaringan/region (termasuk ID). Scraper
  crypto otomatis fallback ke CoinGecko untuk OHLC; funding rate & open interest
  (Binance futures) akan `fail` dan dikosongkan — itu by design, bukan bug.
  Untuk pakai Binance (VPN aktif) atau route lewat proxy, atur di `.env`:
  `BINANCE_BASE`, `BINANCE_FAPI_BASE`, `BINANCE_ENABLED`, atau `KASTARA_PROXY`
  (mis. `socks5://127.0.0.1:1080`). Lihat `.env.example`.
- **`SQLITE_BUSY` / database is locked** (mis. buka DB di DBeaver): DB pakai
  mode **DELETE** (default SQLite) + `busy_timeout=5000` (lihat
  `db/connection.py`) — proses Python kita otomatis retry s/d 5 detik kalau
  ada lock singkat. Akar masalahnya kalau muncul di DBeaver biasanya
  **DBeaver di Windows connect lewat path `\\wsl.localhost\...`** — itu
  efektif network share (9P) dari sisi Windows, dan SQLite (apalagi mode
  WAL, yang sempat dicoba dan tidak membantu — lihat
  `docs/ARCHITECTURE.md §6.1`) tidak reliable lintas boundary Windows↔WSL.
  **Solusi permanen: install DBeaver DI DALAM WSL** (bukan di Windows),
  jalan via WSLg — akses file jadi native, boundary-nya hilang total.
  Sudah di-setup di `~/dbeaver` (tarball no-root, bundled JRE, tidak perlu
  `sudo`/`apt`):
  ```bash
  ~/dbeaver/launch.sh          # jalankan DBeaver (muncul sebagai window Windows via WSLg)
  ```
  Koneksi di DBeaver: pakai path native sesuai `KASTARA_DB_PATH` di `.env`
  (lihat poin berikutnya — **bukan** lagi di dalam folder project), dan
  **bukan** `\\wsl.localhost\...`. Kalau tetap mau pakai DBeaver versi
  Windows: tutup semua tab/reconnect fresh (transaksi lama yang nyangkut di
  client itu penyebab paling umum) + tambah driver property
  `busy_timeout=5000`.
- **`KASTARA_DB_PATH` — lokasi DB**: file DB sengaja ditaruh **di luar folder
  project** (`.env`: `KASTARA_DB_PATH=/home/<user>/LOCAL/kastara-finance-data/kastara-finance.db`)
  supaya tidak nyampur sama kode/git — DB berubah tiap hari (pipeline/cron),
  kode tidak; motong risiko ke-commit atau ke-include ke operasi git secara
  tidak sengaja. Boleh juga isi path Windows UNC
  (`\\wsl.localhost\<distro>\home\...`) — otomatis diterjemahkan ke path
  native Linux (file yang sama), tapi untuk akses dari WSL sendiri (pipeline,
  DBeaver-di-WSL) pakai path native langsung seperti contoh di atas.
- **SQLite vs Postgres/NoSQL**: untuk backfill sampai ~5 tahun data harian,
  SQLite masih pas — datanya tabular (cocok relational, bukan NoSQL) dan
  volumenya (puluhan ribu baris `asset_ohlcv`, ratusan ribu `daily_news`) jauh
  di bawah kapasitas SQLite. Sudah ditambah index untuk query range-tanggal
  di skala itu: `idx_asset_ohlcv_instrument_date`, `idx_daily_news_dedup`
  (juga menegakkan dedup by headline di level DB), `idx_daily_news_impact_date`.
  Pindah ke Postgres baru relevan kalau nanti multi-user concurrent atau butuh
  hosting cloud managed — bukan soal volume data historisnya.
- **RSS feed bisa mati/pindah.** Registry di `scrapers/feeds_config.py`
  (`FEEDS`) — satu-satunya tempat ganti url/enabled, jangan sentuh
  `news.py`. `check_feed_health()` cek tiap feed tiap run (status masuk
  `source_flags` prefix `rss_`, `run_daily` print ringkasan `RSS: X ok, Y
  dead`) — feed mati langsung kelihatan di log, bukan backlog tersembunyi.
- **FRED series id kadang berubah.** Lihat `scrapers/macro_fred.py` (`SERIES`).
  Series gagal ditandai `fail` per-series, pipeline lanjut.
- **Tidak ada API key di source code.** Semua via `.env` + `python-dotenv`.
- **Tidak ada kode dari repo AGPL** (OpenBB dll) yang disalin ke project ini.

---

*Kastara Finance Master Plan v1.6 (`docs/Master Plan.md`) + Phase J+ Build
Contract v1.3. Status per-phase & keputusan terkunci: `docs/ROADMAP.md`. Ritme
pemakaian: `docs/SOP.md`. Inisiatif berikutnya: migrasi FE → Vue
(`docs/migrationFE.md`).*
