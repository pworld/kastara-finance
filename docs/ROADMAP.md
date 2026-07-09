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
