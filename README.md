# Kastara Finance — Phase A + B (Data Layer + Analysis Engine)

**Phase A** (selesai): **kumpulkan data mentah** ke SQLite lokal dari
sumber-sumber gratis (no paid API). **Phase B** (selesai untuk BTC): deteksi
zona S&R + sinyal breakout/retest + R:R calculator dari histori
`asset_ohlcv` — tetap **suggestion, bukan execution/trading logic**;
keputusan akhir tetap manual (`approved`, direview via
`tools/review_signal.py`).

> Scope dikunci di `plan.txt` (Phase A) dan `plan_b.txt` (Phase B).

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
- **Backfill** `pipeline/backfill.py` — tarik data historis (BTC/macro), preview-before-commit.
- **Manual article** `pipeline/add_article.py` — isi `manual_articles` untuk riset
  historis (RSS tidak bisa backfill — lihat [Artikel manual](#artikel-manual-riset-historis)).
- **Indikator Phase A** `indicators/calc.py` — `net_liquidity`, `volume_ma20`.
- **Analysis engine Phase B** (`analysis/`, BTC dulu — lihat
  [plan_b.txt](plan_b.txt)):
  - `analysis/sr_zones.py` — deteksi zona support/resistance (swing
    high/low + clustering + touch count).
  - `analysis/signals.py` — deteksi breakout/retest + R:R calculator.
  - `pipeline/run_analysis.py` — orchestrator, tulis ke `sr_zones` +
    `trade_signals`. **Suggestion only** — `approved` selalu 0 dari kode.
  - `tools/review_signal.py` — CLI approve/reject sinyal by id eksplisit.
  - `pipeline/seed_context_weight.py` — seed pembobotan driver per aset.

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

### Analysis engine (Phase B — S&R + breakout/retest, BTC)

```bash
# Jalankan deteksi zona S&R + sinyal breakout/retest untuk BTC
python -m pipeline.run_analysis
```
Idempotent (re-run tidak duplikat zona/sinyal, tidak menimpa
`validated`/`notes` yang sudah direview manual). **Manual trigger**
untuk sekarang, belum di-cron (lokal cuma dev — lihat [plan_b.txt](plan_b.txt) §7.6).

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

| Tabel | Diisi? | Isi |
|---|---|---|
| `daily_market` | ✅ otomatis | 1 row/tanggal — konteks makro global (BTC, DXY, S&P, IHSG, Fear&Greed, net liquidity, dll) + `source_flags` JSON |
| `asset_ohlcv` | ✅ otomatis | 1 row/aset/tanggal — OHLCV universal + `volume_ma20` |
| `daily_news` | ✅ otomatis | headline + `impact_level` (HIGH/MED/LOW) |
| `econ_calendar` | ✅ otomatis | event ekonomi masa depan (ForexFactory), UPSERT by natural key |
| `manual_articles` | 🖊️ manual (ada tool) | riset historis — isi via `python -m pipeline.add_article`, RSS tidak bisa backfill |
| `reading_workspace`, `trade_signals`, `sr_zones`, `trading_journal`, `prediction_log`, `asset_context_weight`, `expectations`, `positioning`, `policy_tracker` | ⬜ struktur saja | dipakai Phase B/C/D |

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
- **RSS feed bisa mati/pindah.** Daftar feed ada di `scrapers/news.py`
  (`RSS_FEEDS`) — gampang ditambah/ganti. Feed mati ditandai `fail`, di-skip.
- **FRED series id kadang berubah.** Lihat `scrapers/macro_fred.py` (`SERIES`).
  Series gagal ditandai `fail` per-series, pipeline lanjut.
- **Tidak ada API key di source code.** Semua via `.env` + `python-dotenv`.
- **Tidak ada kode dari repo AGPL** (OpenBB dll) yang disalin ke project ini.

---

*Phase A dari Kastara Finance Master Plan v1.4. Phase berikutnya = plan terpisah.*
