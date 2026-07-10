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
| **1** | Dashboard read-only (Flask) | ✅ Selesai — jadi fondasi Panel 1/2/5 di Phase C |
| **B** | S&R detection, breakout/retest engine | ✅ **Selesai untuk BTC** — `plan_b.txt` (dihapus setelah selesai) dieksekusi penuh, 46 test baru, diverifikasi data asli |
| **C** | Dashboard/UI penuh (6 panel, write-enabled) | ✅ **Selesai** — `plan_c.txt` (dihapus setelah selesai) dieksekusi penuh, semua panel diverifikasi via browser |
| **D** | Forward layer (FedWatch, COT, policy) | ✅ **Selesai** — `plan_d.txt` (dihapus setelah selesai) dieksekusi penuh, COT+ETF flow otomatis, Expectations/SBN manual, Disonansi flag jalan |
| **E** | Telegram bot | ✅ **Selesai (push satu arah)** — `plan_e.txt` (dihapus setelah selesai) dieksekusi penuh, Daily Briefing manual (CLI + tombol Panel 6); bot commands dua-arah ditunda ke backlog |
| **F+** | Multi-aset expansion | 🟡 **GOLD/SP500/IHSG/USDIDR/USDJPY aktif** (S&R+signals+context weight) — altcoin/saham/komoditas lain belum |

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

## ✅ Phase 1 — Dashboard Read-Only (selesai, jadi fondasi Phase C)

Tidak ada di `plan.txt` asli (yang menaruh dashboard di Phase C), tapi
dikerjakan lebih dulu atas permintaan langsung karena dibutuhkan segera
untuk verifikasi visual data yang sudah masuk. Kemudian jadi fondasi Panel
1/2/5 saat Phase C dikerjakan penuh.

**Deliverable:**
- `web/app.py` — Flask, endpoint JSON read-only (`/api/latest`,
  `/api/daily_market`, `/api/asset_ohlcv`, `/api/news`, `/api/assets`,
  `/api/health`). Tidak menulis DB — pipeline tetap satu-satunya penulis
  (masih berlaku untuk endpoint ini; Phase C nambah endpoint BARU yang
  menulis, endpoint lama ini TIDAK diubah).
- `web/templates/index.html` — single-page UI (snapshot cards, status
  `source_flags`, chart harga SVG per instrument, tabel berita dengan filter
  impact).
- Verified end-to-end via preview: semua endpoint 200, chart render dari data
  backfill, filter HIGH/MED/LOW berfungsi.

<a id="anchor-panel-breakdown"></a>
### Riwayat: Phase 1 vs Phase C (6 panel) — breakdown historis

