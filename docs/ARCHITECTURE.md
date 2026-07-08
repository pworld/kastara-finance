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
│   ├── macro_fred.py         # FRED (DXY, US10Y, VIX, WALCL, RRP, TGA, HY)
│   ├── macro_yf.py           # yfinance (SP500, IHSG, Gold, USD/IDR, USD/JPY)
│   ├── news.py               # RSS + scoring rule-based (bukan AI)
│   └── econ_calendar.py      # ForexFactory calendar (event masa depan)
├── pipeline/
│   ├── run_daily.py          # orchestrator harian, UPSERT idempotent
│   └── backfill.py           # tarik historis, preview-before-commit
├── indicators/
│   └── calc.py               # net_liquidity, volume_ma20 (calculated fields)
├── web/                      # dashboard read-only (Phase 1)
│   ├── app.py                 # Flask, endpoint JSON + halaman
│   └── templates/index.html   # UI single-page, tanpa build step/CDN
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

### 4.1 Tabel aktif (Phase A)

| Tabel | Grain | Isi |
|---|---|---|
| `daily_market` | 1 baris / tanggal | Snapshot makro global: BTC, DXY, S&P500, IHSG, VIX, Fear&Greed, net liquidity, dll + `source_flags` (JSON status tiap API) |
| `asset_ohlcv` | 1 baris / (tanggal, instrument) | OHLCV universal semua aset yang tradeable: BTC, SP500, IHSG, GOLD, USDIDR, USDJPY |
| `daily_news` | 1 baris / headline unik | Headline RSS + `impact_level` (HIGH/MED/LOW, rule-based) |
| `econ_calendar` | 1 baris / event unik (`event_date`+`event_name`+`country`) | Event ekonomi masa depan (FOMC/CPI/dll) dari ForexFactory, UPSERT (forecast bisa berubah mendekati rilis) |

### 4.2 Tabel struktur-saja (Phase B/D)

`reading_workspace`, `trade_signals`, `sr_zones`, `manual_articles`,
`trading_journal`, `prediction_log`, `asset_context_weight` (Phase B/C) +
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

### 5.6 `web/app.py` — dashboard (read-only)
Flask kecil di atas DB yang sama. **Tidak pernah menulis** — pipeline tetap
satu-satunya penulis. Endpoint: `/api/latest`, `/api/daily_market`,
`/api/asset_ohlcv`, `/api/news`, `/api/assets`, `/api/health`, plus halaman
`/` (single-page, JS vanilla, tanpa build step).

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
