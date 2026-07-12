# Kastara Finance — Technical Architecture

> Status per dokumen ini: **Phase A (data layer) + Phase 1 (read-only dashboard) selesai.**
> Lihat [ROADMAP.md](ROADMAP.md) untuk status tiap phase, [FLOW.md](FLOW.md) untuk alur data.

---

## 1. Ringkasan Sistem

Kastara Finance adalah **data layer + dashboard read-only** untuk memantau
konteks makro (crypto, ekuitas, FX, likuiditas global) dan berita finansial,
sebagai basis untuk analisis manual (dan nantinya semi-otomatis di Phase B+).

Prinsip desain inti (dikunci sejak awal, lihat [plan.txt](../plan.txt)):

- **Data layer dulu, baru logic.** Phase A murni tarik & simpan data mentah.
  Tidak ada trading/signal logic di sini.
- **Tangan, bukan otak.** Keputusan arsitektur dikunci di planning doc;
  eksekusi ikut spec, tidak improvisasi desain besar tanpa instruksi baru.
- **Tahan gagal, bukan diam-diam gagal.** Tiap sumber data yang gagal dicatat
  statusnya (`source_flags`), pipeline tetap jalan — tidak pernah crash total
  karena satu API down, dan tidak pernah menyembunyikan kegagalan itu.
- **Idempotent.** Menjalankan pipeline atau backfill berkali-kali untuk
  tanggal yang sama = update, bukan duplikat baris.