Catatan ini ditulis waktu Phase 1 baru selesai dan Phase C belum dikerjakan
sama sekali (breakdown per panel Master Plan §6). **Sudah tidak akurat** —
lihat [status terkini Phase C](#anchor-phase-c-status) untuk apa yang
sekarang benar-benar ada. Dipertahankan di sini sebagai riwayat, bukan
status aktif:

| Panel (Master Plan §6) | Status SAAT ITU (Phase 1 baru selesai) |
|---|---|
| Panel 1 — Data Snapshot | 🟡 Sebagian: cards + `source_flags` ada; tombol Manual Backfill tidak ada |
| Panel 2 — News Briefing | 🟡 Sebagian: list + impact badge ada; tombol flag manual "key trigger" & "+ Add Manual Article" tidak ada |
| Panel 3 — Forward Panel | ⬜ Tidak ada (butuh tabel Phase D dulu: `expectations`/`positioning`/`policy_tracker`) |
| Panel 4 — Reading Workspace | ⬜ Tidak ada (butuh form input 4 lensa) |
| Panel 5 — Chart + Technical Analysis | 🟡 Sebagian: chart harga polos ada; MA overlay, S&R zone overlay, approve/reject signal tidak ada (butuh Phase B) |
| Panel 6 — Synthesis | ⬜ Tidak ada (butuh `prediction_log` capture + skor prediksi) |

---

## ✅ Phase B — S&R Detection & Breakout/Retest Engine (selesai, BTC)

**Execution plan: `plan_b.txt` (dihapus setelah selesai)** — 7 Open Questions di §7
sudah direview & dikunci Giel, dieksekusi persis sesuai itu.

**Deliverable:**
- `analysis/indicators.py` — `moving_average`, `rolling_ma` (MA rolling
  penuh, dipakai re-derive `volume_ma20` karena kolom itu di `asset_ohlcv`
  cuma keisi untuk hari yang diproses `run_daily.py` — baris hasil backfill
  historis NULL semua, ditemukan saat eksekusi), `ma_stack_order`,
  `volume_ratio`, `is_breakout_volume`, `is_volume_present`.
- `analysis/sr_zones.py` — swing high/low (lookback simetris §7.1),
  clustering ±0.5%, touch-count per episode (bukan per-hari), zone_type
  by majority-vote arah pendekatan, zona <2 touch tetap disimpan
  `is_active=0` (§7.3). `zone_bucket_key()` — natural key log-scale untuk
  UPSERT stabil (§7.4).
- `analysis/signals.py` — breakout (close > resistance + volume >1.5x MA)
  → retest (close > zone_lower + volume >=80%, §7.2) → entry/SL/TP1/R:R.
  Breakout tanpa retest disimpan row terpisah (§7.5), R:R < 1.5 tetap
  disimpan `is_valid=0` (bukan silent-drop).
- `pipeline/run_analysis.py` — orchestrator, BTC-only filter (§4, generic
  di `analysis/*`), UPSERT zona (preserve `validated`/`notes` milik
  manusia saat re-run), INSERT sinyal dedup, `approved` **hardcode 0**
  di satu-satunya titik tulis.
- `tools/review_signal.py` — CLI approve/reject **by id eksplisit**, tidak
  ada mode approve-semua (Master Plan §3: Giel yang approve, bukan mesin).
- `pipeline/seed_context_weight.py` — seed BTC (`net_liquidity`/`etf_flow`
  =HIGH, `fear_greed`/`dxy`=MED, persis Master Plan §4.3).
- 46 test baru (total 80), semua hijau. Diverifikasi juga dengan data BTC
  ASLI (4.313 baris, 2014-2026): 119 zona (117 aktif), 455 sinyal — **0
  di antaranya `approved=1`** (regression guard, bukan cuma di test
  sintetis).
- Cron: **tidak** dijadwalkan otomatis (§7.6) — dijalankan manual, sejalan
  dengan keputusan cron production akan pindah ke server, lokal cuma dev.

**Belum termasuk** (sesuai batas scope `plan_b.txt` §9): dashboard approve
button (Phase C), instrument selain BTC (Phase F+), forward layer (Phase D).

---

<a id="anchor-phase-c-status"></a>
## ✅ Phase C — Dashboard/UI Penuh (selesai)

**Execution plan: `plan_c.txt` (dihapus setelah selesai)** — 5 Open Questions §6
direview & dikunci Giel, dieksekusi persis sesuai itu. Dashboard sekarang
**write-enabled** (pertama kalinya, sebelumnya 100% read-only di Phase 1) —
navigasi 6 tab sesuai alur pagi Master Plan §0/§6.

**Deliverable per panel:**
- **Panel 1** (Data Snapshot): + form Manual Backfill, preview-then-confirm
  (reuse `pipeline.backfill.backfill(preview_only=True)`, ekstensi kecil
  backward-compatible — CLI tidak berubah).
- **Panel 2** (News Briefing): + tombol flag key trigger (`daily_news.
  is_key_trigger`), + form "Add Manual Article" (reuse `pipeline.add_article
  .insert_article()`). *Bug ketemu & diperbaiki saat verifikasi: endpoint
  `/api/news` tidak pernah SELECT kolom `id` (tidak perlu di Phase 1
  read-only) — tombol flag butuh itu, sudah ditambahkan.*
- **Panel 3** (Forward Panel): Economic Calendar tampil data ASLI (76+ event
  dari Phase A) dengan countdown hari; Policy Tracker form manual + list
  (independen Phase D, sesuai keputusan #1); Expectations/Positioning/
  Disonansi tampil **empty state** eksplisit (bukan error) — nunggu Phase D.
- **Panel 4** (Reading Workspace): 4 lensa GEMA/LEON/AKELA/RIVAN + External
  AI Check (manual paste, BUKAN pemanggilan AI) + Conflict Notes. Simpan
  cuma field yang terisi (skip kosong) ke `reading_workspace`
  (`lens` ∈ {GEMA,LEON,AKELA,RIVAN,EXTERNAL_AI,CONFLICT,SYNTHESIS}).
- **Panel 5** (Chart + TA): upgrade dari line-chart Phase 1 jadi **candlestick
  OHLCV + S&R zone overlay + marker breakout/retest + Approve/Reject**
  (reuse `tools.review_signal.set_review()`, `approved` tetap manual).
  MA50/100/200 overlay + volume bar/MA20 + 4 context mini-chart (DXY/S&P
  500/US10Y/Fear&Greed) sempat ditunda (keputusan #2), **sudah dikerjakan
  menyusul** — lihat [Backlog Kecil](#anchor-backlog).
- **Panel 6** (Synthesis): textarea sintesis (→ `reading_workspace` lens=
  SYNTHESIS) + outlook dropdown **5 instrumen** (BTC/SP500/IHSG/GOLD/USDIDR,
  USDJPY dikecualikan — keputusan #5) + form Trading Journal + Prediction
  Log + widget skor prediksi (BENAR/SALAH/PARTIAL).

**Verifikasi:** bukan cuma pytest (92 test, semua hijau) — tiap panel
dicoba LANGSUNG via browser preview (isi form → submit → cek tersimpan di
DB via query langsung → data test dibersihkan lagi). Approve/reject sinyal,
flag key trigger, kedua form Panel 3/4/6, semuanya dikonfirmasi menulis
dengan benar ke tabel yang tepat.

**Belum termasuk** (sesuai batas `plan_c.txt`, bukan terlewat): scraper
otomatis Expectations/Positioning/Policy Tracker (Phase D), Telegram bot
(Phase E), multi-instrument analysis engine (Phase F+), autentikasi (belum
perlu — local-only). Panel 5 MA/volume/context-chart yang tadinya backlog
**sudah selesai juga** (lihat [Backlog Kecil](#anchor-backlog)).

---

## ✅ Phase D — Forward Layer

**Selesai** — `plan_d.txt` (dihapus setelah selesai) dieksekusi penuh. Scope (Master
Plan §4.2, 3 stage): Policy Tracker (Stage 3/Layer A) sudah dikerjakan
lebih awal di Phase C (independen dari urutan Phase D). Sisa scope:

- **Riset sumber sebelum eksekusi** (dicek langsung, bukan asumsi):
  - CME FedWatch: TIDAK ADA API gratis (resmi mulai $25/bulan) → **manual**.
  - Fed Dot Plot/SEP: rilis PDF kuartalan → **manual** (sesuai rencana awal).
  - COT report: CFTC Socrata API **gratis, tanpa API key** (dikonfirmasi
    live query) → **diotomatisasi**.
  - BTC ETF flow: farside.co.uk tidak punya API resmi, dan situsnya di
    belakang Cloudflare — `requests` dengan header default (`Accept:
    application/json`, UA bot) kena challenge page, header browser-realistis
    (UA Chrome + `Accept: text/html` + `Accept-Language`) lolos →
    **diotomatisasi** (HTML scrape, sama profil risiko dengan ForexFactory/
    RSS: kalau situs berubah, `source_flags` fail + lanjut, tidak crash).
  - SBN foreign flow: djppr.kemenkeu.go.id tidak scrape-able reliable (fetch
    polos tidak dapat konten bermakna, indikasi SPA) → **manual**.
- **`scrapers/positioning.py`**: `fetch_cot_positioning()` (BTC/DXY/GOLD/
  SP500, metric `cot_net_long` = noncomm long−short dari CFTC Legacy Futures
  Only report) + `fetch_btc_etf_flow()` (10 hari terakhir dari farside.co.uk,
  metric `etf_net_flow`). Terintegrasi ke `run_daily` (dipanggil tiap hari;
  COT cuma nambah row kalau memang ada rilis mingguan baru — idempotent).
- **`positioning` UPSERT**: `idx_positioning_dedup` UNIQUE(date, instrument,
  metric) ditambah ke schema; `pipeline/run_daily.py::upsert_positioning()`.
- **Manual entry generik** (`web/writes.py::insert_positioning_manual`):
  satu form dipakai baik utk SBN foreign flow (metric bebas TEXT) MAUPUN
  koreksi manual atas row hasil scrape (mis. ETF flow) — `ON CONFLICT DO
  UPDATE` by natural key, sesuai keputusan #2 di `plan_d.txt`.
- **Expectations** (`insert_expectation`/`list_expectations`): form manual
  CME FedWatch cut probability & Dot Plot median.
- **Disonansi Flag** (`compute_disonansi`): aturan v1 sederhana (BUKAN AI) —
  bandingkan sign `stance_score` terbaru (Policy Tracker) vs tren
  `cot_net_long` DXY 14 hari terakhir; kalau berlawanan arah → flagged.
  Return `{"available": false}` kalau data belum cukup (butuh ≥1
  stance_score DAN ≥2 baris COT DXY dalam window) — empty-state eksplisit,
  bukan error.
- **Dashboard Panel 3**: 3 empty-state lama (Expectations/Positioning/
  Disonansi) diganti tabel+form asli.
- **Test baru**: `tests/test_positioning.py` (scraper, live network + unit
  parse helper) + 6 test baru di `tests/test_web_writes.py` — total 108 test.
- **Belum otomatis** (dicatat, bukan terlewat): SBN foreign flow (sumber
  tidak scrape-able), CME FedWatch/Dot Plot (tidak ada API gratis) — semua
  by design, bukan gap teknis.

---

## ✅ Phase E — Telegram Bot

**Selesai (push satu arah)** — `plan_e.txt` (dihapus setelah selesai) dieksekusi penuh.

- **Kenapa PUSH MANUAL, bukan auto dari `run_daily`**: isi briefing (4
  Lensa, Signal approved) baru lengkap SETELAH Giel selesai Panel 4-6
  (~07:20) — `run_daily` jalan jam 07:00, jauh sebelum itu. Auto-push
  nempel di `run_daily` bakal selalu kosong di bagian terpenting. Detail
  lengkap: [ARCHITECTURE.md §6.12](ARCHITECTURE.md#612-telegram-daily-briefing--push-manual-sengaja-tidak-nempel-run_daily).
- **`notify/telegram.py`**: `send_message()` (push Bot API `sendMessage`,
  pakai `requests` biasa — TIDAK nambah dependency berat) + `get_latest_
  chat_id()` (helper setup sekali pakai lewat `getUpdates`).
- **`pipeline/compose_briefing.py`**: rakit teks briefing PERSIS format
  Master Plan §8 (Market Snapshot, Key Events, 4 Lensa, Signal,
  disclaimer wajib) — pure function, murni baca data yang SUDAH Giel isi
  manual, tidak generate apa pun.
- **`pipeline/send_briefing.py`**: CLI (`--dry-run`/`--date`) + tombol
  "Kirim ke Telegram" di Panel 6 dashboard (`POST /api/briefing/send`).
- **Section kosong** (mis. lensa belum diisi) tampil `(belum diisi)` —
  bukan disembunyikan, biar Giel sadar ada yang kelewat. Key Events
  dihilangkan total kalau memang tidak ada news yang di-flag key-trigger
  hari itu (beda kasus — bukan "wajib diisi Giel").
- **>1 sinyal approved** hari yang sama -> semua ditampilkan, 1 baris per
  sinyal (bukan cuma yang terbaru).
- **Test**: `tests/test_compose_briefing.py` (pure function, tanpa
  network) + `tests/test_notify_telegram.py` (di-mock pakai `monkeypatch`
  — SATU-SATUNYA scraper/notify module yang test-nya tidak live-network,
  karena ini operasi SEND, bukan READ — lihat ARCHITECTURE.md §6.12).
- **Ditunda ke backlog** (butuh host always-on, bukan gap): bot commands
  dua-arah (`/snapshot`, `/news` on-demand) — perlu proses long-polling
  yang selalu nyala, laptop lokal tidak selalu on. Konsisten dengan
  keputusan DB & scheduler "local dulu, VPS nanti".
- **Setup manual yang tidak bisa diotomasi**: Giel perlu bikin bot lewat
  `@BotFather` + ambil `chat_id` sendiri (lihat README §Setup Telegram) —
  sama pola dengan `FRED_API_KEY`.

---

## 🟡 Phase F+ — Multi-Aset Expansion

**GOLD/SP500/IHSG/USDIDR/USDJPY selesai diaktifkan** (Master Plan §10,
Phase F/G/H/I digabung 1 pass — `analysis/*.py` sudah generic sejak Phase B,
jadi ini murni "nyalain buat instrument lain", bukan bikin fitur baru).
USDJPY awalnya dikecualikan (keputusan #5 plan_c.txt, khusus utk Panel 6
outlook dropdown) tapi karena datanya sudah lengkap sejak Phase A, Giel
minta diikutkan juga di analysis engine ini.

Yang sebelumnya cuma jalan utk BTC, sekarang jalan utk keenam instrument:
- **`pipeline/run_analysis.py`**: `INSTRUMENTS = ["BTC","GOLD","IHSG","SP500",
  "USDIDR","USDJPY"]` — `python -m pipeline.run_analysis` (tanpa flag)
  proses SEMUA sekaligus; `--instrument X` masih bisa jalan 1 saja.
  `sr_zones`/`trade_signals` sekarang terisi utk keenam instrument (GOLD 74
  zona/433 sinyal, IHSG 73/251, SP500 90/123, USDIDR 65/0, USDJPY 64/0 —
  USDIDR & USDJPY belum ada breakout/retest valid di histori saat ini,
  bukan bug).
- **`pipeline/seed_context_weight.py`**: `GOLD_WEIGHTS`/`SP500_WEIGHTS`/
  `IHSG_WEIGHTS`/`FOREX_WEIGHTS` (USDIDR)/`USDJPY_WEIGHTS` ditambah, persis
  contoh driver Master Plan §4.3 (mis. GOLD: real_yield/dxy/geopolitik;
  USDJPY: rate_differential BOJ-vs-Fed/trade_balance Jepang-AS). `main()`
  seed keenam instrument sekaligus.
- **Dashboard Panel 5**: TIDAK perlu diubah — dropdown instrument &
  `/api/asset_ohlcv`, `/api/sr_zones`, `/api/signals` sudah generic sejak
  Phase C, chart+zona+sinyal langsung tampil begitu data ada. Diverifikasi
  di browser: GOLD/IHSG/SP500/USDIDR/USDJPY semua render chart+zona
  relevan+tabel sinyal dengan benar.
- **Test baru**: `test_seed_context_weight.py` nambah 1 test utk 5
  instrument baru. 121 test hijau total.
- **Catatan**: Panel 6 "Outlook per Instrumen" (`OUTLOOK_INSTRUMENTS` di
  `web/app.py`) MASIH 5 instrumen tanpa USDJPY — itu keputusan #5
  `plan_c.txt` yang terpisah dari analysis engine ini, belum diminta
  diubah.

**Belum dikerjakan** (di luar scope "pastikan 4 instrument ini jalan"):
altcoin lain, saham individual, komoditas tambahan, tinjau ulang SQLite
kalau volume/concurrency berubah signifikan (lihat
[ARCHITECTURE.md §6.1](ARCHITECTURE.md#61-sqlite-vs-postgres-vs-nosql)).

---

<a id="anchor-backlog"></a>
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
- [x] ~~Backfill penuh 5 tahun~~ — **selesai** untuk semua instrument
      (`BTC` 2014-2026, `SP500`/`IHSG`/`GOLD`/`USDIDR`/`USDJPY` 2010-2026,
      4.000+ baris masing-masing) + semua series FRED (lihat item
      `hy_credit_spread` di bawah untuk penjelasan kenapa satu series lebih
      pendek — **bukan gap**, `walcl`/`tga` yang rendah juga WAJAR, seri
      publikasi mingguan bukan harian).
- [x] ~~Panel 5 chart MA/volume/context~~ — MA50/100/200 overlay, volume
      bar+MA20, 4 context mini-chart (DXY/S&P500/US10Y/Fear&Greed) selesai,
      diverifikasi via browser (120 titik penuh tiap garis MA, tanpa NaN).
- [x] ~~Panel 5 chart: penanda tanggal/bulan + filter rentang~~ — sumbu bawah
      chart sekarang nampilin label bulan/tahun (tick otomatis di titik
      pergantian bulan, di-thin maks. 9 label biar gak numpuk saat rentang
      panjang), plus 5 tombol filter rentang (1B/3B/6B/1T/Semua) di atas
      chart yang ganti jumlah candle yang di-fetch & ditampilkan
      (`CHART_VISIBLE`, default 90 hari). "Semua" narik s.d. 5.000 baris
      (cap di `/api/asset_ohlcv`, dinaikkan dari 1.000) — cukup untuk histori
      BTC penuh (~4.300 baris sejak 2014). Diverifikasi di browser: tiap
      tombol filter mengubah rentang tanggal & jumlah candle yang benar
      (1B → 30 hari/2 label, Semua → 2014-2026/9 label).
- [x] ~~Panel 5 chart: sumbu harga (Y) + fix skala tertarik zona jauh~~ —
      ditambah gridline + label harga di kanan chart biar angka open/close
      kebaca langsung. Nemu bug pas nambahin ini: `sr_zones` narik SEMUA
      zona aktif sepanjang histori (termasuk era BTC ~$200), jadi skala Y
      dulu ke-stretch 199 → 124.457 dan candle beneran keliatan gepeng di
      dasar chart. Fix: cuma zona yang overlap ±50% dari rentang harga yang
      lagi tampil dipakai buat skala & digambar (`relevantZones`); label
      "N/117 zona aktif" nunjukin berapa dari total yang relevan ke harga
      saat ini. Diverifikasi: 3B → 29/117 zona relevan & axis 42.874-98.286
      (masuk akal), Semua → 117/117 (span histori penuh, benar).
- [x] ~~Investigasi `hy_credit_spread`~~ — **BUKAN bug/gap kita.** Dicek
      langsung ke FRED (`/fred/series` metadata untuk `BAMLH0A0HYM2`):
      *"Starting in April 2026, this series will only include 3 years of
      observations. For more data, go to the source."* — ICE Data (pemilik
      data ini) sengaja membatasi seri ini ke rolling 3-tahun karena lisensi
      dengan FRED, bukan keterbatasan scraper/backfill kita. Dikonfirmasi:
      DB kita sudah punya 787 dari 793 total observasi yang FRED sediakan
      (re-run backfill: 0 baris baru = cakupan sudah lengkap). Histori lebih
      panjang dari series ini **tidak tersedia gratis** — cuma lewat ICE Data
      langsung (berbayar), di luar scope "no paid API".
- [x] ~~Panel 3 Economic Calendar: tampilkan forecast/previous + isi actual~~
      — `forecast`/`previous` sebenarnya sudah discrape sejak awal tapi tidak
      pernah ditampilkan; sekarang muncul sebagai kolom di tabel. `actual`
      **tidak pernah** disediakan ForexFactory (dicek langsung ke raw JSON
      endpoint — field itu tidak ada sama sekali di respons), jadi diisi
      **manual** lewat dashboard: input inline + tombol "Simpan" per baris
      (`POST /api/econ_calendar/actual`, `web/writes.py::set_econ_actual`),
      berubah jadi tombol "Ubah" begitu terisi. Query `/api/econ_calendar`
      juga diperluas dari "hari ini + mendatang" jadi "H-7 s.d. mendatang"
      biar event yang baru rilis kemarin masih muncul untuk diisi actual-nya.
      2 test baru (`test_web_writes.py`), diverifikasi live di browser +
      query DB langsung.
- [ ] Index/monitoring ukuran DB berkala saat volume bertambah (sanity check,
      bukan berarti perlu migrasi — lihat rationale SQLite di
      ARCHITECTURE.md).
- [x] ~~Evaluasi ulang daftar RSS feed~~ — registry dipindah ke
      `scrapers/feeds_config.py` (satu-satunya tempat kelola feed, ganti
      URL/enabled di sana, bukan di `news.py`) + `check_feed_health()`
      per feed tiap run (status ok/dead masuk `source_flags` dgn prefix
      `rss_`, sama pola dengan API lain — feed mati langsung kelihatan di
      log, bukan backlog tersembunyi). Semua URL DIVERIFIKASI LANGSUNG
      (bukan asumsi): **Reuters** & **Kontan** (`kontan.co.id/feed` DAN
      `/rss`) dikonfirmasi mati beneran (Kontan return HTML homepage
      biasa, bukan XML, bahkan dgn browser UA — bukan bot-block, memang
      sudah dimatikan) → di-`enabled: False` + note. **Bisnis.com**
      TERNYATA masih hidup tapi di subdomain lain (`rss.bisnis.com`, bukan
      `bisnis.com/rss/market` yang 404) — ditemukan lewat riset ulang.
      Hasil akhir: **7 feed aktif** (Fed FOMC, CNBC Finance, CNBC Economy,
      Investing ID, CNBC Indonesia, ANTARA Ekonomi, Bisnis.com), dites
      live via `run_daily`: **7 ok, 0 dead**. `pipeline/run_daily.py`
      print ringkasan `RSS: X ok, Y dead → [...]` tiap run. 9 test baru
      di `tests/test_news.py` (pindah dari `test_macro.py`), 127 test
      hijau total. `IMPACT_KEYWORDS["HIGH"]` sempat kelewat `"bi rate"`
      (cuma `"bank indonesia"` versi lengkap) — ketemu saat porting test
      lama, sudah ditambah balik jadi headline singkatan "BI Rate ..."
      tetap HIGH.
- [ ] Backfill/isi `econ_calendar` untuk event yang sudah lewat kalau perlu
      histori kalender (scraper ini hanya kasih rolling window "minggu ini",
      bukan sumber histori — butuh sumber lain kalau memang perlu).
- [x] ~~`manual_articles` CLI~~ — `pipeline/add_article.py` selesai (add +
      list/search by tag/date-range/keyword), 5 test hijau. Dipakai buat
      riset historis (mis. dari 2010) yang RSS tidak bisa jangkau.
- [x] ~~Panel 1 Snapshot: compare Hari/Minggu/Bulan/Tahun~~ — tombol filter
      di atas kartu snapshot (pola sama dgn filter rentang Panel 5), tiap
      kartu nampilin delta + panah (▲ hijau naik / ▼ merah turun) vs D-1/
      W-1/M-1/Y-1. `web/app.py::_compare_from_series()` cari titik histori
      terdekat <= tanggal target (bukan exact match, wajar ada gap kalender
      krn `run_daily` manual). Kolom yang instrument-nya ada di
      `asset_ohlcv` (BTC/SP500/IHSG/USDIDR/USDJPY/Gold) pakai histori dari
      SANA (bisa >10 tahun), bukan `daily_market` (baru ~4-5 baris utk
      kolom2 itu krn baru mulai keisi beneran) — tanpa ini, compare
      week/month/year bakal selalu n/a utk harga instrument. Kolom lain
      (DXY/US10Y/VIX/dll, di-backfill FRED sejak 2010) & kolom yang
      genuinely belum ada histori panjang (BTC Vol MA20, Funding Rate, Fear
      &amp; Greed, Net Liquidity) tetap `n/a` di periode yang datanya belum
      cukup — bukan bug, jujur soal batas data. Satu fetch `/api/latest`
      cukup (semua periode dihitung sekaligus di server), toggle di
      frontend murni ganti tampilan tanpa fetch ulang. 5 test baru
      (`tests/test_web_app.py`, test pertama utk `web/app.py`), 132 test
      hijau total.
- [x] ~~Panel 1: kategori kartu, collapse source_flags, deteksi data gap~~
      — 3 keluhan UX sekaligus:
      1. **Kartu snapshot dikelompokkan** jadi 3 kategori (Crypto (BTC),
         Makro Global, Ekuitas &amp; FX) — `SNAPSHOT_FIELDS` di `web/app.py`
         diubah dari dict flat jadi list-of-dict berisi `category`, render
         per-grup di frontend (bukan 1 grid rata 14 kartu).
      2. **"Status Sumber Data (source_flags)" jadi collapsible** — native
         `<details>`/`<summary>` (bukan JS custom), default TERTUTUP,
         segitiga ▸/▾ nunjukin state.
      3. **Deteksi data gap di Manual Backfill** — endpoint baru
         `GET /api/data_gaps?instrument=X`, jalan otomatis tiap instrument
         dropdown berubah (`web/app.py::_detect_gaps()`). Tiap instrument
         dipetakan ke kalender-ekspektasi (`INSTRUMENT_SOURCE`): `DAILY`
         (BTC, RRP — RRP dikonfirmasi rilis harian via FRED metadata),
         `WEEKDAY` (ekuitas/forex/DXY/US10Y/VIX/HY), `WEEKLY_WED` (WALCL/
         TGA — dikonfirmasi rilis mingguan, jeda antar-Rabu SENGAJA tidak
         dianggap gap). Gap 1-hari (libur biasa) tidak dilaporkan, cuma
         >=2 hari-ekspektasi berturut-turut. Nemu real gap pas dites: IHSG
         58 gap (kebanyakan minggu libur Lebaran — kelihatan jelas dari
         rentang tanggalnya, Giel yang putuskan itu wajar atau perlu
         backfill, tools cuma kasih visibilitas). 9 test baru
         (`tests/test_web_app.py`), 141 test hijau total.
- [x] ~~News "key trigger" visibility + rework Synthesis + tab Riwayat~~
      — keluhan: tombol "key" di Panel 2 tidak kelihatan sudah di-flag atau
      belum, dan hasil flag cuma muncul di Telegram, jadi bingung gunanya.
      1. **Panel 2 News**: filter tanggal (default hari ini) + filter impact +
         tombol "🚩 Key saja"; baris ter-flag beda warna (`.news-key`); tombol
         flag jadi TOGGLE (★ Key / 🚩 key, klik lagi buat lepas). `/api/news`
         sudah balikin `is_key_trigger` & terima `date` sejak awal — cuma
         ditambah param `key_only`.
      2. **Panel 4 Reading**: section "Berita Key Hari Ini" (read-only) di atas
         4 lensa — berita yang di-flag jadi bahan nulis analisa. Ini yang
         kasih "guna" ke tombol key di dalam dashboard, bukan cuma Telegram.
      3. **Panel 6 Synthesis**: date-picker + auto-load (synthesis & outlook
         hari yang dipilih), dan **fix Outlook yang tadinya tidak tersimpan
         ke mana-mana** — sekarang persist (reuse `reading_workspace`
         lens=`OUTLOOK:<INSTRUMENT>`, upsert 1 stance/instrument/hari, tanpa
         perubahan schema).
      4. **Panel 7 "Riwayat" (BARU)**: arsip input manual yang belum punya
         view historis (chart/news/snapshot sudah punya). Tab dengan sub-tab:
         Synthesis / Prediksi (track record penuh) / Trading Journal / 4 Lensa.
         Read-only list helpers baru di `web/writes.py` + route GET di
         `web/app.py`.
      7 test writes baru, 148 test hijau total; semua panel diverifikasi live
      di browser (toggle key, Key-saja filter, key news Panel 4, outlook
      persist + reload, synthesis save/load, sub-tab Riwayat), data uji
      dibersihkan.
- [x] ~~UI: filter single-select jadi `<select>` + search/sort/pagination
      di semua tabel~~ — 2 keluhan UX sekaligus:
      1. **3 filter button-group yang cuma single-select** (tidak pernah
         multi-select) diganti `<select>` biar hemat tempat: Snapshot
         Hari/Minggu/Bulan/Tahun (`#snapshotPeriodSelect`), News
         Impact/Key-saja (`#newsImpactSelect`), Chart rentang
         1B/3B/6B/1T/Semua (`#chartRangeSelect`). CSS `.news-filters`
         (button-group lama) dihapus, sudah tidak dipakai.
      2. **Search + sort + pagination generik** ditambah ke SEMUA tabel data
         (News, Signals, Econ Calendar, Positioning, Policy Notes, dan
         ke-4 sub-tabel Panel 7 Riwayat — 9 tabel total). 1 utility JS
         reusable (`applyTableControls()`/`renderTableBar()`, dipakai
         ulang, bukan reimplementasi per tabel): cari (debounce 250ms),
         sort per kolom (klik header `<th data-sort="field">`, delegated
         click listener), pagination (10/20/50/100 baris per halaman).
         Cari/sort/page beroperasi di `tableCache[key]` (data yang SUDAH
         di-fetch) — ganti halaman/urutan TIDAK fetch ulang ke server,
         cuma filter server-side (date range, impact, dll) yang trigger
         fetch baru. `renderSignalsTable()`'s hardcoded `.slice(0, 30)`
         dihapus, sekarang tabel Signal Panel 5 bisa akses semua ~200
         sinyal via pagination, bukan cuma 30 pertama.
      **Keputusan arsitektur**: tetap vanilla JS/HTML, TIDAK pindah ke
      framework frontend (React/Vue/dll) — single-user, local-only, tanpa
      build pipeline; search/sort/pagination cuma ~80 baris utility, tidak
      butuh framework. Migrasi framework baru relevan kalau nanti jadi
      multi-user/komersial (Master Plan Phase 2/3), bukan buat polish UX.
      Diverifikasi live di semua 9 tabel (search filter benar, sort
      asc/desc benar, pagination page-count & Prev/Next benar).

- [x] ~~`index.html` dipecah jadi partials/static assets~~ — file tunggal
      1700 baris (HTML+CSS+JS campur) dipecah, TANPA ubah perilaku apa pun
      dan TANPA pindah dari Jinja2/vanilla JS (konsisten dengan keputusan
      arsitektur di atas):
      1. **CSS** → `web/static/css/dashboard.css` (dilink via
         `url_for('static', ...)`).
      2. **HTML per-panel** → `web/templates/partials/panelN_*.html` (7
         file, 1 per tab), di-`{% include %}` dari `index.html`.
      3. **JS per-panel** → `web/static/js/{core,panel1..7,main}.js` (9
         file: shared helpers/table-utility di `core.js`, tiap panel
         dipisah biar gampang dicari, `main.js` isinya `refreshAll()` +
         init), di-load via `<script src>` berurutan (dependency order:
         core dulu, baru panel1-7, baru main — karena semua fungsi masih
         global, bukan module, urutan load penting).
      `index.html` sekarang ~57 baris (shell doang: head+nav+includes+script
      tags). Flask default `static_folder`/`template_folder` (relatif ke
      `web/`) dipakai apa adanya, tidak perlu config baru. Diverifikasi:
      148 test tetap hijau (murni restructure frontend, tidak sentuh
      backend), live browser check tiap panel (1/2/5/7 dicek eksplisit —
      snapshot cards, news table+pagination, chart SVG 335 elemen, sub-tab
      Riwayat) tanpa console error, semua asset ke-load 200/304.
- [x] ~~Panel 4: label 4 lensa deskriptif + hapus "Entri Hari Ini"~~ — 2
      keluhan UX:
      1. Label kartu 4 lensa cuma kode (GEMA/LEON/AKELA/RIVAN) tanpa
         konteks fungsinya. Sekarang jadi "GEMA · Makro Global" / "LEON ·
         Makro Lokal" / "AKELA · On-chain/Fundamental" / "RIVAN · Sentimen
         &amp; Psikologi Pasar" (`LENS_LABELS` map baru di `core.js`, dipakai
         juga di Panel 7 histori 4 Lensa biar konsisten). **Kode `lens` di
         DB TIDAK berubah** (tetap GEMA/LEON/AKELA/RIVAN) — cuma label
         tampilan, biar histori lama tetap kompatibel.
      2. Section "Entri Hari Ini" (tabel kecil di bawah 4 lensa, cuma
         nampilin entri hari ini) dihapus dari Panel 4 — sudah redundan
         sejak Panel 7 "Riwayat &gt; 4 Lensa" ada (nampilin SEMUA histori
         termasuk hari ini, di baris teratas). `loadReadingEntries()` di
         `panel4.js` dihapus, `main.js::refreshAll()` disesuaikan.
      Diverifikasi live: label baru muncul di kartu Panel 4 & kolom Lensa
      Panel 7, "Entri Hari Ini" sudah tidak ada, save 4 lensa masih jalan
      (dicek row tersimpan lewat query DB langsung, lalu dibersihkan).
- [x] ~~Panel 4: 4 Analisa jadi AI-generated (OpenRouter)~~ — **deviasi
      eksplisit & disengaja** dari prinsip Phase C (`web/writes.py` §0 /
      Master Plan: "4 lensa diisi manual, bukan AI agent"). Atas permintaan
      Giel langsung, 4 analisa (GEMA/LEON/AKELA/RIVAN) sekarang di-generate
      lewat OpenRouter, dipicu manual per kartu (tombol "Jalankan Analisa"),
      ditampilkan read-only di popup modal (bukan textarea yang bisa diedit).
      Codename dianonimkan dari UI (cuma label fungsi yang tampil: Makro
      Global / Makro Lokal / On-chain-Fundamental / Sentimen &amp; Psikologi
      Pasar) — kode `lens` di DB TIDAK berubah, histori lama tetap kompatibel.
      1. **`llm/persona_analysis.py`** (paket baru, pola sama `notify/telegram.py`)
         — panggil OpenRouter chat completion via `requests` (sudah dependency,
         tanpa SDK baru). Model dari env `OPENROUTER_MODEL` (default
         `anthropic/claude-3.7-sonnet`). System prompt tiap persona ditulis
         manual Giel di `prompts/persona_&lt;lens&gt;.txt` — **TIDAK dibuat
         otomatis, TIDAK di-commit** (gitignored, dianggap IP analisa
         pribadi Giel, cuma `prompts/README.md` yang di-track). Kalau file
         kosong/belum ada, `run_persona_analysis()` raise
         `PersonaPromptMissing` — endpoint balikin error yang jelas ke UI,
         BUKAN diam-diam skip atau jalan dengan prompt kosong (sesuai
         permintaan eksplisit: "jika belum ada prompt persona beri tahu saya").
      2. **`pipeline/compose_persona_context.py`** — pure function (pola sama
         `compose_briefing.py`), rakit SATU blob konteks (snapshot pasar +
         berita key hari ini) yang dikirim SAMA ke ke-4 persona; system
         prompt masing-masing yang nentuin sudut pandang (bukan konteks
         beda-beda per persona — disederhanakan karena kita tidak punya
         data on-chain asli terpisah).
      3. **`web/writes.py::save_persona_analysis()`** — upsert (DELETE lalu
         INSERT, pola sama `save_outlook`) sehingga re-run persona yang sama
         di hari yang sama OVERWRITE, tidak numpuk duplikat di histori Panel 7.
      4. **`web/app.py`**: `POST /api/persona/run` (body `{lens}, jalankan 1
         persona) + `GET /api/persona/status` (cek prompt sudah diisi atau
         belum, dipakai render kartu). Reuse `GET /api/reading?date=X` yang
         sudah ada buat load hasil tersimpan (tidak perlu route baru).
      5. Manual note lain (External AI Check, Conflict Notes, Synthesis,
         Outlook, Trading Journal, Prediction Log) **TIDAK berubah** — tetap
         100% manual, scope deviasi ini SENGAJA dibatasi ke 4 analisa saja.
      Diverifikasi: 14 test baru (`test_persona_analysis.py`,
      `test_compose_persona_context.py`, + 2 test upsert di
      `test_web_writes.py`, semua di-mock — tidak hit OpenRouter asli),
      162 test hijau total. Live browser: path "prompt belum diisi" (semua
      status `false`, tombol kasih toast, tidak ada panggilan API) diverifikasi
      dulu sebelum prompt asli diisi Giel.
- [x] ~~Panel 1: OI agregat + Long/Short Ratio + Liquidation Long/Short 24h
      (Coinalyze)~~ — scraper baru `scrapers/coinalyze.py` (pola sama
      `scrapers/crypto.py`), 3 endpoint Coinalyze dites LIVE sebelum ditulis
      (`/open-interest`, `/liquidation-history`, `/long-short-ratio-history`,
      auth `Authorization: Bearer <key>`, no key = di-skip bukan error).
      **OI agregat = jumlah 3 exchange utama** (Binance/OKX/Bybit — API
      Coinalyze TIDAK punya simbol gabungan siap pakai, harus dijumlah
      manual; simbol per-exchange formatnya beda-beda, mis. Binance
      `BTCUSDT_PERP.A` vs Bybit `BTCUSDT.6` tanpa suffix `_PERP` — dicek
      satu-satu, bukan ditebak). **Liquidation dipisah long vs short** (2
      kolom baru `btc_liq_long_24h`/`btc_liq_short_24h`), BUKAN 1 angka
      gabungan — kolom lama `btc_liquidation_24h` (sejak Phase A,
      diperuntukkan CoinGlass) dibiarkan kosong/tidak dipakai, bukan
      dihapus (hindari migrasi berisiko). Kolom `btc_long_short_ratio`
      (sejak Phase A, sama-sama pernah kosong) akhirnya terisi juga.
      `btc_oi_aggregate` kolom baru, BEDA dari `btc_oi` yang sudah ada sejak
      Phase A (itu single-exchange Binance saja) — keduanya tetap ada,
      tidak saling gantikan. **Migrasi kolom ke DB lama**: `CREATE TABLE IF
      NOT EXISTS` di `schema.sql` tidak menambah kolom ke tabel yang sudah
      ada isinya — ditambah `db/connection.py::_migrate_columns()` (cek
      `PRAGMA table_info` lalu `ALTER TABLE ADD COLUMN` idempotent),
      dipanggil dari `init_db()`, dites terhadap DB asli (bukan cuma DB
      test) sebelum lanjut. 5 test baru (`test_coinalyze.py`, live network
      pola sama `test_crypto.py`), 167 test hijau total. Diverifikasi live:
      `python -m pipeline.run_daily` penuh (bukan cuma scraper isolated),
      4 card baru muncul di Panel 1 kategori "Crypto (BTC)" dengan angka
      asli (OI agregat ≈$12.35B, L/S ratio 1.46, liq long/short terpisah).
- [x] ~~Panel 3: IHSG Foreign Net Buy/Sell (IDX)~~ — scraper baru
      `scrapers/idx_foreign_flow.py`, sumber internal JSON API idx.co.id
      "Digital Statistic" (bukan API resmi publik, ditemukan lewat source
      code proyek open-source `NeaByteLab/IDX-API` dan dikonfirmasi LIVE
      sebelum dipakai — endpoint `primary/DigitalStatistic/GetApiData`,
      TANPA API key, cuma session cookie). **Simpan 3 komponen mentah
      TERPISAH** (`ihsg_ff_foreign_foreign`, `ihsg_ff_foreign_domestic`,
      `ihsg_ff_domestic_foreign`) + 1 net terhitung
      (`foreign_net_buy_value`), bukan cuma net — GEMA/LEON persona (Track
      D) butuh baca F2F vs F2D vs D2F sendiri-sendiri sesuai aturan
      interpretasi masing-masing. **Koreksi penting** atas library
      referensi `NeaByteLab/IDX-API`: field `foreignForeign*`/
      `foreignDomestic*` BUKAN "buy"/"sell" langsung seperti yang
      dipetakan library itu — label kolom ASLI dari IDX (dari
      `columns[].Title` di response): `foreignForeign` = "Foreign Investor
      Sell − Foreign Investor Buy" (F2F, asing-ke-asing, BUKAN sinyal
      arah), `foreignDomestic` = "Foreign Investor Sell − Domestic
      Investor Buy" (F2D, sisi distribusi). Rumus benar: **Foreign Net Buy
      = domesticForeignValue (D2F, dari endpoint kembaran) −
      foreignDomesticValue (F2D)** — dites & tervalidasi terhadap angka
      nyata (2026-06-02: −Rp 1,39 triliun, magnitude masuk akal).
      **Temuan teknis penting**: idx.co.id di belakang Cloudflare
      bot-management — header browser-realistis SAJA TIDAK CUKUP (beda
      dari farside.co.uk yang juga Cloudflare tapi cukup dengan header,
      lihat `scrapers/positioning.py`). Dikonfirmasi lewat testing
      langsung: curl CLI tembus konsisten (3/3), tapi `requests`/urllib3
      Python KONSISTEN kena halaman JS-challenge ("Just a moment...", 403)
      walau header identik — soal TLS fingerprint (JA3), bukan header.
      Fix: dependency baru **`curl_cffi`** (requirements.txt) yang meniru
      TLS handshake browser asli — SATU-SATUNYA scraper di project ini
      yang butuh ini. `positioning` table dipakai apa adanya (metric
      generik per-instrument per-hari, TIDAK perlu kolom baru di
      `daily_market`), reuse `upsert_positioning` yang sudah ada (natural
      key `date+instrument+metric` dedupe otomatis) — cuma nambah item
      list, pola persis sama dengan COT/ETF flow yang sudah ada. Pola
      tarik-rentang-bukan-1-hari (mirror `fetch_btc_etf_flow`) dipilih
      karena data "hari ini" sering belum terbit saat `run_daily` jalan
      (dikonfirmasi: bulan berjalan selalu balik array kosong) — jadi
      scraper tarik SELURUH bulan tiap run, biar hari-hari sebelumnya
      ke-backfill otomatis kalau run sebelumnya sempat gagal/terlewat. 5
      test baru (`test_idx_foreign_flow.py`, live network pola sama
      scraper lain), 172 test hijau total. Diverifikasi live penuh:
      `pipeline.run_daily` untuk tanggal Juni 2026 (bulan lengkap) — 80
      row masuk `positioning` (20 hari bursa × 4 metric), angka 2026-06-02
      cocok PERSIS dengan perhitungan manual saat riset plan, Panel 3
      browser nampilin ke-4 baris dengan benar.
- [x] ~~Panel 4: rewrite konteks 4 Persona jadi Shared Core + Slice per
      persona (system prompt v4)~~ — **pivot arsitektur eksplisit dari
      Giel**, membalik keputusan awal ("Sama untuk ke-4 (Recommended)" saat
      Panel 4 pertama dibangun). Alasan: 4 analis yang membaca data BERBEDA
      menghasilkan sudut pandang independen yang bisa didebat (konflik
      produktif), bukan 4 analis baca data identik yang cuma beda gaya
      bicara.
      1. **`indicators/calc.py`**: `COMPARE_PERIODS`/`compare_from_series`
         (delta Hari/Minggu/Bulan/Tahun) dipindah dari `web/app.py` ke sini
         — dipakai BARENG oleh Panel 1 (`web/app.py`) dan konteks persona
         (`pipeline/compose_persona_context.py`), hindari `pipeline`
         import dari `web` (layering salah arah kalau tetap di app.py).
      2. **`pipeline/compose_persona_context.py`** — rewrite total,
         signature jadi `compose_persona_context(conn, date, lens)`.
         **SHARED CORE** (semua persona): tanggal, berita key, BTC
         close+delta H/M. **SLICE per lens**: GEMA (DXY/US10Y/VIX/Net
         Liquidity/HY+delta, USD/JPY/Gold/SP500/BTCDom tanpa delta,
         USD/IDR+delta, IHSG foreign flow F2F/F2D/D2F dari Track C, COT
         DXY+ETF flow, Policy Tracker speaker ASING), LEON (IHSG/USD-IDR+
         delta, IHSG foreign flow — framing BEDA dari GEMA: "rapor
         kepercayaan kebijakan" bukan "arah arus modal", econ_calendar
         country=ID, Policy Tracker speaker DOMESTIK), AKELA (econ_calendar
         penuh, Disonansi Flag, Fear&Greed+delta, VIX, BTC Vol MA20,
         funding rate, delta H/M/B/T instrumen utama), RIVAN (funding rate,
         OI agregat+delta dari Track B, liquidation long/short 24h, L/S
         ratio, ETF flow, BTC Dominance, volume vs Vol MA20). IHSG foreign
         flow SENGAJA tidak diberikan ke AKELA/RIVAN (disiplin slice).
         Policy Tracker speaker asing/domestik diklasifikasi lewat keyword
         match nama institusi (`DOMESTIC_INSTITUTION_KEYWORDS`) — tabel
         `policy_tracker` tidak punya kolom terstruktur utk ini.
      3. **`web/app.py::persona_run()`** — teruskan `lens` ke
         `compose_persona_context`.
      4. **`prompts/persona_{gema,leon,akela,rivan}.txt`** — diganti PENUH
         (verbatim) dengan system prompt v4 dari Giel, termasuk panduan
         interpretasi F2F/F2D/D2F eksplisit di prompt GEMA & LEON.
      5. Prompt Orkestrator (panel debat 4-sekaligus + sintesis konflik,
         juga ada di dokumen v4) **DICATAT sebagai backlog**, TIDAK
         dibangun — Panel 4 saat ini jalankan 1 persona per klik, bukan
         panel debat serentak; butuh desain UI terpisah.
      **Temuan saat implementasi**: `econ_calendar country='ID'` SELALU
      kosong saat ini — sumber ForexFactory tidak cover kalender Indonesia
      sama sekali (dicek: `SELECT DISTINCT country` cuma NZ/AU/CA/GB/US/
      EU/CH/JP/CN, tidak ada ID). Bukan bug Track D — keterbatasan sumber
      data yang sudah ada, dicatat apa adanya di teks konteks LEON
      ("sumber ForexFactory saat ini tidak cover kalender ID") bukan
      disembunyikan.
      **Urutan eksekusi**: Track B → Track C → Track D (keras, bukan
      preferensi) — slice GEMA/LEON butuh field Track C, slice RIVAN butuh
      field Track B; pasang prompt v4 sebelum data-nya ada akan bikin
      persona mengklaim data yang sebenarnya kosong.
      9 test baru (`test_compose_persona_context.py` full rewrite, fokus
      verifikasi ISOLASI slice — field GEMA tidak bocor ke RIVAN dst),
      178 test hijau total. Diverifikasi live: ke-4 slice dipanggil dengan
      tanggal sama terhadap DB asli, konfirmasi isi 100% beda (bukan
      identik lagi), 1 run RIVAN asli lewat OpenRouter — hasilnya
      mengutip angka liquidation long/short SUNGGUHAN dan menerapkan
      aturan interpretasi "short-covering" dari prompt v4 dengan benar,
      row test dibersihkan setelah verifikasi.

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
- **Net exchange flow (BTC)** — dicek: Glassnode/CryptoQuant memang **berbayar**
  untuk metric ini (sesuai catatan awal), dan tidak ada pengganti gratis yang
  setara kualitasnya. Metric ini butuh database alamat exchange yang
  di-labeling & di-maintain terus-menerus (siapa pemilik alamat mana) — justru
  itu yang jadi nilai jual berbayar Glassnode/CryptoQuant, bukan sekadar akses
  data blockchain (yang publik/gratis). Opsi yang ada, semua kurang layak:
  - **Dune Analytics** (gratis) — beberapa dashboard komunitas replikasi
    netflow-style CryptoQuant via SQL query atas data on-chain ter-indeks,
    tapi ini "pakai/adaptasi query orang lain" bukan REST endpoint stabil —
    bentuk integrasi beda sendiri dari semua scraper lain di project ini.
  - **DIY** (maintain sendiri daftar alamat exchange + query chain indexer) —
    effort tinggi, kualitas data di bawah vendor berbayar, tidak sepadan untuk
    dashboard personal. **Tetap Backlog** — tidak ada jalan gratis yang worth
    effort-nya saat ini.
  - **Update (dicoba CryptoQuant API key berbayar milik Giel, diverifikasi
    LIVE)**: key valid (endpoint lain seperti `market-data/price-ohlcv`
    berhasil 200 + data asli), TAPI seluruh kategori `exchange-flows`
    (`netflow`, `inflow`, `outflow`, `reserve`, dll — 6 endpoint dicoba
    semua) balikin 403 "no authority for this request". Bukan soal free vs
    berbayar lagi — plan CryptoQuant yang Giel punya SEKARANG tidak
    mencakup kategori ini sama sekali, kemungkinan butuh tier lebih
    tinggi/add-on terpisah (granularitas entitlement per-endpoint, bukan
    per-tier rapi — `open-interest` juga 403 padahal sama-sama "market-data"
    dengan `price-ohlcv` yang jalan). Tidak ada workaround (coba hitung
    manual dari inflow−outflow juga mentok, keduanya sama-sama 403). **Giel
    putuskan drop** — tidak worth dikejar lebih jauh. Tetap Backlog.
- **Whale / long-term holder (LTH) accumulation (BTC)** — sama, Coin Metrics
  punya tier "Community" gratis, TAPI metric age-band/LTH-split spesifik
  (`SOPRLth`, realized cap by coin age, dll) ternyata di-gate ke tier
  "Network Data Pro" (berbayar) — tier gratisnya tidak mencakup ini. Satu-
  satunya proxy yang genuinely gratis & bisa dipakai:
  - **Whale Alert API** (free tier) — feed transaksi besar individual
    real-time (mis. "$X pindah dari wallet A ke exchange B"). Ini proxy
    **pergerakan whale**, BUKAN metric "LTH supply accumulating" yang
    sebenarnya (beda konsep: transfer individual vs UTXO age analysis), tapi
    arahnya related (whale pindahin dana ke/dari exchange). Rate limit tier
    gratis belum dikonfirmasi persis — perlu dicek dokumentasi resminya
    kalau mau dipakai. **Tetap Backlog** — kalau nanti mau proxy kasar, Whale
    Alert adalah pilihan paling realistis, bukan metric asli LTH.
  - **Update**: dicoba juga lewat CryptoQuant API key Giel (endpoint
    `network-indicator/utxo-age-distribution`, proxy LTH/STH via UTXO age) —
    403 sama seperti `exchange-flows` di atas, tidak termasuk plan yang
    dipunya. **Giel putuskan drop** bareng item di atas — tidak worth
    dikejar lebih jauh. Tetap Backlog.

## Prinsip Perubahan Roadmap

Sesuai `plan.txt`: **jangan lompat phase tanpa instruksi baru.** Kalau ada
kebutuhan mendesak di luar urutan (seperti Phase 1 kemarin), itu boleh — tapi
harus tercatat di sini dengan jelas kenapa keluar urutan, supaya roadmap tetap
mencerminkan kenyataan, bukan rencana ideal yang sudah basi.
