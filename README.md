# Kastara Finance — Phase A (Database & Scraper)

Data layer untuk Kastara Finance. Phase A = **kumpulkan data mentah** ke SQLite
lokal dari sumber-sumber gratis (no paid API). Belum ada trading/signal/UI —
itu Phase B+.

> Scope dikunci di `plan.txt`. Phase A HANYA data layer.

📄 **Dokumen lengkap ada di [`docs/`](docs/):**
[ARCHITECTURE.md](docs/ARCHITECTURE.md) (desain teknis & rationale),
[FLOW.md](docs/FLOW.md) (alur data, diagram),
[ROADMAP.md](docs/ROADMAP.md) (status tiap phase).

---

## 1. Apa yang dikerjakan

- **SQLite** `kastara-finance.db` dengan 14 tabel (`db/schema.sql`) — 11
  tabel Phase A + 3 tabel forward-layer (struktur, diisi saat Phase D).
- **5 scraper** modular (tiap source bisa jalan sendiri):
  - `scrapers/crypto.py` — CoinGecko + Binance + Alternative.me (BTC OHLCV,
    dominance, funding, OI, Fear & Greed). *Binance ke-block? otomatis fallback
    CoinGecko untuk OHLC.*
  - `scrapers/macro_yf.py` — yfinance (S&P 500, IHSG, Gold, USD/IDR, USD/JPY).
  - `scrapers/macro_fred.py` — FRED (DXY, US10Y, VIX, WALCL, RRP, TGA, HY spread).
    Butuh `FRED_API_KEY`.
  - `scrapers/news.py` — RSS (CNBC, Fed, CNBC Indonesia, dll) + scoring
    rule-based HIGH/MED/LOW (bukan AI).
  - `scrapers/econ_calendar.py` — ForexFactory (event ekonomi masa depan:
    FOMC/CPI/dll), endpoint JSON gratis tidak resmi.
- **Pipeline** `pipeline/run_daily.py` — orchestrator harian, idempotent (UPSERT).
- **Backfill** `pipeline/backfill.py` — tarik data historis, preview-before-commit.
- **Indikator** `indicators/calc.py` — `net_liquidity`, `volume_ma20`.

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

# 3. konfigurasi (opsional, hanya untuk FRED)
cp .env.example .env
# edit .env, isi FRED_API_KEY (gratis: https://fred.stlouisfed.org/docs/api/api_key.html)
```

FRED opsional — tanpa key, series FRED akan di-`skip` (bukan error), sisanya
tetap jalan.

---

## 3. Cara pakai

### Inisialisasi DB (otomatis dipanggil pipeline, tapi bisa manual)
```bash
python -m db.connection
# -> bikin kastara-finance.db + 14 tabel
```

### Jalankan pipeline harian
```bash
python -m pipeline.run_daily              # tanggal hari ini (WIB)
python -m pipeline.run_daily 2026-06-24   # tanggal tertentu
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

### Dashboard web (read-only)
```bash
python -m web.app
# buka http://127.0.0.1:5000
```
Dashboard Flask kecil di atas DB yang sama (HANYA baca — pipeline tetap satu-
satunya penulis). Menampilkan: snapshot pasar, status `source_flags`, chart harga
per instrument, dan berita dengan badge impact. Endpoint JSON: `/api/latest`,
`/api/daily_market`, `/api/asset_ohlcv?instrument=BTC`, `/api/news`, `/api/assets`,
`/api/health`. Host/port bisa diatur via `WEB_HOST` / `WEB_PORT`.

### Test
```bash
python -m pytest -q
```

---

## 4. Skema data (ringkas)

| Tabel | Diisi Phase A? | Isi |
|---|---|---|
| `daily_market` | ✅ | 1 row/tanggal — konteks makro global (BTC, DXY, S&P, IHSG, Fear&Greed, net liquidity, dll) + `source_flags` JSON |
| `asset_ohlcv` | ✅ | 1 row/aset/tanggal — OHLCV universal + `volume_ma20` |
| `daily_news` | ✅ | headline + `impact_level` (HIGH/MED/LOW) |
| `econ_calendar`, `reading_workspace`, `trade_signals`, `sr_zones`, `manual_articles`, `trading_journal`, `prediction_log`, `asset_context_weight` | struktur saja | dipakai Phase B+ |

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
- **`SQLITE_BUSY` / database is locked**: DB pakai mode **WAL** + `busy_timeout`
  (lihat `db/connection.py`), jadi SQL client (DBeaver dll) bisa baca sambil
  pipeline nulis. Kalau masih ke-lock: pastikan client-mu auto-commit dan tidak
  menahan transaksi tulis. File sidecar `*.db-wal` / `*.db-shm` itu normal.
- **`KASTARA_DB_PATH` di Windows/WSL**: app jalan di dalam WSL. Boleh isi path
  Windows UNC (`\\wsl.localhost\<distro>\home\...`) — otomatis diterjemahkan ke
  path native Linux (file yang sama). Default cukup `kastara-finance.db`.
- **SQLite vs Postgres/NoSQL**: untuk backfill sampai ~5 tahun data harian,
  SQLite masih pas — datanya tabular (cocok relational, bukan NoSQL) dan
  volumenya (puluhan ribu baris `asset_ohlcv`, ratusan ribu `daily_news`) jauh
  di bawah kapasitas SQLite. Sudah ditambah index untuk query range-tanggal
  di skala itu: `idx_asset_ohlcv_instrument_date`, `idx_daily_news_dedup`
  (juga menegakkan dedup by headline di level DB), `idx_daily_news_impact_date`.
  Pindah ke Postgres baru relevan kalau nanti multi-user concurrent atau butuh
  hosting cloud managed — bukan soal volume data historisnya.
- **RSS feed bisa mati/pindah.** Daftar feed ada di `scrapers/news.py`
  (`RSS_FEEDS`) — gampang ditambah/ganti. Feed mati ditandai `fail`, di-skip.
- **FRED series id kadang berubah.** Lihat `scrapers/macro_fred.py` (`SERIES`).
  Series gagal ditandai `fail` per-series, pipeline lanjut.
- **Tidak ada API key di source code.** Semua via `.env` + `python-dotenv`.
- **Tidak ada kode dari repo AGPL** (OpenBB dll) yang disalin ke project ini.

---

*Phase A dari Kastara Finance Master Plan v1.4. Phase berikutnya = plan terpisah.*
