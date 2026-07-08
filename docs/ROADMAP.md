# Kastara Finance — Roadmap

> Sumber acuan: **[Master Plan.md](Master%20Plan.md)** (v1.4, dokumen strategi
> lengkap) → diturunkan jadi **[plan.txt](../plan.txt)** (scope eksekusi Phase
> A yang benar-benar dikerjakan) + keputusan tambahan lewat sesi eksekusi
> (Phase 1, dashboard). Dokumen ini dokumen hidup — update status di sini tiap
> phase baru selesai atau tiap kali ada temuan gap baru terhadap Master Plan.

## Status Ringkas

| Phase | Nama | Status |
|---|---|---|
| **A** | Database & Scraper (data layer) | ✅ **Selesai penuh** — sesuai `plan.txt` **dan** checklist Master Plan §10 (lihat [status](#anchor-gap-phase-a)); cron daemon butuh 1 langkah manual sudo, lihat catatan |
| **1** | Dashboard read-only (Flask) | 🟡 **Selesai sebagai subset kecil** — bukan 6-panel Phase C (lihat [breakdown](#anchor-panel-breakdown)) |
| **B** | S&R detection, breakout/retest engine | ⬜ Belum mulai |
| **C** | Dashboard/UI penuh (6 panel, input manual, workspace) | 🟡 Sebagian kecil (lihat [breakdown](#anchor-panel-breakdown)) |
| **D** | Forward layer (FedWatch, COT, policy) | ⬜ Belum mulai — schema (3 tabel) sudah siap, tinggal isi logic |
| **E** | Telegram bot | ⬜ Belum mulai |
| **F+** | Multi-aset expansion | ⬜ Belum mulai |

---

<a id="anchor-cross-check"></a>
## 🔍 Cross-check vs Master Plan v1.4

Ditulis setelah `Master Plan.md` (dokumen strategi penuh) dimasukkan ke
`docs/` — sebelumnya eksekusi hanya mengacu ke `plan.txt` (turunan scope
Phase A yang lebih sempit). Hasil pembacaan ulang:

### ✅ Konsisten
- 11 tabel utama (Section 4 Master Plan) — match persis dengan `schema.sql`.
- Tech stack (Section 5): SQLite dev → Postgres kalau scale/multi-device,
  Flask, chart custom (bukan TradingView) — semua match.
- Prinsip inti: `source_flags`, rule-based scoring (bukan AI), tanpa
  execution/trading logic, tanpa kode AGPL — semua konsisten.
- Manual backfill tool (Section 4.1: preview → confirm → commit) — match
  persis dengan `pipeline/backfill.py`.

<a id="anchor-gap-phase-a"></a>
### ✅ Gap checklist Phase A (Master Plan §10) — sudah ditutup

`plan.txt` (yang dieksekusi lebih dulu) sengaja mempersempit scope Phase A.
Master Plan §10 mendefinisikan Phase A lebih luas; tiga item berikut sempat
jadi gap, sekarang sudah dikerjakan:

1. **Scraper Economic Calendar** ✅ — `scrapers/econ_calendar.py`, sumber
   ForexFactory (endpoint JSON tidak resmi, gratis no-key; **Trading
   Economics sengaja tidak dipakai** karena API resminya butuh key berbayar
   untuk cakupan penuh — melanggar aturan "no paid API"). UPSERT by
   `(event_date, event_name, country)` ke `econ_calendar`, di-integrasikan ke
   `pipeline/run_daily.py`. Endpoint ini tidak resmi/undocumented — bisa
   berubah/rate-limit sewaktu-waktu; sudah tahan gagal (`source_flags`,
   tidak crash pipeline). Kolom `actual` tetap NULL dari scraper ini (sumber
   tidak menyediakan data hasil rilis).
2. **3 tabel forward-layer** ✅ — `expectations`, `positioning`,
   `policy_tracker` (Section 4.2) sudah ditambah ke `schema.sql` (struktur
   saja, sesuai Master Plan §10). Diisi nanti saat Phase D beneran mulai.
3. **Cron job otomatis 00:00 WIB** 🟡 — crontab per-user sudah **terinstall
   dan diverifikasi jalan benar** (disimulasikan persis environment cron:
   `env -i` + `/bin/sh`, exit 0, log tertulis ke `logs/run.log`). Yang
   **belum**: cron **daemon**-nya sendiri butuh `sudo service cron start`
   (butuh password interaktif — di luar kendali eksekusi otomatis, harus
   dijalankan manual satu kali oleh Giel). Lihat instruksi lengkap di
   [README §5](../README.md#5-otomatisasi-cron).

Total tabel sekarang **14** (11 Phase A + 3 forward-layer), naik dari 11.

### Deviasi kecil yang disengaja (bukan bug)

Master Plan menulis kolom `date` di `daily_news` (dan tabel lain) sebagai
*"FOREIGN KEY → daily_market"*. Implementasi di `schema.sql` **tidak**
menulis ini sebagai `FOREIGN KEY` SQL sungguhan — hanya relasi by-convention
(kolom `date` yang cocok). Ini konsisten dengan `plan.txt` (yang memang tidak
mendefinisikan FK literal), jadi dibiarkan — dicatat di sini supaya jelas ini
pilihan sadar, bukan sesuatu yang terlewat.

---

## ✅ Phase A — Database & Scraper (selesai penuh)

**Selesai sesuai scope `plan.txt` DAN checklist Master Plan §10**: SQLite +
14 tabel (11 Phase A + 3 forward-layer struktur), 5 scraper modular (crypto,
macro FRED, macro yfinance, news, economic calendar), pipeline harian
idempotent, backfill tool dengan preview-before-commit, cron terinstall
(daemon butuh 1 langkah manual — lihat [gap](#anchor-gap-phase-a) di atas).

**Deliverable:**
- `db/schema.sql` — 14 tabel + index untuk skala 5-tahun.
- `scrapers/{crypto,macro_fred,macro_yf,news,econ_calendar}.py` — tiap
  sumber independen, tahan API-fail (`source_flags`).
- `pipeline/run_daily.py` — orchestrator, UPSERT idempotent, termasuk
  economic calendar.
- `pipeline/backfill.py` — historical fetch, preview wajib sebelum commit.
- `indicators/calc.py` — `net_liquidity`, `volume_ma20`.
- Crontab per-user terinstall (`0 0 * * *`, TZ sistem sudah Asia/Jakarta =
  WIB, tidak perlu konversi).
- 29 test, semua hijau.

**Definition of Done** — semua kriteria di `plan.txt §8` **dan** checklist
Master Plan §10 terpenuhi.

---

## 🟡 Phase 1 — Dashboard Read-Only (subset kecil dari Phase C)

Tidak ada di `plan.txt` asli (yang menaruh dashboard di Phase C), tapi
dikerjakan lebih dulu atas permintaan langsung karena dibutuhkan segera
untuk verifikasi visual data yang sudah masuk.

**Deliverable:**
- `web/app.py` — Flask, endpoint JSON read-only (`/api/latest`,
  `/api/daily_market`, `/api/asset_ohlcv`, `/api/news`, `/api/assets`,
  `/api/health`). **Tidak menulis DB** — pipeline tetap satu-satunya penulis.
- `web/templates/index.html` — single-page UI (snapshot cards, status
  `source_flags`, chart harga SVG per instrument, tabel berita dengan filter
  impact).
- Verified end-to-end via preview: semua endpoint 200, chart render dari data
  backfill, filter HIGH/MED/LOW berfungsi.

<a id="anchor-panel-breakdown"></a>
### Catatan penamaan: Phase 1 vs Phase C (6 panel)

`plan.txt §9` menyebut "Dashboard/UI/Flask" sebagai **Phase C**. Setelah
membaca Section 6 Master Plan (spek 6-panel lengkap), yang sudah dibangun di
Phase 1 ternyata **irisan kecil** — bukan setara satu panel penuh pun:

| Panel (Master Plan §6) | Status di dashboard Phase 1 |
|---|---|
| Panel 1 — Data Snapshot | 🟡 Sebagian: cards + `source_flags` ada; tombol Manual Backfill tidak ada |
| Panel 2 — News Briefing | 🟡 Sebagian: list + impact badge ada; tombol flag manual "key trigger" & "+ Add Manual Article" tidak ada |
| Panel 3 — Forward Panel | ⬜ Tidak ada (butuh tabel Phase D dulu: `expectations`/`positioning`/`policy_tracker`) |
| Panel 4 — Reading Workspace | ⬜ Tidak ada (butuh form input 4 lensa) |
| Panel 5 — Chart + Technical Analysis | 🟡 Sebagian: chart harga polos ada; MA overlay, S&R zone overlay, approve/reject signal tidak ada (butuh Phase B) |
| Panel 6 — Synthesis | ⬜ Tidak ada (butuh `prediction_log` capture + skor prediksi) |

Jadi status Phase C ditandai 🟡 **sebagian kecil**, bukan sekadar "belum
selesai" generik — supaya jelas seberapa jauh sisa kerjanya.

---

## ⬜ Phase B — S&R Detection & Breakout/Retest Engine

**Belum mulai.** Scope (dari `plan.txt`, garis besar — detail akan dikunci di
plan turunan Phase B saat mulai):
- Deteksi support/resistance zone dari histori `asset_ohlcv` (semi-otomatis,
  divalidasi manual → tabel `sr_zones` sudah siap strukturnya).
- Signal breakout/retest → tulis ke `trade_signals` (struktur sudah ada).
- **Bukan** execution/trading logic — tetap suggestion/data layer, keputusan
  akhir tetap manual (`giel_approved` di `trade_signals`).

**Prasyarat:** histori `asset_ohlcv` cukup panjang untuk deteksi zone yang
reliable — selaras dengan rencana backfill 5 tahun yang sedang berjalan.

---

## 🟡 Phase C — Dashboard/UI Penuh

**Sebagian selesai** (lihat Phase 1). `manual_articles` sudah punya jalur
isi via **CLI** (`pipeline/add_article.py`, di luar dashboard — lihat
[README](../README.md#artikel-manual-riset-historis)); sisa scope dashboard:
- Form input manual **di dashboard** (bukan CLI) untuk `reading_workspace`
  (catatan analisis harian), tombol "+ Add Manual Article" di Panel 2
  (setara CLI tapi lewat UI), `trading_journal` (record hasil trading).
- Kemungkinan write-back dari UI (saat ini dashboard 100% read-only).
- Visualisasi tambahan: overlay `sr_zones` di chart, tampilan
  `econ_calendar` (event mendatang).

---

## ⬜ Phase D — Forward Layer

**Belum mulai.** Scope (Master Plan §4.2, 3 stage): data
**masa depan/forward-looking** — FedWatch probability & Dot Plot
(Expectations), COT report & ETF/SBN flow (Positioning), pernyataan
pembuat kebijakan dengan `literal_statement` vs `giel_inference` terpisah
tegas (Policy Tracker). Juga mengisi `econ_calendar` dan
`asset_context_weight` (pembobotan driver per aset) yang strukturnya sudah
disiapkan sejak Phase A.

**Prasyarat schema:** ✅ sudah siap — 3 tabel (`expectations`, `positioning`,
`policy_tracker`) sudah ditambah ke `schema.sql` sejak Phase A (lihat
[Cross-check](#anchor-cross-check)). Phase D tinggal isi scraper/logic-nya,
bukan mulai dari bikin schema.

---

## ⬜ Phase E — Telegram Bot

**Belum mulai.** Scope: notifikasi push (mis. `daily_news` impact HIGH,
`trade_signals` baru) lewat Telegram, sebagai alternatif/pelengkap dashboard.

---

## ⬜ Phase F+ — Multi-Aset Expansion

**Belum mulai.** Scope: perluas cakupan instrument di luar 6 yang ada saat
ini (BTC, SP500, IHSG, GOLD, USDIDR, USDJPY) — mis. altcoin lain, saham
individual, komoditas tambahan. Kemungkinan di titik ini juga saat SQLite
ditinjau ulang kalau volume/concurrency berubah signifikan (lihat
[ARCHITECTURE.md §6.1](ARCHITECTURE.md#61-sqlite-vs-postgres-vs-nosql)).

---

## Backlog Kecil (tidak terikat 1 phase, bisa dikerjakan kapan saja)

Hal-hal konkret yang sudah teridentifikasi selama Phase A/1 tapi belum
dikerjakan — dicatat di sini supaya tidak hilang, bukan komitmen jadwal:

- [x] ~~Cron otomatis untuk `run_daily`~~ — crontab terinstall & diverifikasi
      (lihat [gap checklist](#anchor-gap-phase-a)). **Sisa:** jalankan
      `sudo service cron start` sekali (butuh password interaktif, tidak bisa
      dieksekusi otomatis) + opsional `[boot] command=service cron start` di
      `/etc/wsl.conf` biar cron ikut nyala tiap kali instance WSL start.
- [x] ~~Scraper Economic Calendar~~ — `scrapers/econ_calendar.py` selesai,
      terintegrasi ke `run_daily`, 6 test hijau.
- [x] ~~3 tabel forward-layer~~ — `expectations`/`positioning`/
      `policy_tracker` sudah di `schema.sql`.
- [ ] **Backfill penuh 5 tahun** untuk semua instrument (`BTC`, `SP500`,
      `IHSG`, `GOLD`, `USDIDR`, `USDJPY`, + series FRED kalau
      `FRED_API_KEY` sudah diisi) — sedang berjalan bertahap oleh user.
- [ ] Index/monitoring ukuran DB berkala saat volume bertambah (sanity check,
      bukan berarti perlu migrasi — lihat rationale SQLite di
      ARCHITECTURE.md).
- [ ] Evaluasi ulang daftar RSS feed di `scrapers/news.py` — beberapa
      (Reuters, Bisnis.com, Kontan) sempat gagal saat verifikasi; cek apakah
      URL sudah pindah/berubah.
- [ ] Backfill/isi `econ_calendar` untuk event yang sudah lewat kalau perlu
      histori kalender (scraper ini hanya kasih rolling window "minggu ini",
      bukan sumber histori).
- [x] ~~`manual_articles` CLI~~ — `pipeline/add_article.py` selesai (add +
      list/search by tag/date-range/keyword), 5 test hijau. Dipakai buat
      riset historis (mis. dari 2010) yang RSS tidak bisa jangkau.

**Dievaluasi, sengaja tidak dikerjakan:**
- **NewsData.io** — dicek langsung: sentiment analysis **cuma tersedia di
  tier Professional/Corporate (berbayar)**, bukan tier gratis seperti yang
  awalnya dikira. Historical archive (10 tahun) juga fitur berbayar. Tier
  gratisnya (200 credit/hari) cuma jadi agregator RSS tambahan tanpa
  sentiment asli — dinilai tidak worth effort integrasi vs nilai tambahnya.
  Diputuskan **skip**.
- **NewsAPI.org** — free tier "non-commercial only" (konflik dengan rencana
  monetisasi Phase 2/3 di Master Plan), dan historical depth cuma ~1 bulan.
  Skip.

## Prinsip Perubahan Roadmap

Sesuai `plan.txt`: **jangan lompat phase tanpa instruksi baru.** Kalau ada
kebutuhan mendesak di luar urutan (seperti Phase 1 kemarin), itu boleh — tapi
harus tercatat di sini dengan jelas kenapa keluar urutan, supaya roadmap tetap
mencerminkan kenyataan, bukan rencana ideal yang sudah basi.