- **Gratis & ringan.** Semua sumber data no-key atau free-tier. Tidak ada
  dependency berat (no ML/tensorflow), tidak ada infra berat (SQLite lokal,
  bukan Postgres/cloud) — lihat [§6](#6-keputusan-desain--rationale) untuk
  kapan ini perlu ditinjau ulang.

---

## 2. Tech Stack

| Layer | Pilihan | Alasan |
|---|---|---|
| Bahasa | Python 3.11+ (dijalankan di 3.14 lewat WSL) | Ekosistem data/scraping matang |
| Database | SQLite (`kastara-finance.db`), mode **DELETE** + `busy_timeout` | Lihat [§6.1](#61-sqlite-vs-postgres-vs-nosql) |
| HTTP client | `requests` | Simpel, cukup untuk REST/JSON |
| Data harga | `yfinance` | Gratis, no key, cakupan luas (ekuitas/FX/komoditas) |
| Transform ringan | `pandas` | Dipakai seperlunya (agregasi OHLC), bukan ML |
| RSS | `feedparser` | Parsing feed berita |
| Env/secrets | `python-dotenv` | Config lewat `.env`, tidak ada key hardcoded |
| Web/API | `Flask` | Kecil, cukup untuk dashboard read-only Phase 1 |
| Test | `pytest` | Standar de-facto Python |

Semua di [requirements.txt](../requirements.txt). Tidak ada dependency berat
(no ML framework) — sesuai batasan di `plan.txt`.

---

## 3. Struktur Folder

```
kastara-finance/
├── .env / .env.example     # secrets & config (FRED key, Binance override, dll)
├── db/
│   ├── schema.sql           # DDL 14 tabel + index
│   └── connection.py        # get_connection(), init_db(), resolve path (WSL/Windows aware)
├── scrapers/                # 1 file = 1 sumber data, tiap file jalan sendiri
│   ├── base.py               # http_get retry, SourceFlags, proxy, waktu WIB
│   ├── crypto.py             # CoinGecko + Binance + Alternative.me
│   ├── coinalyze.py          # OI agregat (3 exchange) + liquidation L/S + LS ratio
│   ├── macro_fred.py         # FRED (DXY, US10Y, VIX, WALCL, RRP, TGA, HY)
│   ├── macro_yf.py           # yfinance (SP500, IHSG, Gold, USD/IDR, USD/JPY)
│   ├── news.py               # RSS + scoring rule-based (bukan AI)
│   ├── econ_calendar.py      # ForexFactory calendar (event masa depan)
│   ├── positioning.py        # COT (CFTC) + BTC ETF flow (farside.co.uk)
│   └── idx_foreign_flow.py   # IHSG foreign flow (idx.co.id, curl_cffi -- Cloudflare)
├── pipeline/
│   ├── run_daily.py          # orchestrator harian, UPSERT idempotent
│   ├── backfill.py           # tarik historis, preview-before-commit
│   ├── add_article.py        # CLI manual_articles (riset historis)
│   ├── run_analysis.py       # orchestrator Phase B (S&R + sinyal, BTC)
│   └── seed_context_weight.py  # seed asset_context_weight (BTC)
├── indicators/
│   └── calc.py               # net_liquidity, volume_ma20 (calculated fields, Phase A)
├── analysis/                  # engine Phase B — S&R + breakout/retest
│   ├── indicators.py           # MA, volume ratio, rolling_ma (beda dari indicators/calc.py)
│   ├── sr_zones.py              # swing detection, clustering, touch count
│   └── signals.py               # breakout/retest detection + R:R calculator
├── tools/
│   └── review_signal.py       # CLI approve/reject trade_signals (by id eksplisit)
├── web/                      # dashboard: read-only (Phase 1) + write (Phase C)
│   ├── app.py                 # Flask, endpoint JSON + halaman, 7 tab panel
│   ├── writes.py               # pure functions tulis-DB Phase C (testable
│   │                             tanpa Flask, pola sama add_article.py)
│   ├── templates/
│   │   ├── index.html         # shell tipis: head+nav+{% include %} tiap
│   │   │                         panel+<script src> tiap JS, tanpa build step/CDN
│   │   └── partials/panelN_*.html  # 1 file per tab (HTML saja)
│   └── static/
│       ├── css/dashboard.css  # semua style (dulu inline di index.html)
│       └── js/{core,panel1..7,main}.js  # core = shared helpers + table
│                                 utility; per-panel JS terpisah; main.js
│                                 = refreshAll()+init. Load order penting
│                                 (semua fungsi global, bukan module).
├── tests/                    # 1 test file per modul utama
└── docs/                     # dokumen ini
```

Aturan modular: **tiap scraper harus bisa dijalankan & ditest sendiri**
(`python -m scrapers.crypto`, dst) — tidak saling bergantung satu sama lain.

---

## 4. Skema Database

14 tabel total (11 dasar Phase A + 3 forward-layer, ditambah saat menutup
gap terhadap Master Plan §10). Phase A **mengisi** 4 tabel aktif; sisanya
struktur saja (disiapkan untuk Phase B/D, tidak dipakai sekarang).

### 4.1 Tabel aktif (Phase A + B)

| Tabel | Grain | Isi |
|---|---|---|
| `daily_market` | 1 baris / tanggal | Snapshot makro global: BTC, DXY, S&P500, IHSG, VIX, Fear&Greed, net liquidity, dll + `source_flags` (JSON status tiap API) |
| `asset_ohlcv` | 1 baris / (tanggal, instrument) | OHLCV universal semua aset yang tradeable: BTC, SP500, IHSG, GOLD, USDIDR, USDJPY |
| `daily_news` | 1 baris / headline unik | Headline RSS + `impact_level` (HIGH/MED/LOW, rule-based) |
| `econ_calendar` | 1 baris / event unik (`event_date`+`event_name`+`country`) | Event ekonomi masa depan (FOMC/CPI/dll) dari ForexFactory, UPSERT (forecast bisa berubah mendekati rilis) |
| `sr_zones` | 1 baris / zona unik (bucket relatif, per instrument+zone_type) | Zona S&R hasil deteksi `analysis/sr_zones.py`, UPSERT dari `pipeline/run_analysis.py`. `validated`/`notes` manual — tidak pernah ditimpa re-run. |
| `trade_signals` | 1 baris / event sinyal (append-only) | Breakout/retest hasil `analysis/signals.py`. `approved` selalu 0 dari kode — direview manual via `tools/review_signal.py`. |
| `asset_context_weight` | 1 baris / (instrument, driver) | Pembobotan driver per aset (Master Plan §4.3). BTC di-seed via `pipeline/seed_context_weight.py`. |
| `manual_articles` | 1 baris / artikel | Riset historis manual (RSS tidak bisa backfill) via `pipeline/add_article.py`. |

### 4.2 Tabel struktur-saja (Phase C/D)

`reading_workspace`, `trading_journal`, `prediction_log` (Phase C) +
`expectations`, `positioning`, `policy_tracker` (Phase D, forward-layer
Master Plan §4.2) — DDL sudah ada di `schema.sql`, belum ada scraper/writer
yang mengisi.

> **Deviasi FK yang disengaja:** Master Plan menulis kolom `date` di tabel
> ini sebagai *"FOREIGN KEY → daily_market"*. `schema.sql` tidak
> mengimplementasikan `FOREIGN KEY` SQL sungguhan — relasi hanya
> by-convention (nilai `date` yang cocok). Ini konsisten dengan `plan.txt`
> (execution plan yang benar-benar dipakai), bukan penyimpangan tak sengaja.

### 4.3 Index

Ditambahkan supaya query tetap cepat saat histori bertambah (target: backfill
sampai ~5 tahun data harian):

| Index | Kolom | Melayani |
|---|---|---|
| `idx_asset_ohlcv_instrument_date` | `(instrument, date)` | `WHERE instrument = ? ORDER BY date` — dipakai chart, `volume_ma20`, dedup-check backfill |
| `idx_daily_news_dedup` (**UNIQUE**) | `(date, headline)` | Dedup headline **ditegakkan di level DB**, bukan hanya app-code |
| `idx_daily_news_impact_date` | `(impact_level, date DESC)` | Filter dashboard `/api/news?impact=HIGH` + `ORDER BY date` sekaligus (tanpa temp sort) |
| `idx_econ_calendar_dedup` (**UNIQUE**) | `(event_date, event_name, country)` | Natural key untuk UPSERT — event yang sama di-refresh (forecast berubah mendekati rilis), bukan duplikat |

`daily_market.date` sudah `PRIMARY KEY` (index otomatis). Tabel Phase B/D
belum diberi index karena belum ada query nyata terhadapnya.

### 4.4 `source_flags` — kontrak penting

Setiap baris `daily_market` punya kolom `source_flags` berisi JSON:

```json
{"coingecko_ohlcv": "ok", "binance_ohlcv": "fail", "fred_dxy": "skip", "yf_SP500": "ok"}
```

Nilai: `"ok"` (sukses), `"fail"` (dicoba, error), `"skip"` (sengaja dilewati,
mis. Binance dimatikan via env, atau FRED_API_KEY kosong). Ini adalah
**audit trail** tiap run — jangan dihapus/diringkas, dashboard dan debugging
bergantung padanya.

---

## 5. Modul & Tanggung Jawab

### 5.1 `scrapers/base.py` — kontrak bersama
- `http_get` / `http_get_json`: retry + backoff, dukung proxy via
  `KASTARA_PROXY`.
- `SourceFlags`: akumulator status (`ok`/`fail`/`skip`) per sumber per run.
- `safe_call(name, fn, flags)`: bungkus tiap panggilan API — exception
  ditangkap, ditandai `fail`, **tidak pernah dilempar ke pipeline**.
- `today_wib()` / `now_wib()`: semua waktu dalam WIB (UTC+7), tanggal
  disimpan `YYYY-MM-DD`.

### 5.2 Scraper (masing-masing return dict standar + `source_flags`)
- `crypto.py`: Binance jadi sumber utama BTC OHLCV (bisa dimatikan/di-reroute
  via `.env` — lihat [§6.2](#62-binance-region-block)); fallback otomatis ke
  CoinGecko kalau Binance gagal/dimatikan.
- `macro_yf.py`: 5 ticker yfinance, hitung `change_pct` vs penutupan
  sebelumnya.
- `macro_fred.py`: FRED API, tiap series independen — satu gagal tidak
  menggagalkan yang lain. Tanpa `FRED_API_KEY` → semua di-`skip` (bukan error).
- `news.py`: RSS feeds (bisa mati/pindah sewaktu-waktu, ditandai `fail` bukan
  crash) + scoring rule-based (keyword, word-boundary match — bukan LLM).
- `econ_calendar.py`: ForexFactory (endpoint JSON tidak resmi, gratis
  no-key — lihat [§6.5](#65-economic-calendar-sumber-tidak-resmi)). Event
  masa depan, UPSERT by `(event_date, event_name, country)` karena
  forecast bisa berubah mendekati rilis.

### 5.3 `pipeline/run_daily.py` — orchestrator
Panggil semua scraper → gabung hasil → hitung calculated fields
(`net_liquidity`, `volume_ma20`) → UPSERT ke `daily_market` +
`asset_ohlcv` → `INSERT OR IGNORE` ke `daily_news` (dedup via unique index)
→ UPSERT `econ_calendar` (natural key, refresh forecast) → cetak ringkasan
ok/fail/skip. **Idempotent**: aman dijalankan berkali-kali untuk tanggal
sama. Dijadwalkan via **crontab per-user** (`0 0 * * *`) — lihat
[README §5](../README.md#5-otomatisasi-cron).

### 5.4 `pipeline/backfill.py` — historical fetch
CLI dengan **preview wajib sebelum commit**: hitung baris baru vs duplikat,
tampilkan, minta konfirmasi `[y/N]` (atau `--yes` untuk non-interaktif).
Duplikat (`date`+`instrument` sudah ada) di-skip, bukan error.

### 5.5 `indicators/calc.py`
Pure functions (`net_liquidity`, `volume_ma20_from_values`) + satu fungsi
yang query DB (`volume_ma20_for_instrument`) untuk hitung rata-rata volume
20-hari dari histori `asset_ohlcv`.

### 5.6 `web/app.py` + `web/writes.py` — dashboard (Phase 1 read-only + Phase C write)

Endpoint Phase 1 (`/api/latest`, `/api/daily_market`, `/api/asset_ohlcv`,
`/api/news`, `/api/assets`, `/api/health`) **tetap read-only, tidak diubah**
sejak Phase C dikerjakan. Endpoint baru Phase C **menulis**, tapi TIDAK
menulis logic baru langsung di route — semua reuse fungsi yang sudah ada
& teruji:
- Backfill (`/api/backfill/preview`, `/api/backfill/commit`) → panggil
  `pipeline.backfill.backfill()` langsung (lihat §6.8 soal `preview_only`).
- Manual article (`/api/articles/add`) → `pipeline.add_article.insert_article()`.
- Approve/reject sinyal (`/api/signals/review`) → `tools.review_signal.set_review()`.
- Reading workspace, trading journal, prediction log, policy tracker,
  key-trigger flag → fungsi baru di `web/writes.py` (pure, testable tanpa
  Flask — `tests/test_web_writes.py`, tidak ada test Flask-route langsung,
  endpoint cukup diverifikasi manual via preview browser).

Navigasi 6 tab (satu halaman, JS `display:none/block`, bukan reload) —
urutan sama dengan alur pagi Master Plan §0: Snapshot → News → Forward →
Reading → Chart → Synthesis.

**Tanpa autentikasi** (keputusan sadar, `plan_c.txt` §6.4) — local-only,
`WEB_HOST=127.0.0.1` default, belum ada rencana expose ke luar localhost.

**Chart Panel 5 (menyusul setelah Phase C awal):** candlestick + MA50/100/200
overlay + volume bar/MA20 + 4 context mini-chart (DXY/S&P500/US10Y/Fear&
Greed) — item yang sempat ditunda di `plan_c.txt` keputusan #2, dikerjakan
belakangan. Semua MA dihitung **client-side di JS** (`rollingMA()`, versi
JS dari `analysis/indicators.py::rolling_ma`), bukan endpoint baru — chart
fetch `/api/asset_ohlcv` dengan `limit` lebih besar dari yang ditampilkan
(120 visible + 220 padding histori) supaya MA200 valid sejak candle
PALING KIRI yang kelihatan, bukan cuma dari titik ke-200 dan seterusnya.
Context mini-chart pakai `/api/daily_market` (sudah ada, tidak ada endpoint
baru), independen dari instrument yang dipilih.

### 5.7 `analysis/` — engine Phase B (PURE, tidak baca/tulis DB)

Terpisah dari `indicators/calc.py` (Phase A) karena beda concern & beda
cara pakai — lihat rationale lengkap di `plan_b.txt` §2. Semua modul
generic per-instrument (tidak hardcode BTC); filter instrument ada di
orchestrator (`pipeline/run_analysis.py`), bukan di sini.

- `indicators.py`: `moving_average`/`rolling_ma` (MA — beda dari
  `indicators/calc.py`, di sini WAJIB full window, None kalau data kurang),
  `ma_stack_order`, `volume_ratio`, `is_breakout_volume` (>1.5x MA),
  `is_volume_present` (>=80%, ambang "tidak sepi" saat retest).
- `sr_zones.py`: `find_swing_points` (lookback simetris ±20 hari — titik
  baru terkonfirmasi 20 hari SETELAHNYA, cocok untuk review pagi bukan
  real-time), `cluster_points` (gabung swing point ±0.5%, dibandingkan ke
  harga PALING RENDAH cluster supaya tidak "creep"), `find_touches`
  (hitung episode sentuhan, bukan per-hari), `detect_zones` (pipeline
  penuh), `zone_bucket_key` (natural key log-scale untuk UPSERT stabil
  walau batas zona geser sedikit antar-run).
- `signals.py`: `detect_signals` — breakout (close > resistance + volume)
  → retest (close > zone_lower + volume hadir) → entry/SL/TP1/R:R. Sinyal
  R:R rendah TETAP direturn (`is_valid=0`), bukan silent-drop. Tidak pernah
  menyertakan `approved` di output-nya sama sekali (desain lebih ketat
  dari sekadar "selalu 0" — field itu cuma ada di titik tulis DB).

### 5.8 `pipeline/run_analysis.py` — orchestrator Phase B
Baca histori `asset_ohlcv` → `analysis/sr_zones.py` → UPSERT `sr_zones`
(preserve `validated`/`notes`) → reload zona aktif → `analysis/
signals.py` → INSERT `trade_signals` (dedup manual by date+instrument+
signal_type+zone bounds, tidak ada UNIQUE index — lihat §6.6).
`approved` **hardcode 0** persis di titik `INSERT` ini — satu-satunya
tempat kode otomatis menulis `trade_signals`.

**Temuan penting saat eksekusi:** kolom `volume_ma20` di `asset_ohlcv`
ternyata cuma keisi untuk hari yang diproses `run_daily.py` — baris hasil
`backfill.py` (mayoritas data historis) NULL semua. Orchestrator re-derive
`volume_ma20` dari histori volume penuh via `rolling_ma()`, tidak
mengandalkan kolom tersimpan.

### 5.9 `tools/review_signal.py` — CLI approve/reject
Pola sama seperti `pipeline/add_article.py`. `approve`/`reject` **wajib
`--id` eksplisit** — tidak ada mode approve-semua (Master Plan §3: Giel
yang approve, bukan mesin). `reject` cuma set `notes` (approved tetap
0) — bedanya dengan "belum direview" (approved=0, notes=NULL) adalah
notes terisi.

---

## 6. Keputusan Desain & Rationale

### 6.1 SQLite vs Postgres vs NoSQL

**Keputusan: tetap SQLite**, termasuk untuk target backfill ~5 tahun data
harian.

- Data bersifat tabular/relational (OHLCV, snapshot bertanggal) — cocoknya
  relational, NoSQL (document DB) tidak menambah manfaat dan mempersulit
  query indikator (join, agregasi).
- Volume realistis: `asset_ohlcv` ≈ puluhan ribu baris untuk 5 tahun ×
  beberapa instrument; `daily_news` (paling gemuk) ≈ ratusan ribu baris.
  SQLite nyaman sampai jutaan baris.
- Concurrency ditangani dengan **mode DELETE** (default SQLite, dipilih
  sadar) + `busy_timeout=5000` — retry otomatis s/d 5 detik kalau ada lock
  singkat, bukan langsung `SQLITE_BUSY`. Sempat pakai mode **WAL** untuk
  tujuan yang sama, tapi WAL butuh shared-memory (`-shm`) yang **tidak
  reliable lintas boundary Windows↔WSL** — kasus nyata: DBeaver di Windows
  akses file lewat `\\wsl.localhost\...` (efektif network share/9P dari
  sisi Windows) sementara pipeline jalan native di WSL; WAL malah bikin
  `SQLITE_BUSY` yang sama, cuma ganti bentuk. DELETE + `busy_timeout` lebih
  predictable untuk pola akses campuran begini. Tulisan kita (pipeline,
  dashboard) singkat (<1 detik), jadi trade-off exclusive-lock saat commit
  kecil.
- **Trigger untuk pindah ke Postgres** (bukan sekarang): kalau dashboard
  perlu diakses banyak user concurrent, atau butuh banyak proses penulis
  bersamaan, atau butuh hosting cloud managed. Ini soal concurrency/deployment,
  bukan volume data historis.

### 6.2 Binance region-block

Binance sering diblokir DNS-level di sebagian jaringan/region. Solusi:
otomatis fallback ke CoinGecko untuk OHLC kalau Binance gagal, dan semua
endpoint Binance bisa dikonfigurasi lewat `.env`:
`BINANCE_BASE`, `BINANCE_FAPI_BASE`, `BINANCE_ENABLED`, `KASTARA_PROXY`.
Funding rate & open interest (khusus Binance futures) akan kosong kalau
Binance tidak terjangkau — ini **kondisi yang diketahui**, bukan bug.

### 6.3 Path resolusi WSL/Windows

App dijalankan di dalam WSL, tapi user kadang mengisi `KASTARA_DB_PATH`
dengan path UNC Windows (`\\wsl.localhost\<distro>\...`) — misalnya hasil
copy dari SQL client di sisi Windows. `db/connection.py` menerjemahkan path
ini ke path native Linux yang menunjuk file yang sama, supaya tidak
membuat file duplikat/sampah karena beda representasi path.

**DB sengaja ditaruh di luar folder project** (`kastara-finance-data/`,
sibling dari `kastara-finance/`), diatur lewat `KASTARA_DB_PATH` di `.env`.
Alasannya: DB berubah tiap hari (pipeline/cron), kode tidak — memisahkan
keduanya menghindarkan file data ikut ke-track/ke-commit git secara tidak
sengaja (di luar proteksi `.gitignore` yang memang sudah ada juga). Semua
resolusi path (`get_db_path()` / `_resolve_db_path()`) tetap satu-satunya
sumber kebenaran lokasi DB — tidak ada path DB yang di-hardcode di modul
lain (scrapers, pipeline, web).

### 6.4 Rule-based, bukan AI/LLM

Scoring impact berita (`news.py`) dan semua logic Phase A murni rule-based
(keyword match). Ini bukan keterbatasan teknis — ini keputusan yang dikunci
di `plan.txt` supaya sistem transparan dan predictable di lapisan data;
AI/LLM eksternal (kalau dipakai) masuk di layer *reading workspace* (Phase C),
bukan di data layer.

### 6.5 Economic Calendar — sumber tidak resmi

Master Plan §10 menyebut ForexFactory/Trading Economics sebagai sumber
economic calendar. **Trading Economics sengaja tidak dipakai** — API
resminya butuh key berbayar untuk cakupan penuh negara (guest key cuma kasih
beberapa negara sample), melanggar aturan "JANGAN pakai API berbayar".

ForexFactory sendiri tidak punya API resmi; `econ_calendar.py` memakai
endpoint JSON tidak resmi (`nfs.faireconomy.media`) yang dipakai widget
kalender ForexFactory — gratis, no-key, tapi **undocumented** dan bisa
berubah/kena rate-limit sewaktu-waktu (sudah teramati saat testing: HTTP 429
setelah beberapa kali panggil berturut-turut dalam waktu singkat). Ditangani
dengan pola yang sama seperti RSS feed: `safe_call` + `source_flags`,
gagal → `fail`, pipeline tetap lanjut. Untuk run harian (1×/hari via cron)
risiko rate-limit ini rendah — masalah 429 yang teramati murni artefak
testing manual berulang.

Keterbatasan lain sumber ini: hanya kasih rolling window "minggu ini" (tidak
ada histori atau minggu depan), dan tidak menyediakan kolom `actual` (hasil
rilis) — kolom itu tetap `NULL` dari scraper ini.

### 6.6 `trade_signals` — dedup tanpa UNIQUE index

Beda dengan `daily_news`/`econ_calendar` (UNIQUE index, `INSERT OR IGNORE`),
`trade_signals` **sengaja tidak diberi UNIQUE index** (dikunci di
`plan_b.txt` §5) — event breakout/retest yang exact match di tanggal yang
sama secara alami jarang berulang, jadi manfaat UNIQUE index kecil
dibanding kerumitan mendefinisikan natural key yang tepat untuk data
append-only seperti ini. Dedup dicek manual di
`pipeline/run_analysis.py::insert_signal_dedup()` — SELECT dulu by
`(date, instrument, signal_type, zone_lower, zone_upper)` sebelum INSERT.
Volume `trade_signals` jauh lebih kecil dari `daily_news` (ratusan per
instrument vs ratusan-ribu), jadi 1 SELECT tambahan per sinyal bukan
masalah performa.

### 6.7 `sr_zones` — UPSERT tanpa kolom bucket-key tersimpan

Natural key untuk UPSERT `sr_zones` (`zone_bucket_key()` di
`analysis/sr_zones.py`) **dihitung ulang di Python setiap saat**, bukan
disimpan sebagai kolom di DB. Alasan: skema `sr_zones` sudah dikunci sejak
Phase A (`zone_lower`, `zone_upper`, tanpa kolom tambahan) dan menambah
kolom baru berarti mengubah skema yang sudah ada — dihindari selama
alternatif tanpa migrasi (hitung ulang saat lookup, biaya kecil karena
jumlah zona per instrument masih ratusan) sudah cukup. Kalau nanti jumlah
zona per instrument membengkak drastis (banyak instrument, Phase F+), ini
kandidat pertama untuk dioptimasi (mis. kolom generated tersimpan +
index).

### 6.8 `pipeline.backfill.backfill()` — `preview_only` (ekstensi Phase C)

CLI backfill (Phase A) pakai `input()` untuk konfirmasi commit — ini akan
**hang** kalau dipanggil dari request web (tidak ada stdin). Daripada
duplikat logic fetch+dedup-check di `web/app.py` (melanggar prinsip reuse),
`backfill()` diberi parameter baru `preview_only: bool = False`: return
persis setelah preview dihitung, SEBELUM prompt `input()` maupun commit.
Default `False` — CLI dan semua test lama tidak berubah sama sekali;
Panel 1 dashboard manggil dengan `preview_only=True` (utk tombol Preview)
lalu `assume_yes=True` (utk tombol Confirm & Commit, 2 request terpisah,
re-fetch data — diterima sebagai trade-off karena tiap fetch murah, lihat
§6.1).

### 6.9 Bug ditemukan saat verifikasi browser: `/api/news` tidak SELECT `id`

Endpoint `/api/news` (Phase 1, read-only) tidak pernah butuh kolom `id`
sebelumnya. Saat Panel 2 nambah tombol "flag key trigger" (butuh `id` buat
tahu row mana yang di-update), tombolnya diam-diam tidak muncul sama
sekali — `r.id` selalu `undefined` di JS. Ditemukan justru karena
verifikasi dilakukan LANGSUNG di browser (bukan cuma pytest, yang tidak
akan menangkap bug ini karena tidak ada test untuk response shape endpoint
JSON lama). Diperbaiki dengan menambah `id` ke `SELECT`. Pelajaran yang
menegaskan prinsip `plan_c.txt` §5: "diverifikasi via preview browser,
bukan cuma pytest."

### 6.10 `hy_credit_spread` — contoh nyata "series FRED bisa dibatasi provider"

`scrapers/macro_fred.py` sudah wanti-wanti sejak Phase A: *"Series id FRED
kadang berubah/deprecate... jangan asumsi."* Ini kejadian konkretnya:
`hy_credit_spread` (`BAMLH0A0HYM2`) cuma punya 787 baris di DB (vs ~4.100 di
`dxy_close`/`vix_close`) — awalnya diduga gap backfill, ternyata **bukan**.
Dicek langsung ke metadata FRED (`/fred/series`): pemilik data (ICE Data
Indices) membatasi series ini ke **rolling 3-tahun** karena lisensi dengan
FRED (*"Starting in April 2026, this series will only include 3 years of
observations"*) — histori lebih panjang cuma tersedia langsung dari ICE
Data (berbayar), di luar scope "no paid API". Dikonfirmasi lewat re-run
`backfill.py`: 0 baris baru (DB sudah punya semua yang FRED sediakan).
Tidak ada tindakan lanjut — ini batas sumber data, bukan bug.

### 6.11 `scrapers/positioning.py` — Cloudflare butuh header browser-realistis

Riset Phase D (`plan_d.txt`) sempat menyimpulkan farside.co.uk (BTC ETF
flow) "bisa di-scrape" berdasar 1x tes `curl` sukses (200, tabel HTML
lengkap). Begitu diimplementasi pakai `requests` (library yang benar-benar
dipakai scraper) dengan `scrapers/base.py::DEFAULT_HEADERS` bawaan (UA bot
jujur `kastara-finance/0.1` + `Accept: application/json`), responsnya malah
halaman **Cloudflare "Just a moment..."** (bot-challenge), bukan tabel.
`curl` lolos karena header/TLS fingerprint-nya kebetulan mirip browser;
`requests` dengan header generik tidak.

Fix: kirim header browser-realistis KHUSUS untuk request ini (UA Chrome +
`Accept: text/html...` + `Accept-Language`), override `DEFAULT_HEADERS` via
parameter `headers=` di `http_get()` — bukan ubah `DEFAULT_HEADERS` global
(itu dipakai scraper JSON lain yang justru butuh `Accept: application/json`
jujur). Pelajaran: kalau riset kelayakan scrape cuma dites lewat `curl`
manual, hasilnya belum tentu representatif untuk request yang benar-benar
dikirim library HTTP Python — validasi ulang pakai kode yang sama persis
yang bakal jalan di produksi, bukan proxy tool yang beda fingerprint.

CFTC COT sebaliknya: dites langsung pakai Socrata API (`publicreporting.
cftc.gov/resource/<id>.json`), gratis, TANPA API key — dikonfirmasi bekerja
persis seperti riset awal, tidak ada kejutan.

### 6.12 Telegram Daily Briefing — PUSH manual, sengaja TIDAK nempel `run_daily`

Master Plan §5/§8 (Phase E) menyebut "push daily briefing" seolah itu
proses otomatis harian seperti scraper lain. Tapi isi briefing (4 Lensa,
Signal approved) baru lengkap SETELAH Giel selesai Panel 4-6 (~07:20) —
`run_daily` jalan jam 07:00, jauh sebelum itu. Kalau `compose_daily_
briefing()` dipanggil otomatis di akhir `run_daily`, isinya SELALU kosong
di bagian yang paling penting (lensa & sinyal), padahal `pull data` dan
`analisa manual Giel` adalah dua peristiwa terpisah waktu.

Keputusan: `pipeline/send_briefing.py` adalah AKSI TERPISAH (CLI + tombol
Panel 6), dipicu Giel sendiri kapan siap — bukan langkah otomatis di
`pipeline/run_daily.py`. Ini konsisten dengan prinsip "mesin merakit, Giel
memprediksi": `compose_daily_briefing()` cuma merakit teks dari row yang
SUDAH ada di DB (ditulis manual oleh Giel di Panel 4-6), tidak pernah
menunggu/polling data yang belum ada.

**Pola test berbeda dari scraper lain (sengaja):** semua scraper
(`scrapers/*.py`) di-test dengan LIVE network call (lihat `test_econ_
calendar.py`, `test_positioning.py`) karena itu operasi READ — aman
diulang berkali-kali. `notify/telegram.py` adalah operasi SEND (push
pesan ke chat asli) — kalau test-nya live juga, tiap `pytest` run bakal
benar-benar ngirim pesan ke Telegram Giel. Jadi `tests/test_notify_
telegram.py` di-mock pakai `monkeypatch` (pertama kalinya test suite ini
pakai mocking) — satu-satunya pengecualian yang disengaja dari kebiasaan
"test scraper pakai network asli".

### 6.13 Bug ditemukan saat setup asli: `notify/telegram.py` tidak `load_dotenv()` sendiri

Semua modul yang baca env var (`scrapers/macro_fred.py` via `FRED_API_KEY`,
dll) selama ini "gratis" dapat `.env` ter-load karena tiap entry point
(`run_daily`, `backfill`, `web.app`) import `db.connection` duluan, dan
`db/connection.py` yang panggil `load_dotenv()`. `notify/telegram.py`
didesain juga bisa dijalankan BERDIRI SENDIRI (`python -m notify.telegram`
— cara resmi ambil `chat_id` pertama kali, lihat README), tapi modul ini
tidak import `db.connection` sama sekali -> `.env` tidak pernah ke-load,
`os.getenv("TELEGRAM_BOT_TOKEN")` selalu kosong walau sudah diisi di `.env`.

Ketemu pas Giel benar-benar setup token asli (bukan di test — testnya pakai
`token=`/`chat_id=` eksplisit jadi tidak kena masalah ini). Fix: `notify/
telegram.py` panggil `load_dotenv()` sendiri di level modul, tidak
bergantung pada modul lain di-import duluan.

**Bug kedua (bukan kode, tapi konfigurasi)**: nilai `TELEGRAM_CHAT_ID` yang
sempat diisi Giel salah 1 digit dari chat_id asli (`...443` vs `...442`
yang benar) — baru ketahuan setelah `get_latest_chat_id()` dipanggil
SETELAH Giel benar-benar kirim pesan ke bot (chat_id yang valid cuma bisa
didapat dari update asli, bukan ditebak/disalin dari sumber lain). Pesan
error Telegram `"Bad Request: chat not found"` jadi sinyal diagnostik yang
tepat untuk kasus ini — sudah divalidasi cocok.