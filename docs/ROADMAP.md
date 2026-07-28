# Kastara Finance — Roadmap

> Sumber acuan: **[Master Plan.md](Master%20Plan.md)** (v1.5, dokumen strategi
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
| **J+** | Equity expansion (saham individual IDX→US) | 🔶 **Build Contract v1.3 LOCKED (11 Jul 2026) + Addendum A Tab 8 (12 Jul 2026, SELESAI SELURUHNYA 13 Jul 2026), Gerbang G1/G2/G3 DIJAWAB (13 Jul 2026)** — universe = **BBCA + TSLA**; **J-2/J-3(groundwork)/J-3b/J-4/J-6/J-7/J-8/J-10/J-11/J-12/J-13/J-14/J-15 SELESAI**; sisa: **J-5** (ditunda, belum worth dgn 1 ticker/sektor), **J-9** (prompt persona v5, butuh tulisan Giel), + validasi bar-replay manual & kalibrasi §13 (keputusan Giel, bukan otomatis) |

---

<a id="anchor-gap-tersisa"></a>
## 📍 Gap Tersisa (13 Jul 2026) — ringkasan cepat, TIDAK perlu scroll ke bawah

Semua build/kode dari kontrak sudah selesai. Yang tersisa cuma butuh
tindakan/keputusan Giel sendiri, bukan development lagi:

1. **Track A — Deploy infra** (auth, Docker/Railway, Telegram bot 2-arah) —
   sengaja ditunda ("save for release time"), belum dikerjakan sama sekali.
2. **Bar-replay validation** — mekanismenya SUDAH ADA (Panel 8 "Validasi
   Lane", lihat §"Update — Mekanisme validasi lane" di bagian Phase J+ di
   bawah), tapi belum ada satu instrumen pun yang divalidasi. BBCA & TSLA
   masih `lane=INVEST`, belum `TRADE`.
3. **Kalibrasi §13 final** — `IDX_ZONE_TOLERANCE_TICKS = 2` di
   `analysis/calibration.py` masih DRAFT, nunggu Giel konfirmasi/revisi
   setelah lihat bar-replay beneran (lihat §"Update — J-3: ARA/ARB..." di
   bawah).
4. **J-9 prompt persona** — draft teks sudah ada di
   [`docs/j9_equity_slice_prompt_draft.md`](j9_equity_slice_prompt_draft.md),
   belum digabung ke `prompts/persona_rivan.txt`/`persona_akela.txt`
   (suara Giel sendiri, bukan final version dari saya).
5. **J-5 — sector benchmark** — ditunda, belum worth effort-nya dengan
   cuma 1 ticker per sektor di universe saat ini.

Detail penuh tiap item ada di section "🔶 Phase J+" di bawah (cari heading
"**Update —**" terbaru per topik) — poin di atas cuma ringkasan biar tidak
perlu scroll baca histori lengkapnya.

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
- [x] ~~Forward panel: urutkan Economic Calendar berdasar tanggal + filter
      importance~~ — sebelumnya event lama nongkrong di atas tabel, sekarang
      di-sort (upcoming/hari-ini dulu, event lewat didorong ke bawah) + filter
      dropdown default **HIGH saja (bintang 3)**, opsi "HIGH + MED" kalau
      perlu lihat semua. Murni client-side (`ForwardView.vue`), tidak ubah API.
- [x] ~~Earnings emiten tampil di Forward panel (J-15 gel.2, kontrak §19.5)~~
      — `earnings_calendar` (data J-7 sudah ada sejak lama, TAPI tidak pernah
      di-surface: tak ada endpoint, tak ada di UI) sekarang tampil di
      `ForwardView.vue` section "Earnings Emiten", berdampingan dgn Economic
      Calendar ("gabung visual" = section terpisah, bukan 2 skema dipaksa 1
      tabel). READ-ONLY (eps_actual diisi scraper, bukan manual). Kolom:
      countdown, EPS forecast/actual, surprise (beat hijau/miss merah).
      **WARNING earnings posisi terbuka** (kontrak §18 keputusan #3):
      `trading_journal.outcome='ONGOING'` JOIN `earnings_calendar` mendatang →
      badge merah "tutup penuh" utk saham AS (`hard_rule`, penegak rule
      no-hold-through-earnings), badge informatif utk IDX (tak ada aturan
      tutup-penuh, gap tetap risiko). 2 read helper baru
      (`list_earnings_calendar`/`list_earnings_warnings`, `web/writes.py`) +
      2 endpoint (`GET /api/earnings`, `/api/earnings/warnings`). 5 test baru
      (`test_web_writes.py`), diverifikasi direct-Python ke DB asli (earnings
      2026-07-22 muncul H-7) + skenario warning temp-DB (TSLA/US hard,
      BBCA/IDX soft, posisi lewat/jauh di-skip).
- [x] ~~News Threads N-1 fondasi (Addendum B §20, adendum Giel)~~ — gap
      Addendum B yang SEBELUMNYA belum dibangun sama sekali (beda dari
      Addendum A/Panel Universe yang sudah selesai J-14/J-15). **N-1 saja**
      (fondasi) — N-2 (strip Reading, injeksi digest ke `compose_persona_
      context.py`, auto-DORMANT) SENGAJA belum dibangun, kontrak sendiri
      membagi 2 gelombang & N-2 perlu N-1 dipakai beberapa hari dulu sbg
      bahan uji.
      **Schema**: 3 tabel baru (`news_threads`, `news_thread_links`,
      `thread_relations` schema-only utk N-2) + 1 UNIQUE index dedup — 22→25
      tabel total.
      **Backend**: `scrapers/news.py::_matches` dipromosikan jadi
      `scrapers/base.py::keyword_matches()` (reuse rule-based matcher, bukan
      tulis ulang, dipakai 2 tempat sekarang). `web/writes.py` — `save_thread`
      (guard title wajib + **maks 7 thread ACTIVE**, ditegakkan di write
      function bukan cuma UI, keputusan #5), `patch_thread` (guard verdict
      wajib saat status=CLOSED), `suggest_thread_links` (auto-suggest
      rule-based, HANYA scan thread ACTIVE, SELALU cuma SUGGESTED — tidak
      pernah auto-CONFIRMED, human gate §20.0), `confirm_thread_link` (stance
      WAJIB — anti-confirmation-funnel keputusan #3 — `also_key_trigger`
      reuse `flag_key_trigger()` existing), `reject_thread_link`,
      `add_thread_link_manual` (guard ref_table dikenal + dedup), `list_
      thread_links` (union manual 3 sumber: daily_news/manual_articles/
      policy_tracker), `attach_thread_suggestions` (CONFIRMED menang atas
      SUGGESTED kalau 1 berita match >1 thread). `pipeline/run_daily.py`:
      hook `suggest_thread_links` SETELAH `insert_news_dedup` (butuh row id
      asli), count masuk `summary`. 7 endpoint baru `/api/threads*`
      (mutasi via POST, bukan PATCH — konsisten konvensi app ini yang tidak
      pernah pakai PATCH/PUT di tempat lain) + `/api/news` di-extend nempel
      `thread_link` per row.
      **Frontend**: `NewsView.vue` — chip "Saran: `<thread>`?" + Konfirmasi
      (Dialog pilih stance, checkbox "sekalian key trigger") / Tolak per
      baris; `ThreadIndexView.vue` (baru, `<DataTable>` + form buat thread) +
      `ThreadDetailView.vue` (baru, timeline vertikal link CONFIRMED + edit
      current_read/status/verdict + tautkan manual) — **route `/threads/:id`
      pertama di app ini yang pakai `:id` dinamis**. Nav sidebar "Threads"
      ditambah di grup Daily (§20.6: konfirmasi SUGGESTED = ritual pagi) —
      tanpa ini halaman baru tidak reachable lewat UI normal di N-1.
      19 test baru (`test_web_writes.py`, guard 7-ACTIVE/verdict-wajib/
      stance-wajib/ref_table-dikenal/dedup, idempotensi auto-suggest,
      `also_key_trigger` beneran reuse `flag_key_trigger`). 336 test hijau
      total. **Diverifikasi live**: `init_db()` dijalankan ke DB asli
      (tabel baru butuh migrasi — awalnya sempat 500 "no such table" sebelum
      ini disadari), Flask test-client round-trip penuh (create→list→detail→
      patch→3 guard 400), DAN `suggest_thread_links` terhadap headline
      PRODUKSI ASLI hari ini — keyword "hawkish" berhasil match "Bank
      Sentral Makin Hawkish, Manulife IM Sarankan Pengelolaan Investasi
      Aktif" dengan status SUGGESTED (bukan auto-CONFIRMED, human gate
      terbukti jalan). Thread verifikasi di-CLOSE lagi setelahnya (tidak
      ditinggal ACTIVE di DB asli). `npm run build` sukses (349 module,
      termasuk `ThreadIndexView`/`ThreadDetailView` — bukti transform
      SFC baru tidak error; console-check saja tidak cukup karena route
      lazy-load di balik auth guard tidak pernah di-import kalau belum
      login).
- [x] ~~Faceted Tagging C-1 fondasi (Addendum C §21, adendum Giel)~~ — **C-1
      saja** (fondasi), C-2 (feed manual ke persona, tag-based thread
      matching) SENGAJA belum dibangun — kontrak sendiri MENGUNCI ini
      (§21.9 keputusan #7: "bangun C-1+C-2 sekaligus" eksplisit masuk daftar
      "TIDAK dilakukan", beda dari News Threads yang cuma direkomendasikan).
      **5 hal dalam 1 paket**: (a) kamus tag facet controlled-vocabulary
      (geo/org/who/sym/theme/sec, mulai KOSONG), (b) UI command-palette
      tagging, (c) `display_subtitle` (catatan Giel, headline asli TAK
      PERNAH ditimpa), (d) rename fungsional `is_key_trigger` →
      `for_reading` (tag = klasifikasi objektif, for_reading = kurasi
      subjektif — 2 pertanyaan beda yang dulu dirangkap 1 flag).
      **Schema**: 2 tabel baru (`tag_dictionary`, `content_tags` — 25→27
      tabel) + 2 kolom baru di `daily_news` (`display_subtitle`,
      `for_reading`) lewat `_COLUMN_MIGRATIONS` (BEDA dari tabel baru News
      Threads — `daily_news` sudah punya data live, jadi lewat jalur
      migrasi kolom, bukan `CREATE TABLE` — pola sama `asset_context_
      weight.level`), termasuk backfill one-time `for_reading =
      is_key_trigger` (idempotent, tidak jalan ulang tiap `init_db()`).
      **Rename penuh, bukan alias**: `flag_key_trigger()` →
      `set_for_reading()`, `/api/news/flag_key` → `/api/news/for_reading`,
      `confirm_thread_link`'s `also_key_trigger` → `also_for_reading` —
      disapu di ~8 file (writes.py, app.py, 2 file pipeline, 2 view Vue, 3
      file test) via grep menyeluruh, `is_key_trigger` LAMA dibiarkan beku
      di schema (jangan DROP, DB hidup) tapi tidak dibaca/ditulis lagi.
      **Backend baru**: `create_tag` (validasi tata bahasa — facet:value,
      lowercase-hyphen, `sym:` wajib region-prefix — regex PERTAMA di
      writes.py, tapi idiom raise-ValueError sama persis fungsi lain),
      `list_tags`/`resolve_tag` (alias), `apply_tag` (guard tag harus ada
      di kamus dulu + dedup + usage_count naik), `remove_tag`,
      `list_content_tags`/`attach_content_tags` (batch, mirror
      `attach_thread_suggestions`). 6 endpoint `/api/tags*`+`/api/content_
      tags*` baru + `/api/news/<id>/display_subtitle`, semua mutasi via
      POST (bukan PATCH — konsisten konvensi app ini).
      **Frontend**: `TagAutocomplete.vue` baru (bungkus PrimeVue
      `AutoComplete`, sudah tersedia zero-dep di v4.5.5 — grouped dropdown
      by facet + chip+remove-X bawaan, dikonfirmasi via `npm run build`
      generate chunk `TagAutocomplete-*.js` beneran, bukan asumsi dari
      package.json) dipakai 3 tempat: kolom Tag per-baris `NewsView.vue`,
      filter-chip bar (AND/OR toggle) di News, filter tag di
      `ReadingView.vue`. `NewsView.vue` juga dapat inline-edit
      `display_subtitle` (endpoint sempat tidak ke-reach dari UI mana pun
      sebelum ditambahkan — ketahuan saat review sendiri) + collapsible
      "Telusuri Semua Tag" (pola sama `source_flags` di SnapshotView,
      pakai `DataTable.vue` apa adanya).
      **Bug ketemu saat implementasi**: `attach_content_tags()` awalnya
      TIDAK menyertakan `content_tags.id` per tag (cuma canonical+facet) —
      UI tidak akan bisa panggil `remove_tag()` sama sekali tanpa itu.
      Ketahuan sebelum sempat jadi masalah produksi (saat menyambungkan ke
      NewsView, bukan lewat bug report) — diperbaiki + test terkait di-update.
      35 test baru (guard tata bahasa 4 kasus, dedup create/apply, alias
      resolve, batch attach, migrasi backfill). 354 test hijau total.
      **Diverifikasi live**: `init_db()` ke DB asli (1.973 baris `daily_news`
      real — 100% `for_reading` cocok `is_key_trigger` pasca-backfill,
      meski nilainya seragam 0 krn belum ada yang pernah di-flag "key"
      sebelum sesi ini), Flask test-client round-trip penuh (create tag →
      apply ke baris berita ASLI → list → remove → cek benar-benar hilang)
      + 4 guard tata bahasa 400 semua benar, `npm run build` sukses (356
      module). Tag verifikasi (`who:warsh-verify`) SENGAJA dibiarkan di
      kamus asli (usage_count=0 setelah di-lepas) — tidak ada endpoint
      hapus-dari-kamus di C-1 (memang bukan fitur C-1; pembersihan kamus
      lewat review kuartalan §21.7, bukan tombol ad-hoc) — harmless, akan
      kena saring natural saat review kuartalan pertama.
- [x] ~~Bug: DXY/US10Y/VIX kelihatan "kosong" padahal tidak ada gap tanggal
      (17 Jul 2026)~~ — Giel lapor 3 field ini beku beberapa hari, sudah
      cek sendiri tidak ada baris tanggal yang hilang. **Root cause bukan
      gagal fetch** — `source_flags` `fred_dxy`/`fred_us10y`/`fred_vix`
      semuanya `ok` (API call sukses tiap hari). Masalahnya:
      `scrapers/macro_fred.py::_fetch_series()` selalu ambil observasi
      TERBARU yang tersedia dari FRED, lalu dilabeli tanggal target `run_daily`
      TANPA cek apakah observasi itu memang untuk hari itu. FRED sendiri
      publish DXY/US10Y/VIX dengan jeda (bukan real-time) — dicek langsung:
      DXY (`DTWEXBGS`) 7 hari basi, US10Y/VIX 2 hari basi saat bug ditemukan.
      Kalau FRED belum update sejak fetch terakhir, hasilnya angka IDENTIK
      berhari-hari berturut-turut (dikonfirmasi: 120.5046/4.55/15.67 sama
      persis di `daily_market` 14–17 Jul) — bukan bug scraping, tapi
      `source_flags` lama tidak bisa bedakan "fresh" vs "basi tapi sukses fetch".
      **Fix**: `MAX_LAG_DAYS` per series (DXY/US10Y/VIX/RRP/TGA/HY=4 hari,
      WALCL=10 hari — rilis mingguan H.4.1 tiap Kamis) + cek lag di
      `fetch_macro_fred()`, timpa flag jadi `'stale'` (bukan `'ok'`) kalau
      observasi lebih tua dari batasnya — **value TETAP ditulis** (angka
      basi masih lebih berguna drpd NULL), cuma sekarang kelihatan bedanya
      di dashboard. Sempat salah kalibrasi DXY threshold ke 10 hari
      (dikira mingguan) — histori observasi DXY sendiri (5 hari kalender
      berturut-turut) membuktikan itu business-daily juga, diturunkan ke 4
      biar bug yang baru ditemukan beneran ke-flag. Frontend: `.dot.stale`
      (warna `--med`, beda dari fail/ok/skip) + `SnapshotView.vue` sort
      order `fail→skip→stale→ok`. 2 test baru pakai monkeypatch
      (`tests/test_macro.py` — live-test tidak bisa kontrol seberapa basi
      data FRED beneran hari itu secara deterministik, pola sama
      pengecualian `test_notify_telegram.py`). 356 test hijau total.
      **Diverifikasi live** ke DB asli: `fred_dxy` sekarang `stale`,
      `fred_us10y`/`fred_vix` tetap `ok` (lag 2 hari masih dalam batas
      wajar weekend) — dikonfirmasi lewat `/api/latest` beneran, bukan cuma
      unit test.
- [x] ~~News Threads: catch-up scan otomatis + edit title/keyword + multi-link
      di News page (17 Jul 2026, 3 permintaan Giel sekaligus setelah cek
      halaman `/threads`)~~ — Giel lapor thread yang baru dibuat siang hari
      kosong link-nya (thread ACTIVE nyata, tapi 0 SUGGESTED) meski headline
      relevan sudah ada di `daily_news`. **Root cause**: `suggest_thread_links()`
      cuma pernah dipanggil `run_daily` dgn headline yang BARU DI-FETCH hari
      itu — tidak pernah scan ulang histori yang sudah ada di DB. Thread dibuat
      setelah cron pagi = ketinggalan semua berita pagi sampai cron besok.
      Ditambal manual dulu (68 link real ditemukan lewat scan retroaktif),
      lalu Giel minta 3 hal:
      **1) Catch-up scan otomatis** — `THREAD_CATCHUP_DAYS = 7`,
      `save_thread()` & `patch_thread()` (saat `keywords` berubah, thread
      ACTIVE) sekarang scan `daily_news` 7 hari ke belakang & jalankan
      `suggest_thread_links()` langsung, bukan nunggu cron besok. Idempoten
      via UNIQUE index dedup yang sudah ada (aman di-re-run/overlap window).
      **2) Edit title/keywords di `/threads/:id`** — `patch_thread()`
      diperluas terima `title` (guard non-kosong) & `keywords` (JSON-encode
      pola sama `persona_tags`); endpoint `/api/threads/<id>` extend field
      whitelist; `ThreadDetailView.vue` tambah 2 input di form edit yang
      sudah ada.
      **3) Multi-thread-link di `/news`** — sebelumnya `attach_thread_
      suggestions()` cuma kirim 1 `thread_link` 'pemenang' (CONFIRMED menang
      atas SUGGESTED) per berita, jadi kalau 1 headline match >2 thread
      Giel tidak bisa lihat/ubah/lepas yang lain. Diganti kirim array
      `thread_links` (semua link non-REJECTED, CONFIRMED duluan).
      `NewsView.vue` kolom Thread sekarang render banyak chip sekaligus
      (tiap chip ada aksi sendiri — Konfirmasi/Tolak utk SUGGESTED, Lepas
      utk CONFIRMED, reuse `POST /api/threads/link/<id>/reject` yang sudah
      terima link status apa pun) + affordance baru "+ Tautkan Thread"
      (dropdown thread ACTIVE + stance, reuse `POST /api/threads/<id>/links`
      `add_thread_link_manual` yang sudah ada utk `ThreadDetailView`, tidak
      ada endpoint baru).
      9 test baru (`test_web_writes.py` — catch-up scan idempoten & respect
      window, guard title kosong, catch-up trigger saat keyword diubah,
      `attach_thread_suggestions` array shape termasuk exclude-REJECTED).
      364 test hijau total. **Diverifikasi**: Flask test-client round-trip ke
      DB temp terisolasi (create thread → link manual ke berita → muncul di
      `/api/news` sbg `thread_links` → reject → hilang lagi) — sempat KELIRU
      pakai env var `DB_PATH` (bukan `KASTARA_DB_PATH`) di percobaan pertama
      shg tanpa sengaja nulis thread+link test ke DB PRODUKSI asli; ketahuan
      lewat sqlite langsung, langsung dibersihkan (`DELETE` thread id 5 +
      link id 70), dikonfirmasi state balik persis semula sebelum lanjut
      pakai DB temp yang benar. `npm run build` sukses (356 module).
- [x] ~~Inline edit title/status/keywords/bacaan terkini langsung di `/threads`
      index (17 Jul 2026)~~ — sebelumnya edit field ini cuma bisa lewat detail
      page (`/threads/:id`), Giel minta bisa langsung dari daftar. Pola sama
      `subtitleInputs`/`editingIds` di `NewsView.vue`: `editingIds` Set +
      `editInputs` dict per baris, "Edit"→input/select muncul→"Simpan" POST ke
      `/api/threads/<id>` (endpoint sudah ada, tidak ada perubahan backend).
      Verdict TETAP di detail page saja (jarang dipakai, wajib cuma saat
      CLOSED) — kalau status di-set CLOSED dari index tanpa verdict,
      `patch_thread()` nolak dgn error toast, arahkan ke detail page.
- [x] ~~Addendum C §21 selesai PENUH: tutup gap C-1 (Settings page) + bangun
      C-2 (17 Jul 2026, Giel: "jalankan adendum C" → override eksplisit
      klausul tunggu-2-minggu §21.8, "Section 21 & C-1/C-2. FINAL")~~ —
      audit ulang nemu **1 gap nyata di C-1 sendiri**: §21.8 daftar "Settings
      → Tag & Thread Management" (§21.11) sebagai item C-1, tapi tidak pernah
      dibangun (NewsView cuma punya tabel tag read-only, tidak ada
      merge/delete/edit-description, tidak ada halaman kelola thread di luar
      per-row). Sisanya C-1 (skema, tag CRUD, command-palette, `for_reading`,
      `display_subtitle`) genuinely selesai & teruji.
      **Bagian 1 (tutup gap C-1)**: `web/writes.py` — `update_tag`
      (description/facet), `delete_tag` (guard usage_count>0 tanpa force →
      ValueError, force hapus tag+content_tags-nya), `merge_tag` (from jadi
      alias into, content_tags re-point dedup-aware lewat INSERT OR IGNORE +
      DELETE baris redundan, usage_count DIHITUNG ULANG dari row count aktual
      bukan dijumlah — cegah salah hitung saat re-point collide),
      `list_orphan_tags`, `thread_stats`/`list_threads_with_stats` (komposisi
      stance CONFIRMED, pending SUGGESTED, umur hari, `active_count` global
      utk "N/7 ACTIVE", plus facet tags thread lewat reuse
      `attach_content_tags(conn, "news_threads", rows)` — tidak ada fungsi
      baru krn `news_threads` sudah ada di `ALLOWED_CONTENT_TAG_REF_TABLES`).
      5 endpoint baru (`/api/tags/<id>{,/delete}`, `/api/tags/merge`,
      `/api/tags/orphans`, `/api/threads/stats`). `SettingsView.vue` baru,
      2 tab (Tags: edit/hapus/gabung inline + form merge; Threads: tabel
      komposisi/umur + Dialog "Kelola Thread" (status/current_read/verdict/
      persona_tags checkbox 4-lensa/facet tags via `TagAutocomplete` reuse) —
      route `/settings` + nav group baru "Pengaturan" (App.vue, terpisah dari
      "Daily" krn sifatnya reflektif/kuartalan, bukan ritual harian).
      **Bagian 2 (C-2)**: (a) `suggest_tags_for_news()` — auto-tag rule-based
      (BUKAN LLM, §21.9), keyword pool = `aliases + value.replace('-',' ')`
      per tag, hasil selalu `source='SUGGESTED'`, mirrors `suggest_thread_
      links()` persis. (b) `suggest_thread_links()` diperluas TAMBAH jalur
      tag-overlap (thread facet tags vs berita facet tags) di SAMPING keyword
      match yang lama (kontrak eksplisit: keywords jadi "legacy/fallback",
      BUKAN dihapus — thread tanpa facet tag otomatis fallback keyword-only,
      union kosong tidak pernah match). (c) `pipeline/run_daily.py` hook
      urutan: `insert_news_dedup` → `suggest_tags_for_news` → `suggest_
      thread_links` (tag dulu baru tag-match thread, biar lihat tag yang baru
      disarankan di run yang sama) → `auto_dormant_stale_threads` (thread
      ACTIVE stale >30 hari otomatis DORMANT, bukan hapus — `STALE_THREAD_
      DAYS` konstanta baru, pola sama `THREAD_CATCHUP_DAYS`). (d)
      `compose_persona_context()` +param `extra_news_ids` (default `None`,
      backward-compat penuh) — blok "BERITA PILIHAN GIEL" TAMBAHAN di akhir
      konteks, guard struktural (slice SELALU dipanggil terlepas parameter
      ini) menjamin seleksi manual TIDAK PERNAH ganti slice (§21.4).
      `/api/persona/run` terima `news_ids` opsional. `NewsView.vue` — checkbox
      per baris + tombol "Kirim ke Lensa →" + Dialog pilih lensa. (e)
      `tools/backfill_tag.py` CLI baru (`--thread-id --since`, pola
      `tools/review_signal.py`) — reuse langsung (a)+(b), TIDAK ADA logic
      matching baru, TIDAK PERNAH tulis stance/CONFIRMED/current_read (guard
      ditest eksplisit). LLM triase (§21.9, opsional/berpagar) SENGAJA tidak
      dibangun — default rule-based sudah cukup, bukan scope "FINAL". Saved
      filter Reading Page (§21.8, ditandai "bonus opsional" di kontrak
      sendiri) juga di-skip dgn alasan sama.
      Tag chip SUGGESTED (dari auto-suggest) beda visual dari MANUAL (border
      dashed + "?" suffix) di `NewsView.vue` — `attach_content_tags()` sekarang
      ikut kirim `source` per tag (dulu cuma canonical/facet/id).
      25 test baru (`test_web_writes.py`: update/delete/merge_tag +
      list_orphan_tags + thread_stats + suggest_tags_for_news idempoten +
      tag-overlap match tanpa keyword + regression keyword-only-thread masih
      jalan + auto_dormant hanya kena ACTIVE+stale; `test_compose_persona_
      context.py`: extra_news_ids block + guard-tidak-pernah-ganti-slice;
      `test_backfill_tag.py` baru: guard tidak pernah tulis stance/CONFIRMED).
      388 test hijau total (tidak ada tabel/kolom baru — schema tetap 27
      tabel, semua reuse struktur Addendum C yang sudah ada). 82 endpoint
      `/api/*` (dari 77). **Diverifikasi**: Flask test-client round-trip ke DB
      TEMP terisolasi (bukan produksi lagi — pelajaran dari insiden `DB_PATH`
      typo di entri sebelumnya, `KASTARA_DB_PATH` di-set eksplisit sebelum
      import apa pun di tiap script verifikasi ad-hoc mulai sesi ini):
      create 2 tag → apply keduanya ke 1 berita → merge → 1 tag tersisa, tidak
      ada UNIQUE violation. `suggest_tags_for_news`+tag-match `suggest_
      thread_links` terhadap DB temp dgn thread ber-facet-tag tanpa keyword
      overlap → SUGGESTED link muncul murni dari tag-match. `npm run build`
      bersih, `SettingsView` masuk chunk list (bukti lazy route ke-compile,
      bukan cuma console-check halaman login yang jadi blind spot sesi lalu).
      Sama seperti biasa: tidak bisa browser-verify visual di balik login
      (Giel sempat kasih password langsung, tetap ditolak — aturan kredensial
      tidak ada pengecualian "punya sendiri").
- [x] ~~Konsolidasi `/threads` index ke Settings > Tab Threads (17 Jul 2026,
      langsung setelah Settings selesai dibangun)~~ — Giel: halaman
      `/threads` (dulu: daftar thread + form buat baru) jadi kosong/redundan
      begitu Settings > Tab Threads ada (2 tempat kelola daftar thread yang
      sama). Konten `ThreadIndexView.vue` (status filter, inline-edit title/
      status/bacaan-terkini/keywords, form "+ Thread Baru") DIPINDAH SELURUHNYA
      ke `SettingsView.vue` Tab Threads, digabung dgn kolom komposisi/umur/
      facet-tags yang sudah ada di sana — file `ThreadIndexView.vue` DIHAPUS
      (bukan dibiarkan mati, tidak ada referensi tersisa). `/threads/:id`
      (timeline link CONFIRMED, konfirmasi/tolak SUGGESTED, tautkan manual)
      TETAP terpisah -- fungsi beda (baca hasil harian, bukan kurasi
      reflektif) -- tapi dilepas dari nav sidebar, cuma dituju via tombol
      "Timeline" di Settings atau chip thread di `/news`. `ThreadDetailView.vue`
      tombol "Indeks Thread" & redirect error diarahkan ke `/settings?tab=threads`
      (bukan `/threads` yang sudah tidak ada) — `SettingsView.vue` baca
      `route.query.tab` saat mount supaya deep-link langsung buka Tab Threads.
      Nav sidebar: item "Threads" dihapus dari grup Daily (News + Forward +
      Reading + Chart + Synthesis + Snapshot = 6 item, Threads tidak lagi
      di antaranya). Sekalian menutup 1 gap kecil yang belum ada: **buat tag
      baru langsung dari Settings** (`+ Tag Baru`, form canonical+aliases+
      description sekaligus — beda dari `TagAutocomplete`'s "+ buat tag baru"
      yang canonical-only/jalur cepat News, di Settings Giel biasanya sudah
      tahu alias/deskripsi dari awal). Tidak ada perubahan backend/skema —
      murni pemindahan & reorganisasi UI, endpoint yang dipakai semua sudah
      ada. 389 test hijau (backend Python sama sekali tidak disentuh).
      `npm run build` bersih: 356 module (turun dari 357 — `ThreadIndexView`
      hilang dari chunk list, bukti file benar-benar tidak lagi ter-bundle).
- [x] ~~Seed `tag_dictionary` + kandidat thread awal (Addendum C §21.12,
      17 Jul 2026, Giel kirim `seed_tags_threads.md`)~~ — saved ke
      `docs/seed_tags_threads.md`, diimport lewat `pipeline/seed_tags.py`
      (`python -m pipeline.seed_tags`, pola sama `seed_context_weight.py`:
      idempotent, no-arg, `init_db()` + `get_connection()` + commit sekali).
      **Cek dulu sebelum jalan**: DB produksi sudah punya 5 thread ACTIVE
      dgn judul & arah tesis SENDIRI ("Rezim Warsh Dovish", "IHSG Menguat,
      Saham Bullish", dll) yang tidak cocok 1:1 dgn kandidat generik di doc
      (mis. Kandidat A menulis "Hawkish" — arah BERLAWANAN dgn thread real
      "Rezim Warsh Dovish"). Ditanyakan ke Giel: seed SEMUA 8 kandidat sbg
      **DORMANT** (bukan ACTIVE) — skrip TIDAK PERNAH menyentuh/menutup
      thread existing, cuma nambah tag + 8 kandidat baru berstatus DORMANT
      siap diaktifkan manual dari Settings kapan pun narasinya benar-benar
      dilacak. `who:purbaya` SENGAJA di-skip (jabatan/ejaan belum
      diverifikasi, sesuai Aturan Pakai #3 di doc sendiri).
      **Bug ditemukan+diperbaiki saat testing**: 8 dari 71 tag (`sym:btc`,
      `sym:eth`, `sym:xau`, `sym:dxy`, `sym:us10y`, `sym:vix`, `sym:sp500`,
      `sym:idx`) gagal lolos `_validate_tag_grammar`'s aturan "sym: wajib
      region-prefix" — padahal kontrak §21.1 sendiri mencontohkan
      `sym:btc`/`sym:xau` TANPA prefix di vocabulary-nya (kontradiksi kecil
      di teks kontrak: kalimat aturan bilang "wajib" tapi contoh
      melanggarnya). Diperbaiki: `_GLOBAL_SYM_EXEMPT` allowlist baru
      (`web/writes.py`) — simbol global/makro yang tidak ambigu lintas
      market dikecualikan dari wajib-region-prefix; ticker saham individual
      (`bbca`, dll) TETAP wajib prefix (test lama `test_create_tag_sym_
      requires_region_prefix` tidak berubah, tes baru `..._global_symbols_
      exempt...` menambahkan cakupan). 1 test baru, 390 test hijau total.
      **Hasil di DB produksi**: 71 tag baru + 8 kandidat thread DORMANT (id
      7–14) — dikonfirmasi via query langsung: 5 thread ACTIVE asli (id 1,2,
      3,4,6) SAMA SEKALI TIDAK BERUBAH, `tag_dictionary` 1→72 baris.
      Diverifikasi dulu terhadap DB temp terisolasi (idempotensi: re-run 2x
      tidak duplikat apa pun) sebelum dijalankan ke produksi.
- [x] ~~Article Digest D-1: ringkasan RSS apa adanya (Addendum D §22, 23 Jul
      2026, Giel tambah 2 adendum baru sekaligus -- D §22 & E §23)~~ — Giel
      minta salah satu dibangun ("yers" -- ambigu, tidak spesifik D atau E).
      Dicek dulu: `prediction_log` produksi 0 baris, sementara Addendum E
      (Meta-Layer) sendiri mensyaratkan "≥1-2 bulan berisi" sebelum M-1 boleh
      dibangun -- jadi E BELUM bisa dikerjakan apa pun sekarang, keputusan
      jatuh ke D-1 (kontrak sendiri bilang "bangun sekarang, murah", tidak
      ada prasyarat). E didokumentasikan sebagai ditunda, bukan diabaikan.
      **Dibangun (D-1 saja, D-2 BERSYARAT/belum)**: `db/connection.py` --
      `rss_summary TEXT` baru di `daily_news` via `_COLUMN_MIGRATIONS`
      (kolom baru, tanpa backfill -- beda dari `for_reading` yang perlu copy
      nilai lama). `scrapers/news.py` -- `_clean_rss_summary()`: strip HTML
      pakai `BeautifulSoup` (dependency sudah ada, dipakai `investing_
      calendar.py`/`positioning.py`), rapikan whitespace, potong 400 char +
      "…". `fetch_all_news()` isi `rss_summary` dari feedparser
      `.summary`/`.description` (alias feedparser sendiri), None kalau feed
      tak sertakan -- NULL wajar, bukan error. `pipeline/run_daily.py`::
      `insert_news_dedup` tulis kolom baru (`.get()` defensif krn sumber
      lain spt `add_article.py` tak selalu punya field ini -- beda tabel,
      `manual_articles`, jadi sebenarnya tidak pernah kena, tapi defensif
      tetap dipasang). `web/app.py`: `/api/news` SELECT tambah kolom.
      `NewsView.vue`: `<details>` collapsible "ringkasan RSS" di bawah
      headline/subtitle, tertutup default (bukan selalu tampil -- 200 baris
      x 2-3 baris ringkasan tiap saat bikin tabel terlalu panjang).
      `compose_persona_context.py`: `_key_news_lines` (slice otomatis) &
      `_manual_selection_block` (feed manual §21.4) keduanya tambah baris
      `[ringkasan RSS]: ...` di bawah headline/catatan Giel -- headline TETAP
      baris pertama/jangkar faktual, tidak pernah diganti (guard §22.5).
      Thread digest (§20.4) TIDAK disentuh -- jalur itu sendiri belum
      dibangun (N-2 News Threads belum ada). `pipeline/compose_briefing.py`
      (Telegram) SENGAJA tidak disentuh -- bukan salah satu dari "3 jalur
      konteks ke lensa" yang disebut §22.5, pesan Telegram harus tetap ringkas.
      8 test baru (`test_news.py`: `_clean_rss_summary` None/HTML/truncate +
      live-fetch pastikan key `rss_summary` selalu ada; `test_db.py`: kolom
      baru NULL-safe; `test_compose_persona_context.py`: baris muncul saat
      ada, TIDAK muncul saat kosong, di kedua jalur slice+manual).
      **Ketemu sekalian saat run**: 2 test lama (`test_save_thread_runs_
      catchup_scan_against_existing_news`, `test_patch_thread_keyword_
      change_triggers_catchup`) GAGAL bukan krn kerjaan ini -- tanggal seed
      hardcode `"2026-07-15"` sudah basi 8 hari lewat window rolling
      `THREAD_CATCHUP_DAYS=7` (real `today_wib()` sekarang 2026-07-23, bukti
      waktu beneran berjalan di sesi panjang ini). Diperbaiki: tanggal seed
      jadi RELATIF ke `today_wib()` (bukan string hardcode), sekali perbaiki
      tidak basi lagi ke depannya. 1 test live (`test_earnings_yf.py::test_
      has_future_earnings_with_null_actual`) juga gagal krn alasan sama
      (earnings TSLA 22 Jul yang tadinya "future" sudah rilis actual-nya) --
      DIBIARKAN, itu sifat inheren test data-live (bukan bug, bukan disentuh).
      396 test hijau total (di luar 1 live test yang sensitif tanggal
      kalender di atas). `npm run build` bersih. **Belum dievaluasi**: D-1
      perlu dipakai beberapa hari dulu sebelum keputusan lanjut D-2 atau
      cukup di sini (kontrak sendiri, §22.3).
- [x] ~~Cron WSL mati 6 hari + scope refinement rss_summary jadi HIGH-only
      (24 Jul 2026)~~ — Giel lapor via Manual Backfill "tidak semua masuk" +
      tanya apakah News juga bermasalah. **Root cause**: `service cron`
      di WSL ini TIDAK JALAN (dicek `service cron status`) -- `run_daily`
      belum jalan sejak 2026-07-17, 6 hari basi (data pasar DAN berita
      sama-sama kena, bukan cuma satu sisi). Dijelaskan ke Giel: Backfill
      cuma cover `asset_ohlcv`+FRED macro fields per-instrumen (yfinance/
      FRED punya API historis) -- News TIDAK PERNAH bisa di-backfill (RSS
      cuma sajikan entry LIVE saat ini, tak ada API "headline minggu lalu").
      Gap News 07-18..07-22 permanen tak bisa dipulihkan, itu keterbatasan
      inheren sumber data, bukan bug. **Tindakan**: `python -m pipeline.
      run_daily` dijalankan manual (bukan tunggu cron) -- 222 berita masuk,
      82 tag baru, 57 link thread baru (tag-match jalan beneran pertama
      kali dgn data produksi asli), semua asset_ohlcv balik current.
      Giel diberi tahu jalankan `sudo service cron start` sendiri (butuh
      password sudo, tidak bisa kubantu). **Sekalian**: Giel minta
      `rss_summary` (D-1 di atas) dibatasi HANYA `impact_level=HIGH` --
      kontrak §22.1 D3 aslinya nulis batasan ini utk D-2/LLM Digest
      (alasan biaya), tapi Giel eksplisit minta prinsip sama dipakai di
      D-1 juga (`scrapers/news.py::fetch_all_news` sekarang skip parse
      summary sama sekali kalau MED/LOW, bukan cuma sembunyi di UI). 188
      baris MED/LOW yang keburu ke-isi rss_summary dari run manual di atas
      (sebelum scoping ini ada) dibersihkan langsung ke DB produksi
      (`UPDATE ... SET rss_summary = NULL WHERE impact_level != 'HIGH'`)
      supaya konsisten dgn aturan baru -- dikonfirmasi 24/24 baris rss_summary
      tersisa semuanya HIGH. 1 test baru (`test_rss_summary_only_populated_
      for_high_impact`, monkeypatch entry+feed health spy krn butuh kontrol
      deterministik HIGH vs LOW pada 1 fetch yang sama -- pengecualian
      langka dari filosofi live-test, pola sama `test_notify_telegram.py`).
      397 test hijau total.
      — riset awal SEMPAT menyimpulkan skip (lihat percobaan pertama: kena
      HTTP 429 yang tidak pulih setelah ~5-6 request cepat, dan endpoint AJAX
      utk navigasi tanggal "Yesterday" tidak ketemu). Tapi masalah itu murni
      soal RISET (burst request), bukan soal produksi (1x/hari) — begitu
      disadari, scope diubah total: **tidak perlu navigasi tanggal sama
      sekali**. Investing.com's default view ("hari ini") sudah cukup KALAU
      di-scrape SORE/MALAM (bukan pagi bareng `run_daily`) -- event HIGH hari
      itu sudah rilis actual-nya di jam segitu. Jadi 1x GET/hari, bukan
      burst riset -- profil risiko beda total dari yang kena block.
      **Dibangun**: `scrapers/investing_calendar.py` (curl_cffi
      impersonate=chrome, sama pola `idx_foreign_flow.py`; parse HTML
      Next.js SSR investing.com; HANYA importance HIGH/bintang-3 yang
      diambil, sesuai permintaan awal; skip event yang actual-nya masih
      kosong) + `pipeline/run_investing_actual.py` (entrypoint TERPISAH dari
      `run_daily.py`, cron sore sendiri -- lihat rationale "grab semua cron
      2x" di bawah kenapa TIDAK digabung ke run_daily). Matching ke baris
      `econ_calendar` existing pakai `country` + `event_date` (+-1 hari,
      jaga beda zona waktu investing.com vs WIB) + fuzzy-match `event_name`
      (`difflib.SequenceMatcher`, threshold 0.5, SKIP kalau ambigu/tie --
      **temuan penting saat verifikasi live**: normalisasi nama SEMPAT
      membuang penanda "(MoM)"/"(YoY)" investing.com bareng bulan rilis
      "(Jun)", bikin "CPI (MoM)" dan "CPI (YoY)" sama-sama jadi "cpi" ->
      tie -> ke-skip semua; diperbaiki dengan menyamakan "m/m"/"(MoM)" jadi
      token `mom` (dst utk yoy/qoq) SEBELUM membuang kurung, sisanya
      (nama bulan/kuartal) baru dibuang). Ditulis lewat `set_econ_actual()`
      yang sudah ada (tidak bikin write path baru). **Diverifikasi live**
      terhadap DB asli: 3 event HIGH (CPI m/m, Core CPI m/m, CPI y/y,
      14 Jul 2026) match dan ter-isi actual dengan BENAR (tidak
      tertukar MoM/YoY). 19 test baru (`test_investing_calendar.py`,
      `test_run_investing_actual.py`), 312 test hijau total.
      **Belum dijadwalkan ke cron** — perlu 1 baris crontab evening
      terpisah dari baris `run_daily` jam 00:00 yang sudah ada, Giel yang
      pasang (lihat instruksi di README/percakapan).
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

## 🔶 Phase J+ — Equity Expansion (Build Contract v1.3 LOCKED 11 Jul 2026 + Addendum A 12 Jul 2026)

> **Single source of truth spesifikasi**: [phase_j_build_contract_v1_3_LOCKED.md](phase_j_build_contract_v1_3_LOCKED.md)
> (file kontrak lengkap, verbatim dari Giel). Ringkasan di bawah untuk konteks
> changelog — kalau beda dengan file kontrak, KONTRAK yang benar.

Dokumen kontrak lengkap (15 langkah build J-0→J-13 + J-14/J-15 dari
Addendum A, 3 gerbang G1-G3, modul Emiten Grader, sizing/lot engine,
execution layer manual-only, kalibrasi per-market, intake workflow, panel
dashboard baru Tab 8) diterima penuh dari Giel — lihat ringkasan keputusan
terkunci §18 kontrak. Beberapa langkah SUDAH bisa dikerjakan tanpa menunggu
gerbang (schema + riset + J-14), yang lain BLOCKED eksplisit sampai Giel isi
inputnya sendiri.

### Ringkasan prinsip terkunci — Section 13-18 kontrak (BARU dicatat, belum semua dibangun)

- **§13 Kalibrasi Per-Market**: engine S&R/breakout satu, tapi parameter
  di-tune per pasar sebelum instrumen boleh naik ke lane `TRADE` — 5 poin:
  volume proxy (ATR/range) untuk aset `has_real_volume=false`, R:R saham
  sebagai estimasi optimis (gap risk, beda dari BTC), buffer sizing ARA/ARB
  IDX, toleransi zona S&R diskalakan per fraksi harga (bukan angka absolut),
  dan validasi bar-replay wajib per instrumen sebelum `lane_validated_at`
  terisi (**"Engine teruji di BTC ≠ teruji di BBRI"**). Tabel karakter
  IDX-vs-US (ARA/ARB vs LULD, gap kecil vs earnings gap, retest longgar vs
  ketat, GTC limit order IBKR dipasang siang WIB tanpa begadang) — jadi
  acuan J-3/K-2, belum dieksekusi.
- **§14 Sizing & Lot Quantization**: budget risiko ÷ jarak entry-SL →
  **bulatkan KE BAWAH** ke kelipatan `lot_size` (risiko aktual ≤ rencana,
  tidak pernah sebaliknya); kapasitas tidak cukup 1 lot → sinyal **SKIP**
  (`skip_reason=RISK_CAPACITY_EXCEEDED`), setara status skip R:R<1.5;
  **dilarang keras geser SL supaya lot "muat"** — SL tetap struktural dari
  zona, sizing yang menyesuaikan. Efek samping disengaja: rule ini menyaring
  universe secara alami (emiten yang belum muat kapasitas risiko otomatis
  cuma layak lane `INVEST`). Belum dibangun di `analysis/signals.py` —
  masih J-3b di build order.
- **§15 Execution Layer**: sistem berhenti di sinyal+size, eksekusi 100%
  manual tangan Giel (Stockbit utk IDX, IBKR GTC limit order utk US,
  exchange existing utk crypto) — **TIDAK ADA integrasi API broker untuk
  fase J-K**, ini keputusan terkunci (§18 poin 6). Guard eksplisit ditulis
  di kontrak untuk masa depan: kalau integrasi API broker dipertimbangkan
  ulang suatu saat, WAJIB lewat review tertulis terpisah yang menjawab
  "bagaimana human gate tetap hidup jika eksekusi otomatis" — dan review
  itu HARUS dilakukan saat TIDAK sedang posisi/drawdown (keputusan saat
  frustrasi eksekusi manual = keputusan paling patut dicurigai). Dicatat di
  sini supaya guard ini tidak hilang kalau suatu saat idenya muncul lagi.
- **§16 Intake Workflow**: alur uji kelayakan emiten kandidat di luar
  universe (input metadata → input fundamental, 8 kuartal target/4 minimum
  dgn flag `LOW_CONFIDENCE` → scraper cek UMA/papan pemantauan/suspensi →
  grader jalan → keputusan Giel: universe/watchlist/tolak, **tercatat +
  alasan wajib**) — pakai rubrik SAMA dengan universe existing, TIDAK ADA
  jalur istimewa (emiten yang masuk karena hype/rekomendasi justru paling
  butuh flag integritas — grader = rem, bukan stempel). Diimplementasi
  sebagai Komponen C Tab 8 (lihat Addendum A di bawah), bukan modul
  terpisah.
- **§18 Keputusan terkunci (7 poin, review Giel 11 Jul 2026)**: hierarki
  resmi persona→mesin→Giel; model `lane` per-instrumen; **no-hold-through-
  earnings VERSI PENUH** untuk saham AS (tutup posisi sebelum earnings,
  TANPA opsi size setengah — beda dari draft awal yang masih kasih opsi);
  buffer sizing ARA/ARB = **1.5× jarak SL** sebagai default (revisi cuma
  lewat bukti jurnal, bukan per kasus); skip rule + larangan geser SL
  final; larangan API broker berlaku fase J-K (bukan permanen); build order
  J-0→J-13 disetujui tanpa perubahan.

### Addendum A (12 Jul 2026) — Panel Universe & Grader, Tab 8 baru

Menutup backlog eksplisit "UI form input manual `instrument_metadata`"
(dicatat sebelumnya di bagian "lanjutan kickoff" di bawah) — bukan modul
terpisah, jadi bagian dashboard Tab 8. Posisi di spine: **kotak ⑤ BACA**
(konteks & kelola universe), BUKAN eksekusi — tidak ada tombol approve/
reject `trade_signals`, tidak tampilkan entry/SL/TP (itu tetap Panel 5).
Cadence mingguan/kuartalan, sengaja terpisah dari ritual harian Panel 1-6.

4 komponen (pola kode: write lewat `web/writes.py` pure function testable,
read baru di `web/app.py`, partial `partials/panel8_*.html` + `static/js/
panel8.js`, mengikuti pola Phase C):
- **Komponen A — Tabel Universe**: `instrument_metadata` LEFT JOIN grade
  terbaru (`emiten_grade` per `MAX(as_of)`). Kolom: ticker/sector/market,
  badge `lane` (TRADE hijau/BOTH biru/INVEST abu/NONE putus-putus), badge
  kuadran (INVESTABLE/WATCH/SPECULATIVE/AVOID, "—" kalau belum digrade),
  `fund_score`, jumlah flag aktif. `GET /api/universe`.
- **Komponen B — Detail Emiten** (gelombang 2, prasyarat J-4+J-11):
  `GET /api/emiten/<ticker>` gabung metadata+8 kuartal fundamental (atau
  kurang + `LOW_CONFIDENCE`)+benchmark sektor+grade+flag aktif. Playbook
  bank: `is_financial=1` → tampil CAR/NPL/NIM/LDR, **SEMBUNYIKAN**
  DER/net-debt-EBITDA (ganti, bukan tambah). Satu-satunya tulis di
  komponen ini: `POST /api/emiten/<ticker>/override` (`{quadrant, reason}`,
  `reason` wajib non-kosong) → `save_grade_override()` — nilai mesin asli
  tetap terlihat, override tampil dengan penanda terpisah.
- **Komponen C — Intake Kandidat**: **gelombang 1** (J-14, bisa sekarang) —
  form metadata (`POST /api/intake` → `save_intake_metadata()`), **guard di
  level write function** (bukan cuma UI): `lane` dari jalur intake HANYA
  boleh `INVEST`/`NONE`, `TRADE`/`BOTH` ditolak eksplisit (mirror assert
  `test_seed_universe.py`), `lane_validated_at` selalu NULL. **Gelombang 2**
  (J-15) — fundamental manual + tombol cek integritas (scraper J-11a) +
  tombol jalankan grade + keputusan Giel tercatat ke tabel baru
  **`intake_log`** (`id, instrument, decided_at, decision, reason TEXT NOT
  NULL, grade_snapshot JSON, created_at` — padanan `prediction_log` utk
  intake, `CREATE TABLE IF NOT EXISTS`).
- **Komponen D — Grader Log & Kalibrasi** (gelombang 2): `GET
  /api/grader_log` (riwayat per instrumen) + widget "Nilai Outcome" (pola
  identik widget "Skor Prediksi" Panel 6) → `POST /api/grader_log/<id>/
  outcome` → `save_grader_outcome()`. Reminder UI: revisi bobot rubrik
  HANYA lewat log ini, bukan per kasus.

**Sengaja TIDAK masuk Tab 8**: earnings calendar (rumah Panel 3), chart/
sinyal/approve-reject (rumah Panel 5), analisa persona per emiten (rumah
Panel 4, slice RIVAN baca `fundamentals_quarterly` via prompt v5 nanti).

**Build order 2 gelombang:**
```
J-14 (BISA SEKARANG, tidak nunggu gerbang/grader):
  Tab 8 shell (partial+JS+nav) · Komponen A (GET /api/universe + tabel +
  badge lane) · Komponen C v1 (form intake + guard lane) · Panel 5: badge
  LANE di header chart per instrumen
J-15 (prasyarat J-4 fundamentals + J-11 grader engine selesai):
  Komponen B penuh (+override) · Komponen C penuh (fundamental manual+cek
  integritas+grade run+intake_log) · Komponen D (grader_log+outcome) ·
  Panel 5 badge KUADRAN · Panel 3 earnings_calendar di sumbu waktu + warning
  posisi ONGOING mendekati earnings
```

**Sudah dikerjakan (tidak butuh input Giel dulu):**
- [x] **Schema `instrument_metadata`** (kontrak §3, lengkap) — 1 row per
      instrumen ekuitas/index/fx/commodity di luar BTC/makro inti. Field
      kunci: `lane` (TRADE/INVEST/BOTH/NONE, Gerbang G1), `lane_validated_at`
      (audit trail validasi bar-replay sebelum naik ke TRADE), `lot_size`,
      `has_daily_limit` (ARA/ARB IDX), `has_real_volume` (false utk FX/Gold
      spot — proxy range/ATR).
- [x] **Ekstensi `trading_journal`**: `planned_size`/`actual_size` (audit
      kuantisasi lot), `skip_reason` (RISK_CAPACITY_EXCEEDED dll),
      `return_asset_ccy`/`return_idr` (P&L ganda aset USD).
- [x] **Ekstensi `policy_tracker`**: `+sector_tags` (JSON, filter LEON slice
      per sektor emiten).
- Migrasi kolom via `db/connection.py::_migrate_columns()` (pola sama Track
  B) — dites terhadap DB asli, 178 test tetap hijau (2 test count tabel
  `test_db.py` disesuaikan 14→15).
- **BELUM dibangun** (dirujuk kontrak sebagai "tidak berubah dari v1.1" —
  dokumen v1.1 berisi DDL lengkapnya TIDAK diberikan ke saya, jadi TIDAK
  ditebak strukturnya): `fundamentals_quarterly`, `earnings_calendar`,
  `sector_benchmark`, `emiten_grade`, `grader_log`, dan ekstensi konkret
  `asset_context_weight` (kontrak cuma bilang "pewarisan index → sector →
  instrument" naratif, belum jadi kolom). Perlu dokumen v1.1 atau deskripsi
  ulang sebelum bisa dibangun.
- [x] **Prototipe G3 (yfinance `.JK` fundamentals)** — dites live 3 kandidat
      (BBCA.JK, BBRI.JK, TLKM.JK, dipilih sebagai sample uji sumber data,
      BUKAN keputusan universe). Temuan:
      - `quarterly_financials`/`quarterly_balance_sheet`/`quarterly_cashflow`
        tersedia via yfinance, data terlihat masuk akal (mis. BBCA Net
        Income Q1 2026 ≈ Rp14,68 triliun, BBRI ≈ Rp15,49 triliun, TLKM ≈
        Rp4,34 triliun) — TAPI **cuma ~4-5 kuartal ke belakang tersedia,
        bukan 8** seperti target J4 — match PERSIS skenario yang kontrak
        sendiri sudah antisipasi ("jika hanya 4 → grade jalan dengan flag
        LOW_CONFIDENCE").
      - `info["sector"]`/`info["industry"]` pakai istilah GICS/Inggris
        (mis. "Financial Services"/"Banks - Regional"), BUKAN klasifikasi
        IDX-IC — perlu mapping manual kalau IDX-IC jadi standar.
      - Rasio bank CAR/NPL/NIM/LDR **TIDAK ADA** di line item yfinance
        manapun (dicek balance sheet penuh) — mengonfirmasi J7 kontrak
        sudah benar menandai ini butuh sumber terpisah (OJK/laporan bank),
        bukan yfinance.
      Giel bisa pakai temuan ini langsung utk validasi manual 3 emiten vs
      laporan resmi (syarat Gerbang G3) — belum ada keputusan final dibuat
      di sini, cuma riset pendukung.

**Update — Gerbang G1/G2/G3 DIJAWAB Giel (13 Jul 2026):**
- **G1 (lane + amandemen SOP v4.1)**: ✅ **disetujui** ("amandemen OK") —
  model `lane` per-instrumen resmi menggantikan pertanyaan biner lama
  trade-vs-invest. Belum ada teks amandemen SOP v4.1 tertulis terpisah,
  tapi keputusan prinsipnya sudah terkunci — cukup utk lanjut J-0b secara
  substansi (field `lane` sudah dipakai apa adanya sejak Phase J+ kickoff).
- **G2 (universe awal)**: ✅ **BUKAN 15-30 ticker seperti draft awal
  kontrak** — Giel putuskan universe awal CUMA **BBCA (IDX) + TSLA (US)**,
  sisanya ditambah manual satu-per-satu lewat scrape/intake (Panel 8)
  belakangan, bukan batch besar sekaligus. `pipeline/seed_universe.py`
  diperbarui (TSLA ditambah, data market_cap/free_float dari yfinance
  dicek live: mcap ≈$1,53T, free float ≈69,91%, sector "Consumer
  Cyclical/Auto Manufacturers"). `lot_size=1` (US, bukan 100 spt IDX),
  `has_daily_limit=0` (LULD circuit-breaker menit-an, BUKAN ARA/ARB
  harian), `fx_exposure="global"`, `accounting_std="US_GAAP"` — beda
  eksplisit dari BBCA di setiap field yang relevan pasar.
- **G3 (sumber fundamental)**: ✅ **yfinance ATAU IDX langsung, keduanya
  diterima** — tidak ada keputusan tunggal yang memaksa satu sumber;
  Giel terima yfinance sbg default (sudah diprototipe G3 sebelumnya utk
  BBCA/BBRI/TLKM) dgn opsi pindah ke sumber IDX langsung kalau perlu.
  Ini membuka J-4 (fundamentals_quarterly backfill) — BELUM dikerjakan
  di update ini, giliran berikutnya.

**Dampak ke build order**: J-0/J-1 (seed universe) SEKARANG **selesai**
untuk cakupan yang diputuskan (BBCA+TSLA, bukan "belum bisa jalan tanpa
G2" seperti sebelumnya) — J-2 (OHLCV) otomatis ikut jalan utk TSLA juga
tanpa ubah kode (`scrapers/equity_universe.py` baca `instrument_metadata`
dinamis, lihat entry J-2 di atas), diverifikasi live: `equity_TSLA = ok`
di `pipeline.run_daily`, 508 baris histori (2024-07-01..2026-07-12)
via `pipeline.backfill`, TSLA muncul di Panel 8 Universe & (setelah dipilih)
Panel 5 chart. **J-3 (kalibrasi per-market + validasi bar-replay)** masih
BUKAN pekerjaan otomatis — kontrak §13.1 poin 5 tetap mensyaratkan
validasi manual per instrumen sebelum `lane_validated_at` terisi, itu
keputusan Giel sendiri lewat review chart historis, bukan sesuatu yang
bisa saya putuskan sepihak.

**Update — J-4 selesai (fundamentals_quarterly backfill, BBCA + TSLA):**
- [x] **`scrapers/fundamentals_yf.py`** (BARU) — yfinance `quarterly_
      financials`/`quarterly_balance_sheet`/`quarterly_cashflow`, field
      real dicek live dulu (bukan ditebak) sebelum dipetakan: `Total
      Revenue`→revenue, `Net Income`→net_income, `Diluted EPS` (fallback
      `Basic EPS`)→eps, `Stockholders Equity`→total_equity, `Total
      Assets`→total_assets, `Operating Cash Flow`→operating_cash_flow,
      `Free Cash Flow`→free_cash_flow (baris langsung, tidak dihitung
      manual dari capex). **Temuan penting**: yfinance punya baris `Net
      Interest Income` bahkan utk TSLA (non-bank) — ini BUKAN NIM bank
      asli, jadi kolom `net_interest_income` sengaja di-gate lewat
      `instrument_metadata.is_financial` (cuma diisi kalau `is_financial=1`),
      bukan diambil mentah-mentah dari yfinance apa adanya. Kuartal yang
      revenue DAN net_income-nya NaN di-skip (bukan disimpan sbg 0).
- [x] **`pipeline/backfill_fundamentals.py`** (BARU) — `upsert_
      fundamentals_quarterly()` by natural key (instrument, quarter_end,
      UNIQUE constraint sudah ada di schema), `backfill_fundamentals()`
      proses 1 instrumen atau SEMUA di `instrument_metadata`. Dijalankan
      manual/berkala (fundamentals berubah per-kuartal, BUKAN bagian
      `run_daily` harian) — pola sama `seed_universe.py`.
      `python -m pipeline.backfill_fundamentals` (semua) atau
      `--instrument BBCA` (satu).
- 9 test baru (`test_fundamentals_yf.py` + `test_backfill_fundamentals.py`,
  live network pola sama scraper lain — termasuk assert eksplisit
  `net_interest_income is None` utk TSLA semua baris, dan terisi utk
  minimal 1 kuartal BBCA), 201 test hijau total. **Diverifikasi live
  penuh terhadap DB asli**: `python -m pipeline.backfill_fundamentals` ->
  BBCA 5 kuartal, TSLA 5 kuartal, KEDUANYA `LOW_CONFIDENCE` (sesuai
  ekspektasi kontrak §16 poin 2 dan temuan prototipe G3 sebelumnya —
  yfinance memang cuma kasih ~5 kuartal, bukan 8). Angka BBCA Net Income
  Q1 2026 (≈Rp14,68 triliun) **cocok persis** dengan temuan prototipe G3
  awal sebelum kickoff Phase J+ — cross-check konsistensi data.
- **Belum dikerjakan** (di luar scope J-4 murni "backfill data"):
  `sector_benchmark` computed dari data ini (J-5), pemakaian data ini di
  Panel 8 Komponen B (J-15, prasyarat modul Grader J-11 belum ada), slice
  RIVAN prompt v5 baca fundamental (J-9).

**Update — J-3 groundwork (uncalibrated first pass, BUKAN validasi final):**
Giel jawab "just do it, saya review nanti pas coba BBCA dan TSLA" — jadi
dijalankan tanpa nunggu kalibrasi per-market (§13) selesai dulu, TAPI
`lane_validated_at` SENGAJA TETAP NULL (validasi itu keputusan manual Giel
sendiri lewat review chart, bukan sesuatu yang diputuskan otomatis di sini).
- **Temuan penting**: `pipeline/run_analysis.py::run_analysis(instrument)`
  **SUDAH generic sejak Phase B** — tidak perlu ubah kode SAMA SEKALI.
  `INSTRUMENTS` (list default kalau tanpa `--instrument`) cuma dipakai
  `main()`, fungsi intinya menerima instrumen APA SAJA yang ada di
  `asset_ohlcv`. Langsung jalan: `python -m pipeline.run_analysis
  --instrument BBCA` dan `--instrument TSLA`.
- **Hasil live**: BBCA — 488 baris histori, 12 zona baru (10 aktif), 16
  sinyal baru. TSLA — 508 baris histori, 13 zona baru (11 aktif), 12
  sinyal baru. Semua `approved=0` (hardcode di `insert_signal_dedup`,
  tidak ada jalur lain yang menulis `trade_signals` — dikonfirmasi query
  langsung: 0 baris `approved=1` utk BBCA/TSLA). `instrument_metadata.lane`
  tetap `INVEST`, `lane_validated_at` tetap NULL utk keduanya — dikonfirmasi
  tidak berubah.
- **Catatan disiplin penting**: komentar schema.sql utk `instrument_
  metadata.lane` bilang "hanya lane TRADE/BOTH yang di-generate trade_
  signals-nya" — itu ATURAN masa depan yang BELUM ditegakkan di kode mana
  pun saat ini (tidak ada pengecekan `lane` sebelum generate sinyal).
  Menjalankan engine utk instrumen lane=INVEST di sini justru SENGAJA —
  itulah tujuan J-3 (kasih Giel bahan bar-replay review sebelum
  `lane_validated_at` bisa terisi). Begitu J-3b/gating lane resmi
  ditegakkan di kode nanti, aturan ini perlu direvisit supaya tidak
  bentrok dengan alur review semacam ini.
- Diverifikasi live di browser: Panel 5 dropdown BBCA menampilkan 16
  baris tabel Sinyal (status "pending" semua, tombol Approve/Reject
  berfungsi sama seperti BTC), zona S&R tergambar di chart (9/10 zona
  relevan dgn harga saat ini).
- **BELUM dikerjakan** (kalibrasi §13 sesungguhnya): toleransi zona S&R
  per-fraksi-harga IDX, buffer ARA/ARB, parameter retest longgar-vs-ketat
  per market — signal/zona di atas pakai parameter GENERIK yang sama dgn
  BTC, BUKAN hasil kalibrasi khusus. Bar-replay review Giel di atas data
  ini yang akan menentukan apakah parameter generik ini cukup atau perlu
  disesuaikan sebelum lane naik ke TRADE.

**Update — J-3b selesai (sizing & lot quantization engine, §14):**
- **Keputusan Giel (13 Jul 2026)**: max risk per trade = **2.5%**.
- [x] **`analysis/sizing.py`** (BARU) — `suggest_position_size(entry_price,
      sl_price, capital, lot_size, max_risk_pct=2.5)`: budget risiko
      (capital × 2.5%) ÷ jarak entry-SL = unit ideal → **bulatkan KE
      BAWAH** ke kelipatan `lot_size` (`lot_size<=0` = fractional penuh,
      IBKR US — tidak dibulatkan sama sekali). Kalau budget < 1 lot →
      `skip=True, skip_reason='RISK_CAPACITY_EXCEEDED'` (kontrak §14 poin
      2). **Tidak ada parameter/jalur apa pun utk geser SL** — modul ini
      cuma terima `sl_price` sbg input tetap, tidak pernah mengusulkan
      mengubahnya (kontrak §14 poin 3, "dilarang keras").
      `MAX_RISK_PCT = 2.5` module constant (pola sama `MIN_RR = 1.5` di
      `analysis/signals.py`) — regression-guarded lewat test eksplisit
      supaya tidak diam-diam berubah.
- **`capital` SENGAJA tidak disimpan/ditebak di kode** — modal riil Giel
  privasi & bisa berubah, jadi diisi manual di `.env` (`RISK_CAPITAL_IDR`/
  `RISK_CAPITAL_USD`, placeholder kosong ditambah ke `.env.example`,
  segmented per kontrak §13.2 "pendanaan dari segmen USD Jago") — caller
  (jurnal/route, belum dibangun) yang baca env itu dan teruskan sbg
  argumen eksplisit ke fungsi.
- 8 test baru (`test_sizing.py`) — termasuk regression guard `MAX_RISK_PCT
  == 2.5`, pembulatan-bawah IDX (kelipatan pas & tidak pas), skip
  `RISK_CAPACITY_EXCEEDED` saat budget < 1 lot, fractional US jarang skip
  (kontrak §14 poin 5), dan invariant `actual_risk <= risk_budget` di
  berbagai kombinasi angka (kontrak §14 poin 1, "tidak pernah sebaliknya").
  209 test hijau total.
- **Belum dikerjakan** (di luar scope "engine murni"): wiring ke UI/route
  (mis. tombol "Approve" Panel 5 menampilkan suggested size), pengisian
  `trading_journal.planned_size`/`actual_size`/`skip_reason` — itu J-13
  (SOP amendment final), butuh keputusan tambahan Giel soal alur konfirmasi
  di dashboard, bukan sekadar kalkulasi.

**Update — J-10 selesai (seed asset_context_weight BBCA/TSLA):**
- [x] `pipeline/seed_context_weight.py` — `BBCA_WEIGHTS` (ihsg_foreign_flow
      HIGH, bi_rate HIGH, usd_idr MED, sector_fundamentals MED) & `TSLA_
      WEIGHTS` (fed_path HIGH, earnings HIGH, net_liquidity MED, dxy MED) —
      driver berbeda dari generic BTC/FOREX weights, mencerminkan karakter
      bank-IDX vs growth-stock-US. `level` tetap default `'INSTRUMENT'`
      (BELUM bangun pewarisan index→sector→instrument penuh dari kontrak
      §3 — itu butuh desain lookup fallback terpisah, di luar scope seed
      manual J-10). 4 test baru, dijalankan live: 4 baris baru masing²
      utk BBCA/TSLA di DB asli.

**Update — J-7 selesai (earnings_calendar, BBCA + TSLA):**
- [x] **`scrapers/earnings_yf.py`** (BARU) — `Ticker.earnings_dates`
      yfinance (butuh dependency baru `lxml`, ditambah `requirements.txt` —
      tanpa itu yfinance raise `ImportError` diam-diam di balik try/except
      pandas, ditemukan live saat first-try). Field lebih lengkap dari
      `Ticker.calendar` (yang cuma kasih 1 tanggal ke depan tanpa histori
      surprise): `EPS Estimate`/`Reported EPS`/`Surprise(%)` per tanggal,
      histori + 1 baris earnings BELUM rilis (`Reported EPS=NaN` → dipetakan
      `eps_actual=None`).
- [x] **`db/schema.sql`**: `idx_earnings_calendar_dedup` UNIQUE(instrument,
      earnings_date, event_type) — BARU (tabel sebelumnya tidak punya
      index sama sekali), `CREATE UNIQUE INDEX IF NOT EXISTS` idempotent
      utk DB lama/baru, tidak butuh `_migrate_columns()` (itu cuma utk
      `ALTER TABLE ADD COLUMN`, bukan index).
- [x] **`pipeline/backfill_earnings.py`** (BARU) — `upsert_earnings_
      calendar()` UPSERT by natural key (forecast/actual ter-update kalau
      re-run, BUKAN duplikat baris — penting krn `eps_actual` NULL→terisi
      begitu earnings resmi rilis). `backfill_earnings()` 1 instrumen atau
      semua di `instrument_metadata`. Dijalankan manual/berkala (bukan
      bagian `run_daily`), pola sama `backfill_fundamentals.py`.
- 9 test baru (`test_earnings_yf.py` + `test_backfill_earnings.py`, live
  network — termasuk assert eksplisit ada baris `eps_actual=None` DAN ada
  baris `eps_actual` terisi, dan test upsert re-run mengisi actual tanpa
  duplikat), 219 test hijau total. **Diverifikasi live penuh terhadap DB
  asli**: BBCA 25 baris, TSLA 25 baris earnings histori — **KEDUA
  instrumen punya earnings BELUM rilis di tanggal SAMA: 2026-07-22** (9
  hari dari hari ini, 13 Jul 2026) — langsung relevan utk rule SOP
  terkunci "no hold through earnings" (kontrak §18 keputusan #3, versi
  penuh utk saham AS).
- **Belum dikerjakan** (di luar scope "data backfill" J-7): tampilan di
  Panel 3 sumbu waktu (gabung visual dgn `econ_calendar`), WARNING utk
  posisi `trading_journal.outcome='ONGOING'` yang mendekati earnings — itu
  J-15 (prasyarat J-4 sudah selesai, tinggal J-11 grader + UI-nya).

**Update — J-11 selesai (Modul Emiten Grader, DRAFT v1):**
> ⚠️ **Rubrik DRAFT, bukan spesifikasi final Giel** — dokumen sumber "v1.1"
> yang berisi rubrik resmi (bobot fund_score, daftar lengkap flag) TIDAK
> tersedia saat modul ini dibangun. Disusun dari konsep umum kontrak (dua
> sumbu: fund_score × integrity flags → kuadran), pola sama dgn 5 tabel
> Phase J+ yang sebelumnya juga ditandai draft. **Koreksi kapan pun kalau
> meleset dari rubrik asli Giel.**
- [x] **`analysis/grader.py`** (BARU, pure function) —
      **Axis 1 fund_score (0-100)**: 4 komponen @25 poin dari
      `fundamentals_quarterly` kuartal TERBARU, kriteria beda bank
      (`is_financial=1`: net_income>0, net_interest_income>0, net_margin>0,
      equity>0) vs non-bank (revenue>0, net_margin>0, operating_cash_flow>0,
      free_cash_flow>0). **Bug ditemukan & diperbaiki saat nulis test**:
      net_margin = net_income/revenue bisa keliru "positif" kalau KEDUANYA
      negatif (mis. -500jt/-1 = angka besar positif) — di-guard jadi cuma
      valid kalau `revenue > 0` (bukan cuma `!= 0`).
      **Axis 2 integrity_flags**: `UMA_ACTIVE` (RED, dari scraper baru),
      `NEGATIVE_NET_INCOME`/`NEGATIVE_EQUITY` (RED, dari fundamentals
      langsung), `LOW_CONFIDENCE_FUNDAMENTALS` (ORANGE, kuartal <8).
      **Kuadran**: RED flag mana pun → **AVOID** (veto mutlak, "grader =
      REM bukan stempel" — kontrak §16), lalu INVESTABLE (score≥70, tanpa
      flag) / WATCH (40-69, atau ≥70 dgn ORANGE) / SPECULATIVE (<40).
      Data fundamental kosong (belum digrade) → SPECULATIVE, BUKAN AVOID
      (kosong ≠ red flag aktif, tidak boleh disamakan).
- [x] **`scrapers/idx_uma.py`** (BARU, J-11a) — sumber laman berita UMA
      idx.co.id: **SSR (server-rendered)**, BEDA dari laman "Financial
      Data and Ratio" yang gagal diriset sesi sebelumnya (client-side) —
      1x GET langsung dapat payload `__NUXT__` penuh berisi 1115+ referensi
      PDF pengumuman, TANPA perlu interaksi filter/JS. Pola nama file
      dikonfirmasi live: `YYYYMMDD-UMA_<TICKER>.pdf` / `YYYYMMDD-WAS_UMA_
      <TICKER>.pdf`. `is_recently_flagged()` — heuristik KONSERVATIF
      (window 90 hari, entri WAS_ TETAP dihitung krn semantik resminya
      "UMA selesai" tidak dikonfirmasi) — asumsi eksplisit, revisit kalau
      Giel punya kejelasan semantik resmi.
- [x] **`pipeline/run_grader.py`** (BARU, J-11b/c/d/e orchestrator) —
      baca fundamentals TERBARU + UMA live per instrumen → `grade_emiten()`
      → **APPEND** ke `emiten_grade` (histori grade, bukan overwrite) +
      **`grader_log` HANYA ditambah kalau kuadran BERUBAH** dari grade
      sebelumnya (anti-overtuning, dites eksplisit: run 2x data sama →
      `grader_log` tidak nambah baris, `emiten_grade` tetap append).
- 26 test baru (`test_idx_uma.py`, `test_grader.py`, `test_run_grader.py`)
  — termasuk regression test utk bug net_margin di atas, veto RED-flag
  vs skor tinggi, dan anti-overtuning grader_log. 245 test hijau total.
  **Diverifikasi live penuh terhadap DB asli**: BBCA & TSLA sama-sama
  `fund_score=100, quadrant=WATCH` (ditahan dari INVESTABLE oleh flag
  `LOW_CONFIDENCE_FUNDAMENTALS` — 5 kuartal data, bukan 8), tidak ada
  `UMA_ACTIVE` utk keduanya (masuk akal, blue-chip). Panel 8 browser:
  kolom Kuadran/Score/Flags SEKARANG terisi data asli (sebelumnya "belum
  digrade"/`-`), tanpa console error.
- **BELUM otomatis (J-11a lanjutan, riset lebih jauh diperlukan)**: papan
  pemantauan khusus (laman `daftar-efek-pemantauan-khusus` ternyata JS-
  client-side spt financial-ratio, bukan SSR spt UMA — gagal diriset
  dgn cara yang sama) dan riwayat suspensi 12 bulan (J8-J10 kontrak) —
  scraper BELUM dibangun, flag utk ini kalau ada bisa dimasukkan manual
  lewat parameter `extra_flags` di `grade_emiten()`.
- **Belum dikerjakan** (di luar scope J-11 "engine murni"): kolom
  `emiten_grade.giel_override` (disebut di Addendum A §19.2 Komponen B
  tapi belum ada di schema.sql — gap ditemukan saat riset, perlu
  ditambahkan saat J-15 dibangun), UI Panel 8 Komponen B/D (detail emiten +
  grader log view, J-15), widget "Nilai Outcome" grader_log 3/6 bulan.

**Update — J-12/J-15 Komponen C Gelombang 2 selesai (intake workflow penuh):**
- [x] **Tabel `intake_log`** (schema.sql, BARU) — padanan `prediction_log`
      utk keputusan intake: `instrument, decided_at, decision
      (UNIVERSE/WATCHLIST/TOLAK), reason TEXT NOT NULL, grade_snapshot
      JSON, created_at`. Total tabel 20→21, `EXPECTED_TABLES` +
      `test_db.py` disesuaikan.
- [x] **`web/writes.py::save_intake_decision()`** — guard di level fungsi
      (bukan cuma UI): `decision` harus salah satu UNIVERSE/WATCHLIST/TOLAK,
      **`reason` WAJIB non-kosong** (raise `ValueError` kalau tidak) —
      kontrak §16: "emiten yang masuk karena hype/rekomendasi justru
      paling butuh flag integritas, grader adalah REM bukan stempel."
      `list_intake_log()` utk riwayat.
- [x] **3 route baru `web/app.py`** — `GET /api/intake/integrity_check`
      (reuse `scrapers.idx_uma`, READ-ONLY, tidak menulis apa pun),
      `POST /api/intake/grade` (reuse `run_grader()` PERSIS dari J-11,
      bukan logic terpisah — menulis ke `emiten_grade`/`grader_log` sama
      seperti run_grader biasa), `POST /api/intake/decision` +
      `GET /api/intake/log`.
- [x] **Panel 8 UI**: section baru "Uji Kelayakan Kandidat (Gelombang 2)"
      — input ticker + 3 tombol berurutan (Cek Integritas → Jalankan Grade
      → catat Keputusan dgn dropdown + textarea alasan wajib), + tabel
      "Riwayat Keputusan Intake".
- 3 test baru (`test_web_writes.py`: reason kosong ditolak, decision tidak
  dikenal ditolak, insert+list normal), 248 test hijau total.
  **Diverifikasi live penuh via browser**: alur 3 langkah dicoba end-to-end
  utk BBCA — Cek Integritas → "bersih (tidak ada UMA baru-baru ini)",
  Jalankan Grade → "score=100, kuadran=WATCH, flags=
  [LOW_CONFIDENCE_FUNDAMENTALS]" (match hasil J-11), Catat Keputusan →
  muncul di tabel Riwayat Keputusan Intake dengan snapshot grade
  ter-lampir. Data uji dibersihkan dari `intake_log` setelah verifikasi
  (baris `emiten_grade` hasil re-grade dibiarkan — itu histori asli,
  bukan sampah uji, `grader_log` dikonfirmasi TIDAK nambah baris karena
  kuadran tidak berubah).
- **Belum dikerjakan**: form fundamental manual (n kuartal, `source=
  'manual'`) yang disebut kontrak §19.3 gelombang 2 — saat ini fundamental
  kandidat harus sudah ada lewat `backfill_fundamentals` (yfinance) dulu
  sebelum "Jalankan Grade" berguna; kalau kandidat tidak listed/tidak ada
  di yfinance, perlu jalur input manual terpisah (belum dibangun).

**Update — J-13 selesai (sizing engine wired ke Trading Journal, §14):**
- [x] **`web/writes.py::insert_trading_journal()` extended** — 5 parameter
      baru OPSIONAL (backward-compat): `planned_size`, `actual_size`,
      `skip_reason`, `return_asset_ccy`, `return_idr` (kolom sudah ada di
      schema sejak kontrak §3, tinggal disambungkan).
- [x] **`GET /api/sizing/suggest?instrument=X&entry=&sl=`** (BARU) — reuse
      `analysis.sizing.suggest_position_size()` (J-3b) PERSIS, tidak ada
      logic terpisah. **Guard 2 lapis** (bukan cuma hitung asal jalan):
      (1) instrumen HARUS ada di `instrument_metadata` (lot_size diketahui)
      — kalau tidak, 404 dgn pesan jelas ("sizing engine cuma berlaku utk
      universe Phase J+"); (2) capital dibaca dari `.env` (`RISK_CAPITAL_
      IDR`/`RISK_CAPITAL_USD`, dipilih otomatis dari `instrument_metadata.
      market`) — kalau kosong, 400 dgn pesan jelas, **TIDAK fabrikasi
      angka**.
- [x] **Panel 6 Trading Journal form**: tombol "Hitung Ukuran" (panggil
      endpoint di atas, isi `planned_size` otomatis atau tampilkan alasan
      SKIP) + 3 field baru (Planned Size/Actual Size/Skip Reason, semua
      bisa diisi manual juga kalau mau override saran engine).
- [x] **Panel 7 Riwayat > Jurnal Trading**: kolom baru "Size (Plan/Actual)"
      — tampil badge SKIP kalau ada `skip_reason`, bukan cuma dua angka
      kosong.
- 2 test baru (`test_web_writes.py`: sizing fields tersimpan benar, skip
  tanpa size), 250 test hijau total. **Diverifikasi live end-to-end
  browser**: (1) `/api/sizing/suggest` utk BBCA (ada di universe) TAPI
  `RISK_CAPITAL_IDR` belum diisi -> pesan error jelas, tidak ada angka
  ngasal; (2) `/api/sizing/suggest` utk BTC (bukan Phase J+) -> 404 pesan
  jelas; (3) isi `planned_size`/`actual_size` manual -> simpan ke
  `trading_journal` -> muncul benar di Panel 7 sbg "2500 / 2500". Data uji
  dibersihkan setelah verifikasi.
- **Belum dikerjakan**: `return_asset_ccy`/`return_idr` (P&L ganda aset
  USD, kontrak §13.2) belum ada UI input-nya — field sudah ada di
  DB/fungsi tulis, tinggal ditambah ke form kalau/waktu Giel mulai
  trading TSLA beneran dan butuh catat P&L; auto-compute dari sizing
  engine (isi `planned_size` otomatis saat approve signal di Panel 5,
  bukan cuma manual di Panel 6) juga belum dibangun — saat ini alurnya
  masih 2 langkah terpisah (approve di Panel 5, hitung+catat size manual
  di Panel 6).

**Update — RISK_CAPITAL_IDR/USD default placeholder (keputusan Giel: "buat
field aja tapi kamu siapkan nilai default"):** `.env`/`.env.example` diisi
`RISK_CAPITAL_IDR=100000000` (Rp100 juta) & `RISK_CAPITAL_USD=10000`
($10rb) — **NILAI PLACEHOLDER, BUKAN modal riil siapa pun**, ditandai jelas
di komentar supaya Giel ganti begitu tahu angka pastinya. Sizing engine
sekarang jalan out-of-the-box (dicek live: `suggest_position_size` dgn
modal placeholder BBCA menghasilkan angka masuk akal), tanpa perlu Giel
buka .env dulu.

**Update — J-6 selesai (rasio prudential bank CAR/NPL/NIM/LDR, MANUAL):**
- [x] **4 kolom baru di `fundamentals_quarterly`** (`car`, `npl_gross`,
      `nim`, `ldr`) — BUKAN tabel terpisah, tetap "1 row per instrumen per
      kuartal" (konsisten dgn tabel yang sudah ada), migrasi via
      `_COLUMN_MIGRATIONS`.
- [x] **`web/writes.py::save_bank_ratios_manual()`** — UPSERT by
      (instrument, quarter_end) yang **HANYA menyentuh 4 kolom rasio**,
      TIDAK PERNAH menimpa revenue/net_income/dll ATAU kolom `source` baris
      yang sudah ada dari yfinance backfill — dites eksplisit (test +
      verifikasi live: baris BBCA 2026-03-31 dari yfinance, isi manual
      CAR/NPL/NIM/LDR, `source` tetap "yfinance" bukan ketimpa "manual").
      Fungsi ini TERPISAH dari `upsert_fundamentals_quarterly` (J-4) by
      design — scraper otomatis tidak pernah menyentuh 4 kolom ini sama
      sekali.
- [x] **2 route baru** `POST`/`GET /api/fundamentals/bank_ratios`.
- [x] **Panel 8 UI**: form input (ticker+kuartal+4 rasio) + tabel riwayat
      per-ticker.
- 3 test baru (`test_web_writes.py`: insert baru, tidak clobber baris
  yfinance, list cuma kuartal yang punya rasio terisi), 253 test hijau
  total. Diverifikasi live: simpan rasio dummy utk BBCA 2026-03-31 (baris
  sudah ada dari yfinance) -> `source` tetap "yfinance", 4 kolom rasio
  terisi benar di tabel. Data uji (angka dummy, BUKAN rasio BBCA asli)
  dibersihkan (di-NULL-kan lagi) setelah verifikasi — baris asli (revenue
  dll) tidak disentuh.
- **Catatan**: form TIDAK validasi `is_financial=1` di level backend (bisa
  saja diisi utk instrumen non-bank kalau Giel salah ketik ticker) — kalau
  ini jadi masalah nyata, tambahkan guard serupa `save_intake_metadata()`
  di sesi mendatang.

**Update — J-15 Komponen B/D selesai (detail emiten, override, grader log):**
- [x] **Schema**: `emiten_grade.giel_override` (TEXT JSON, kolom yang
      sempat ditandai "gap" di update J-11 — sekarang ditambahkan),
      `grader_log.outcome_3m`/`outcome_6m`/`outcome_notes` (BARU, utk
      widget Nilai Outcome). Migrasi via `_COLUMN_MIGRATIONS`.
- [x] **`web/writes.py::get_emiten_detail()`** — gabungan
      instrument_metadata + 8 kuartal fundamentals terakhir + grade
      terbaru (integrity_flags & giel_override diurai dari JSON).
- [x] **`save_grade_override()`** — guard: `quadrant` harus salah satu
      4 kuadran resmi, `reason` WAJIB non-kosong. **Kuadran mesin ASLI
      (`quadrant`) TIDAK PERNAH ditimpa** — override disimpan terpisah di
      `giel_override`, keduanya tampil bareng di UI (dites eksplisit +
      diverifikasi live: override BBCA jadi INVESTABLE, kolom `quadrant`
      di DB tetap WATCH).
- [x] **`list_grader_log()` + `save_grader_outcome()`** — outcome 3bln/6bln
      independen (COALESCE, isi salah satu tidak menghapus yang lain —
      dites eksplisit).
- [x] **4 route baru**: `GET /api/emiten/<ticker>`, `POST /api/emiten/
      <ticker>/override`, `GET /api/grader_log`, `POST /api/grader_log/
      <id>/outcome`.
- [x] **Panel 8 UI**: section "Detail Emiten" (metadata+grade+override
      form, **playbook bank kontrak §12.1 diterapkan** — `is_financial=1`
      tampilkan CAR/NPL/NIM/LDR, SEMBUNYIKAN revenue/OCF/FCF generik yang
      kurang relevan utk bank) + section "Grader Log & Kalibrasi" (tabel
      dgn dropdown outcome inline per baris).
- 9 test baru (`test_web_writes.py`), 262 test hijau total. **Diverifikasi
  live penuh via browser**: detail BBCA tampil benar dgn kolom bank
  (bukan revenue generik), override ke INVESTABLE tersimpan dgn kuadran
  mesin (WATCH) tetap terlihat berdampingan, widget outcome dropdown
  berfungsi (pilih PARTIAL -> tersimpan, muncul di tabel). Data uji
  (override + outcome dummy) dibersihkan setelah verifikasi.
- **Dengan ini, J-15 (Addendum A §19) SELESAI SELURUHNYA** — Komponen
  A (J-14), C Gelombang 1 (J-14) & 2 (J-12), B & D (giliran ini) semua
  sudah ada.

**Update — J-8 selesai (foreign flow, ternyata PER-SAHAM bukan cuma per-
sektor — lebih detail dari yang diminta kontrak):**
- **Riset**: percobaan pertama (tebak nama urlName API "Digital Statistic"
  spt yang berhasil utk Track C) GAGAL — konsisten dgn dead-end
  "papan pemantauan khusus"/"financial ratio" sebelumnya. **Endpoint yang
  benar ditemukan lewat observasi network request BROWSER SUNGGUHAN**
  (navigate ke laman resmi "Stock Summary" IDX, baca network request yang
  benar-benar terpanggil) — bukan tebak nama lagi. Endpoint:
  `https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=9999&start=0`
  — BEDA family dari "Digital Statistic" (`primary/DigitalStatistic/...`)
  yang dipakai Track C. **Tidak butuh session-cookie warmup** (beda dari
  `idx_foreign_flow.py`) — 1x GET langsung 200. Dikonfirmasi live: 965
  saham, termasuk BBCA (`ForeignBuy`=105.752.900, `ForeignSell`=120.664.900
  lembar, 2026-07-10) — field VOLUME (lembar), BUKAN value Rupiah spt
  Track C.
- [x] **`scrapers/idx_stock_foreign_flow.py`** (BARU) —
      `fetch_idx_stock_foreign_flow(tickers)`, generic (terima list ticker,
      tidak baca DB sendiri — beda dari `equity_universe.py`, konsisten dgn
      pola scraper lain yang lebih umum di project ini). Output 3 metric
      per ticker: `stock_ff_foreign_buy_vol`/`sell_vol`/`net_vol`.
- [x] **Wired ke `pipeline/run_daily.py`** — baca ticker `market='IDX'`
      dari `instrument_metadata` (dinamis, otomatis ikut kalau universe
      nambah saham IDX baru), panggil scraper, gabung ke `upsert_
      positioning` yang sudah ada (natural key dedupe otomatis, TIDAK ada
      jalur tulis baru).
- **TIDAK ada kode UI baru** — `positioning` table SUDAH generik, Panel 3
  otomatis menampilkan baris baru ini begitu ada (pola persis Track C).
- 5 test baru (`test_idx_stock_foreign_flow.py`, live network + guard
  ticker kosong = skip network call), 267 test hijau total. **Diverifikasi
  live penuh**: `pipeline.run_daily` -> `idx_stock_summary = ok`, 3 row
  BBCA masuk `positioning` dgn angka PERSIS sama dgn temuan riset manual
  (net = -14.912.000, net = buy - sell tervalidasi), muncul otomatis di
  `/api/positioning` tanpa ubah endpoint atau Panel 3 sama sekali.
- **Catatan cakupan**: ini PER-INSTRUMEN, bukan agregat per-sektor spt
  yang diminta literal kontrak J-8 — dianggap LEBIH baik (bisa diagregasi
  ke sektor kapan pun kalau perlu, granularitas turun tidak bisa
  sebaliknya). Endpoint tidak punya parameter tanggal (selalu hari bursa
  TERAKHIR) — histori/backfill utk tanggal lampau BELUM dibangun (di luar
  scope turn ini, kalau perlu J-2-style backfill perlu riset ulang apakah
  endpoint ini punya cara narik histori).

**Update — lanjutan kickoff (Giel bilang "oke lanjut", isi BBCA saja dulu):**
- [x] **5 tabel Phase J+ dibangun sebagai DRAFT** (`fundamentals_quarterly`,
      `earnings_calendar`, `sector_benchmark`, `emiten_grade`, `grader_log`)
      — karena dokumen v1.1 asli tidak tersedia, kolom disusun dari gap
      analysis §1 + data requirements §2 + riset yfinance G3, BUKAN
      spesifikasi final Giel. Ditandai jelas di komentar `schema.sql`
      supaya gampang dikoreksi kalau meleset dari v1.1 asli. `asset_context_
      weight` diperluas `+level` (INDEX/SECTOR/INSTRUMENT, pewarisan bobot)
      — row lama di-backfill otomatis jadi `INSTRUMENT` (satu-satunya level
      yang ada sebelum konsep ini, tidak dibiarkan NULL). Total tabel
      14→20. 3 test count di `test_db.py` disesuaikan.
- [x] **`pipeline/seed_universe.py`** (baru, pola sama
      `seed_context_weight.py`) — seed manual `instrument_metadata`,
      idempotent (`INSERT OR REPLACE` by `instrument` PK). **BBCA** entry
      pertama: `lane='INVEST'` (BUKAN `TRADE` — kontrak §13.1 poin 5,
      instrumen baru wajib INVEST/NONE dulu sampai validasi bar-replay
      J-3 selesai, `lane_validated_at` sengaja NULL), `is_financial=1`,
      `lot_size=100`, `has_daily_limit=1` (ARA/ARB), data market_cap/
      free_float dari yfinance `.JK` (dicek live, akan basi seiring waktu —
      field metadata lambat berubah, bukan daily_market yang di-refresh
      tiap run). `avg_volume_20d` sengaja NULL — field ini seharusnya
      dihitung dari histori `asset_ohlcv` riil (J-2, belum jalan utk BBCA),
      bukan pendekatan sekali-catat dari yfinance `info`.
- 3 test baru (`test_seed_universe.py`, termasuk assert eksplisit "instrumen
  baru tidak boleh default ke TRADE"), 181 test hijau total.
- **Backlog dicatat (permintaan Giel eksplisit)**: sistem input manual di
  dashboard buat `instrument_metadata` (form UI, bukan edit `seed_universe.py`
  langsung tiap tambah emiten) — BELUM dibangun, seed script ini pengganti
  sementara sampai UI-nya ada.

**Update — J-14 selesai (Tab 8 Gelombang 1, Addendum A §19.5):**
- [x] **Panel 8 "Universe" (BARU)** — `web/templates/partials/panel8_universe.html`
      + `web/static/js/panel8.js`, nav tab ke-8 di `index.html`.
      **Komponen A** (tabel universe): `GET /api/universe` ->
      `web/writes.py::list_universe()` — `instrument_metadata` + grade
      TERBARU per instrumen dari `emiten_grade` (correlated subquery by
      `MAX(graded_at)`, bukan window function — konsisten gaya SQL project
      ini). Kuadran/score tampil "belum digrade"/`-` sampai modul Grader
      (J-11) jalan — bukan bug, cuma belum ada datanya.
      **Komponen C v1** (intake metadata): `POST /api/intake` ->
      `save_intake_metadata()` — **guard di level fungsi** (bukan cuma UI):
      lane HANYA boleh `INVEST`/`NONE`, `TRADE`/`BOTH` raise `ValueError`
      (endpoint balikin 400) — mirror pola assert `test_seed_universe.py`.
      `INSERT OR REPLACE` by `instrument` PK (idempotent, pola sama
      `seed_universe.py`).
- [x] **Panel 5: badge LANE** di header chart (`#instrumentLaneBadge`) —
      `GET /api/instrument_meta?instrument=X` -> `get_instrument_meta()`.
      Badge **disembunyikan** (bukan kosong-error) kalau instrumen tidak
      punya row `instrument_metadata` — berlaku utk semua aset makro/index
      existing (BTC/GOLD/IHSG/SP500/USDIDR/USDJPY, belum ada di universe
      Phase J+), lane cuma relevan utk saham individual.
- [x] **CSS**: 4 badge modifier baru (`lane-trade` hijau/`lane-both`
      biru/`lane-invest` abu/`lane-none` dashed-border) di
      `static/css/dashboard.css`, `LANE_CLASS` map bareng `LENS_LABELS` di
      `core.js` (dipakai Panel 5 & Panel 8, tidak diduplikasi).
- 6 test baru di `test_web_writes.py` (guard lane reject, insert+upsert
  idempotent, join grade terbaru, no-grade-yet, get_instrument_meta
  found/missing), 187 test hijau total. Diverifikasi live via browser:
  BBCA muncul di tabel Universe dengan data asli, intake form nyimpen
  instrumen baru (`ZZZTEST`, lane INVEST, dibersihkan setelah verifikasi),
  badge Panel 5 kosong utk BTC (no row) dan render `LANE INVEST` yang
  benar saat dipanggil manual utk BBCA (BBCA belum ada di dropdown
  instrument Panel 5 krn J-2 OHLCV backfill belum jalan utk saham individual).
- **Komponen B/D + badge KUADRAN Panel 5 + earnings Panel 3** tetap J-15,
  prasyarat J-4 (fundamentals) & J-11 (grader engine) — TIDAK dikerjakan
  di J-14 (di luar scope Gelombang 1 per kontrak §19.5).

**Update — J-2 selesai (OHLCV universe -> asset_ohlcv, yfinance dinamis):**
- [x] **`scrapers/equity_universe.py`** (BARU) — beda dari `scrapers/macro_yf.py`:
      universe DINAMIS dibaca dari `instrument_metadata` tiap run (bukan dict
      hardcoded), jadi nambah emiten baru lewat Panel 8 intake TIDAK perlu
      ubah kode scraper. `yf_ticker_for(instrument, market)`: IDX -> suffix
      `.JK`, US (dan lainnya) -> ticker apa adanya. Tulis ke `asset_ohlcv`
      SAJA (bukan `daily_market` — saham individual bukan konteks makro
      global, Master Plan §4). Semua instrumen di `instrument_metadata`
      di-fetch (termasuk lane INVEST/NONE, bukan cuma TRADE) — histori
      harga tetap dibutuhkan utk validasi bar-replay J-3 nanti.
- [x] **Wired ke `pipeline/run_daily.py`** — `fetch_equity_universe(date,
      db_path)` dipanggil bareng scraper lain, `asset_rows` digabung ke
      pipeline upsert existing (tidak ada jalur tulis baru, reuse
      `upsert_asset_ohlcv`).
- [x] **`pipeline/backfill.py` extended** — instrumen yang tidak dikenal di
      `YF_TICKERS`/`FRED_INSTRUMENTS` (hardcoded macro) sekarang fallback
      cek `instrument_metadata`: kalau ada, ticker diturunkan dinamis lewat
      `yf_ticker_for()` lalu reuse `_yf_history_range()` yang sudah ada.
      `python -m pipeline.backfill --instrument BBCA --from .. --to ..`
      langsung jalan tanpa perlu entry baru di kode manapun.
- 4 test baru (`test_equity_universe.py`, live network pola sama scraper
  lain — `yf_ticker_for()` unit test + `fetch_equity_universe()` live utk
  BBCA), 191 test hijau total. **Diverifikasi live penuh**:
  `pipeline.run_daily` -> `equity_BBCA = ok` di source_flags, row asli
  masuk `asset_ohlcv` (2026-07-10, close 6175); backfill CLI 2 tahun
  (2024-07-01..2026-07-12) -> 486 baris baru; Panel 5 browser -> BBCA
  MUNCUL di dropdown instrument (otomatis, `/api/assets` generic sejak
  Phase C), chart candlestick render 299 elemen SVG dengan data asli, badge
  LANE INVEST tampil benar di header chart.
- **Catatan cakupan**: Panel 1 "Manual Backfill" dropdown HTML masih
  hardcoded ke instrumen makro (BTC/DXY/SP500/IHSG/Gold/USD-IDR) — backfill
  utk instrumen Phase J+ (BBCA dst) jalan via CLI `pipeline.backfill`, BUKAN
  lewat UI Panel 1. Menambah instrumen Phase J+ ke dropdown itu bukan
  bagian J-2 (di luar scope kontrak), dicatat sebagai potensi UX follow-up.
- **`volume_ma20`** tetap NULL utk row BBCA hasil backfill (`backfill.py`
  tidak menghitung ulang kolom itu, beda dari `run_daily` yang eksplisit
  panggil `volume_ma20_for_instrument` tiap run) — TIDAK memblokir apa pun
  sekarang (Panel 5 chart hitung MA sendiri client-side dari OHLCV mentah;
  `analysis/*` belum menyertakan BBCA di `INSTRUMENTS` list, itu bagian J-3).

**Dievaluasi, sengaja tidak dikerjakan:**
- **J-6: Bank ratio CAR/NPL/NIM/LDR via IDX** — Giel tanya "how about IDX"
  sbg alternatif OJK. Riset dilakukan (bukan asumsi): (1) WebSearch
  konfirmasi IDX punya laman "Financial Report and Ratio of Listed
  Companies" di sistem Digital Statistic yang sama dgn foreign-flow API
  yang sudah dipakai (Track C); (2) riset source code proyek open-source
  NeaByteLab/IDX-API menemukan modul `syncFinancialRatio()` — TAPI field
  yang disebut cuma **PER/PBV/ROE/DER** (rasio valuasi pasar umum), BUKAN
  rasio prudential bank (CAR/NPL/NIM/LDR); (3) percobaan langsung nembak
  beberapa nama `urlName` API (`LINK_TABLE_FINANCIAL_RATIO` dkk, pola sama
  endpoint foreign-flow) — semua balik 503 (bukan 404, endpoint yang benar
  memang belum ketemu); (4) percobaan lewat browser sungguhan (isi filter
  bulan/tahun + klik "Terapkan" di laman resminya) juga tidak berhasil
  memicu network request API-nya (kemungkinan resolusi server-side Nuxt,
  bukan client-side fetch yang bisa diintip). **Kesimpulan**: rasio
  prudential bank spesifik KEMUNGKINAN BESAR memang bukan data yang
  dipublikasi di level "ratio umum" milik bursa (IDX) — biasanya itu
  disclosure regulasi milik OJK (`ojk.go.id`, Laporan Surveillance
  Perbankan Indonesia, ditemukan di riset yang sama). **Tetap Backlog** —
  OJK jadi kandidat sumber paling mungkin, belum diriset lebih lanjut
  (di luar scope turn ini). Dicatat di sini supaya riset "urlName IDX
  utk financial ratio" tidak diulang dari nol lagi tanpa alasan baru.
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

**Update — J-3: ARA/ARB sizing buffer (§18 keputusan #4, LOCKED) + fraksi harga
zone tolerance (§13.1 poin 4, DRAFT) selesai (13 Jul 2026):**
- **ARA/ARB buffer 1.5×** (`analysis/sizing.py`) — `suggest_position_size()`
  terima parameter baru `has_daily_limit: bool`. Kalau `True` (dibaca otomatis
  dari `instrument_metadata.has_daily_limit`, bukan input manual user), jarak
  SL dikalikan `ARA_ARB_BUFFER_MULT = 1.5` sebelum dipakai hitung ukuran posisi
  — mengecilkan `suggested_units` supaya risiko riil tidak melebihi budget
  kalau harga gap lewat SL saat kena ARA/ARB (auto-rejection order IDX, beda
  dari LULD circuit-breaker US yang masih bisa closed-out). Ini keputusan
  **terkunci §18**, bukan draft — tidak perlu revisi Giel lagi. Respons API
  `/api/sizing/suggest` sekarang sertakan `nominal_risk_per_unit` (jarak SL
  asli, tanpa buffer) berdampingan dengan `risk_per_unit` (sudah dibuffer) —
  Panel 6 (`panel6.js`) tampilkan keduanya eksplisit kalau buffer dipakai
  ("buffer ARA/ARB 1.5x diterapkan: jarak nominal X → Y") supaya Giel bisa
  lihat transparansi hitungannya, bukan cuma angka akhir. 3 test baru
  (`test_sizing.py`), diverifikasi live: BBCA (`has_daily_limit=1`) tampilkan
  nominal 100 → buffered 150 dengan benar di Panel 6 browser.
- **Fraksi harga (tick size) zone tolerance** (`analysis/calibration.py`,
  file baru) — tabel resmi Peraturan No. II-A BEI (dikonfirmasi WebSearch,
  bukan tebakan): harga <Rp200 → fraksi Rp1; Rp200-500 → Rp2; Rp500-2rb →
  Rp5; Rp2rb-5rb → Rp10; ≥Rp5rb → Rp25. `idx_zone_tolerance_pct()` hitung
  toleransi clustering S&R sbg persentase relatif (`fraksi × 2 ticks ÷ harga
  acuan`) — **DRAFT**, `IDX_ZONE_TOLERANCE_TICKS = 2` masih perlu dikonfirmasi/
  direvisi Giel setelah bar-replay validation per §13.1 poin 5 ("engine teruji
  di BTC ≠ teruji di BBRI"), BEDA dari buffer ARA/ARB di atas yang sudah final.
  `pipeline/run_analysis.py::run_analysis()` cek `instrument_metadata.market`
  — kalau `'IDX'`, toleransi dihitung dari close TERBARU via fungsi ini;
  instrumen lain (semua makro/index existing: BTC/GOLD/IHSG/SP500/USDIDR/
  USDJPY, tidak punya row `instrument_metadata`) tetap pakai `CLUSTER_TOLERANCE`
  default 0.5% persis seperti sebelumnya — **dijamin nol regresi** (diverifikasi
  baik lewat code inspection maupun re-run test suite existing sebelum nambah
  test baru). `upsert_sr_zone()` terima `tolerance` yang SAMA dgn dipakai
  `detect_zones()` supaya `zone_bucket_key()` konsisten antar re-run (tidak
  drift). Summary dict + `_print_summary()` tampilkan persentase toleransi
  aktual dgn catatan "(kalibrasi IDX, DRAFT)" vs "(default)". 4 test baru
  (`test_calibration.py`) + 2 test baru (`test_run_analysis.py`, regression
  guard non-IDX + assert toleransi IDX terpakai benar), 276 test total hijau.
  **Diverifikasi live**: `python -m pipeline.run_analysis --instrument BBCA`
  -> toleransi 0.816% (25×2÷6175, sesuai harga BBCA riil ~Rp6175), 0 zona baru
  (bucket existing tetap match, tidak drift); `--instrument TSLA` -> tetap
  0.500% default (bukan IDX, tidak terpengaruh sama sekali).

**Update — Mekanisme validasi lane / bar-replay sign-off selesai (13 Jul
2026, kontrak §13.1 poin 5):** Giel review "Tidak usah, saya review langsung
dari Panel 5" utk materi persiapan bar-replay (tidak butuh dibangunkan alat
bantu khusus) — TAPI dia tetap butuh **jalur untuk merekam hasil** review itu
begitu selesai, karena `instrument_metadata.lane`/`lane_validated_at`
sebelumnya tidak ada UI/API sama sekali buat menulisnya (cuma terisi manual
lewat `sqlite3` langsung, tidak scalable & tidak ada jejak audit). Dibangun:
- **Tabel baru `lane_validation_log`** (`db/schema.sql`, append-only, pola
  sama `intake_log`/`grader_log`) — `evidence TEXT NOT NULL`, jejak
  instrument/old_lane/new_lane/validated_at per keputusan. `db/connection.py`
  `EXPECTED_TABLES` + `tests/test_db.py` diupdate (21 → 22 tabel).
- **`web/writes.py::validate_lane()`** — SATU-SATUNYA jalur yang boleh
  mengubah `instrument_metadata.lane` / mengisi `lane_validated_at`. Guard di
  level fungsi (bukan cuma UI, pola sama `save_intake_metadata`/
  `save_grade_override`): `evidence` wajib non-kosong, `new_lane` harus salah
  satu TRADE/INVEST/BOTH/NONE, return `None` kalau instrumen belum ada di
  `instrument_metadata` (harus intake dulu). TIDAK PERNAH dipanggil otomatis
  oleh `run_analysis`/`seed_universe`/backfill manapun — murni tindakan
  manual lewat form. `list_lane_validation_log()` utk riwayat, filter
  opsional per instrumen.
- **Routes baru** `POST /api/emiten/<ticker>/validate_lane` +
  `GET /api/lane_validation_log` (`web/app.py`).
- **Panel 8 UI baru** (`panel8_universe.html`/`panel8.js`): section "Validasi
  Lane (Bar-Replay Sign-off)" (ticker + dropdown lane baru + textarea
  evidence wajib) + tabel "Riwayat Validasi Lane" (kolom lane lama→baru +
  evidence), wired ke `refreshAll()` di `main.js`.
- 7 test baru (`test_web_writes.py`: reject lane tidak dikenal, reject
  evidence kosong, return None kalau belum intake, update metadata + log
  evidence dgn benar, filter log per instrumen), 281 test total hijau.
  **Diverifikasi live** via browser (fetch langsung, bukan klik form, supaya
  tidak menyentuh judgment BBCA/TSLA yang sebenarnya): intake ticker
  disposable `ZZTEST` → validasi TRADE dgn evidence → cek log tercatat benar
  → **dibersihkan lagi dari DB produksi** (0 row tersisa, dikonfirmasi
  query). BBCA & TSLA TETAP `lane=INVEST`, `lane_validated_at=NULL` seperti
  semula — mekanisme sudah siap, tapi keputusan bar-replay yang sebenarnya
  tetap milik Giel sepenuhnya, tidak difabrikasi di sini.

**Update — J-9 data plumbing + draft prompt equity slice (13 Jul 2026):**
Giel minta "lanjutkan" 3 hal sekaligus (bar-replay validation, kalibrasi
§13, prompt J-9) — utk J-9, split lagi jadi "mekanisme" (bisa dibangun) vs
"suara/kata-kata prompt" (harus Giel sendiri, sama seperti keputusan
sebelumnya di Track D bahwa prompt persona adalah cara berpikir Giel).
- **Data plumbing** (`pipeline/compose_persona_context.py`) —
  `_equity_fundamentals_lines()` (fundamentals_quarterly + emiten_grade +
  foreign-flow-per-saham J-8, per instrumen di `instrument_metadata`) dan
  `_earnings_calendar_lines()` (earnings_calendar J-7, peruntukannya utk
  AKELA sudah ditulis eksplisit di komentar schema sejak J-7 dibangun) —
  ditambahkan ke `_slice_rivan()` dan `_slice_akela()`. Instrumen bank
  (`is_financial=1`) tampil NII/CAR/NPL/NIM/LDR, non-bank tampil
  Revenue/NetIncome/FCF + flag `confidence` (FULL/LOW_CONFIDENCE). Grade
  tampil kuadran+score+override Giel (kalau ada, ASLI tetap terlihat
  bareng). GEMA/LEON TIDAK disentuh (disiplin slice, konsisten dgn pola
  IHSG foreign flow yg sudah ada). 9 test baru
  (`test_compose_persona_context.py`), 287 test total hijau. **Diverifikasi
  live** thd DB produksi: RIVAN slice tampil BBCA (bank, CAR/NPL/NIM/LDR
  masih `n/a` krn belum diisi manual Giel, NII terisi dari yfinance,
  grade WATCH score=100, foreign flow -14.912.000 lembar) + TSLA (Revenue/
  NetIncome/FCF terisi, confidence=LOW_CONFIDENCE, grade WATCH score=100);
  AKELA slice tampil earnings BBCA & TSLA 2026-07-22 dgn forecast EPS.
- **Prompt teks itu sendiri BELUM diubah** — didraft terpisah di
  `docs/j9_equity_slice_prompt_draft.md` (proposal, BUKAN ditulis ke
  `prompts/persona_rivan.txt`/`persona_akela.txt` yang gitignored/personal
  IP Giel). Draft mengusulkan RIVAN dapat penjelasan data equity + panduan
  "grade bukan vonis final", AKELA dapat penjelasan earnings-date sbg event
  risk terjadwal. GEMA/LEON sengaja tidak diusulkan berubah sama sekali.
  Giel yang putuskan apakah dipakai, diedit, atau dibuang.

**Update — Panel 1 "Cek & Backfill Semua Gap" (14 Jul 2026):** Giel menunjuk
sistem deteksi gap yang sudah ada (`/api/data_gaps`, per-instrument dropdown)
sudah informatif — pertanyaannya kenapa masih harus pilih instrument satu-satu
kalau sistem sudah tahu semua yang bolong. Dibangun:
- **`web/app.py::_all_instruments_with_gaps(conn)`** — fungsi pure (DB-only,
  tanpa network) yang deteksi gap utk SEMUA instrument sekaligus: macro
  (`INSTRUMENT_SOURCE`, 13 instrumen) + universe ekuitas Phase J+
  (`instrument_metadata`, kalender WEEKDAY). Instrumen tanpa histori sama
  sekali (`total_rows=0`) DILEWATI sengaja — itu backfill awal yang butuh
  keputusan sadar (instrument mana, dari tanggal berapa), bukan "isi gap"
  otomatis. Kalender `WEEKLY_WED` juga dilewati (pola sama `/api/data_gaps`).
- **`POST /api/backfill/all/preview`** — pakai fungsi di atas utk cari
  kandidat, lalu panggil `backfill_mod.backfill(..., preview_only=True)`
  (network fetch asli) per instrument utk range gap-nya masing-masing.
  Instrument yang gagal fetch dicatat error-nya, TIDAK menghentikan
  instrument lain (pola sama `safe_call` scraper).
- **`POST /api/backfill/all/commit`** — commit HANYA item yang sudah
  di-preview (body `{"items": [...]}`, bukan deteksi ulang) — menghindari
  drift kalau gap berubah di antara 2 request, request/response symmetric
  dgn alur single-instrument existing.
- **Panel 1 UI** (`panel1_snapshot.html`/`panel1.js`) — tombol baru "Cek &
  Preview Semua Gap" di bawah form Manual Backfill existing, render tabel
  instrument/range-gap/baru/duplikat + tombol "Commit Semua (N instrument)".
  Setelah commit, `loadDataGaps()` dipanggil ulang supaya info gap dropdown
  yang sedang dipilih ikut ter-refresh.
- 5 test baru (`test_web_app.py`, DB-seeded, tanpa network — mirror pola
  `_detect_gaps` existing): gap macro, skip instrument tanpa histori, skip
  kalender WEEKLY_WED, include universe ekuitas (WEEKDAY), no-gap→hasil
  kosong. 292 test total hijau. **Diverifikasi live thd DB produksi**: preview
  menemukan gap asli BTC (2026-07-11 s.d. 2026-07-12, 2 baris), commit
  menulis 2 baris baru (4.316→4.318), info gap dropdown BTC otomatis
  ter-refresh jadi "tidak ada gap terdeteksi" — data yang ditulis REAL
  (bukan dummy, tidak perlu dibersihkan).

**Update — Migrasi FE ke Vue 3 + Vite, Fase 0-2 selesai (14 Jul 2026):** Giel
minta "jalankan semua fase build FE" mengikuti rencana `docs/migrationFE.md`
(app paralel + strangler cutover, keputusan sebelumnya: Vue 3 + Vite +
PrimeVue, chart dibungkus apa adanya, backend tidak disentuh). Node/npm
ternyata sudah diinstall Giel sendiri via nvm sebelum sesi ini (`v24.16.0`);
scaffold Vite+Vue juga sudah pernah dijalankan Giel tapi ke-nested salah
lokasi (`web/frontend/web/frontend/`, kemungkinan dijalankan dari dalam
`web/frontend/`) — dipindah ke lokasi benar (`web/frontend/`), node_modules
yang sudah ter-install dipertahankan.
- **Fase 0** (scaffold): Vue Router (8 route 1:1 dgn tab lama) + Pinia +
  PrimeVue (preset Aura) + proxy dev `/api` → Flask. Diverifikasi live:
  data asli `/api/latest` termuat lewat proxy, routing SPA jalan.
- **Fase 1** (fondasi bersama): `src/lib/api.js`, `src/lib/format.js`,
  `src/components/DataTable.vue` (wrap PrimeVue DataTable, dipakai ~11
  tabel), `src/composables/useAppToast.js`.
- **Fase 2** (migrasi 8 panel): SEMUA 8 view selesai & diverifikasi live thd
  DB produksi (bukan data dummy) — Snapshot (cards+backfill+backfill-semua-
  gap), News, Forward (paling banyak form: econ calendar inline-edit,
  expectations, positioning, policy tracker, disonansi), Reading (persona
  cards + PrimeVue Dialog), Chart (SVG candlestick DIBUNGKUS APA ADANYA,
  `rollingMA`/`drawCandleChart`/`drawMiniLine` dipindah ke
  `src/lib/chartMath.js` nyaris verbatim, dimigrasi TERAKHIR sesuai
  rencana), Synthesis, Riwayat (4 sub-tab), Universe (paling besar, 8
  sub-bagian termasuk validasi lane & grader log). **Bug ditemukan &
  diperbaiki SEBELUM produksi**: `ForwardView` awal pakai 1 `ref` bersama
  utk semua input econ calendar "Actual" yang kosong — salah kalau >1 baris
  butuh diisi bersamaan (kasus nyata, econ calendar biasa banyak event
  future tanpa actual) — diperbaiki jadi state per-baris.
- Verifikasi live mencakup: switch instrument BTC↔BBCA di Chart (harga +
  lane badge ikut berubah benar), Detail Emiten BBCA di Universe (tabel
  fundamentals bank-spesifik + LOW_CONFIDENCE flag tampil benar), search/
  sort/paginate DataTable, Economic Calendar dgn actual sudah terisi vs
  kosong. `npm run build` sukses (~200KB gzip total, code-split per view).
- **Fase 3 (cutover + login) SELESAI (14 Jul 2026)**. Dijeda dulu utk
  konfirmasi eksplisit Giel sebelum menghapus kode lama (lihat update di
  bawah) — setelah dikonfirmasi, dieksekusi penuh:
  - **Auth**: `@app.before_request` di `web/app.py` menolak (401) semua
    `/api/*` kecuali `/api/auth/{login,status}` sampai `session["authed"]`.
    `DASHBOARD_PASSWORD` wajib diisi manual di `.env` — TIDAK PERNAH
    di-generate/default oleh kode (beda dari `RISK_CAPITAL_*` yang memang
    placeholder angka; ini kredensial, aku tidak pernah mengetik/menguji
    nilai aslinya sendiri). Kosong -> login endpoint menolak dgn pesan
    jelas. `FLASK_SECRET_KEY` opsional. Password dibanding pakai
    `secrets.compare_digest` (constant-time).
  - **Serving**: route SPA catch-all (didaftarkan paling akhir) menyajikan
    `web/frontend/dist/` — Flask `/` sekarang SATU proses/port utk API +
    frontend, tidak perlu Vite dev server terpisah utk pemakaian sehari-hari.
  - **Vue**: `src/stores/auth.js` (Pinia) + `src/views/LoginView.vue` +
    router guard (`src/router/index.js`) + redirect otomatis ke `/login`
    kalau sesi expired (`src/lib/api.js`).
  - Kode vanilla lama (`web/templates/`, `web/static/` — 8 partial HTML +
    10 file JS + 1 CSS) **dihapus**, Giel sendiri yang commit (`f7168f2
    "Migrate to Vue JS"`), bukan auto-commit dariku — tetap recoverable
    via `git show bcfa625:web/templates/index.html` dkk kalau perlu.
  - **Diverifikasi**: redirect ke `/login` saat belum auth, 401 di `/api/*`
    tanpa cookie, semua asset ke-serve benar (network tab: 200/304, nol
    404), dan SETELAH Giel isi password & login sendiri — sidebar+tombol
    Keluar+data real tampil benar dari sesi ter-autentikasi. Backend/API +
    292 test Python tetap tidak berubah sama sekali di seluruh proses ini.

**Update — Snapshot: 2 trigger (Berita + Backfill) + rapikan Manual Backfill
(28 Jul 2026):** Giel minta "2 trigger" yang jalan sekarang: Berita (tidak
bisa di-backfill tanggal lampau, RSS cuma sajikan yang live) dan Backfill
(data market, isi gap tanggal lampau) — dipisah krn tujuan beda, bukan
duplikat.
- **`POST /api/run_daily_now`** (baru) — panggil `pipeline.run_daily.
  run_daily()` langsung dari tombol "Trigger Berita (Sekarang)" di
  `SnapshotView.vue`. Sebelumnya Giel harus minta run manual lewat terminal
  tiap kali cron WSL tidak jalan (kejadian berulang, lihat entri di atas) —
  sekarang bisa dipicu sendiri dari UI.
- **Checkbox di "Cek & Preview Semua Gap"** — tabel hasil sekarang punya
  kolom centang per instrument (default semua tercentang), tombol jadi
  "Commit Terpilih (N instrument)" — bisa uncheck instrument yang tidak mau
  di-commit, tidak lagi all-or-nothing.
- **Form Manual Backfill per-instrument DIHAPUS** (dropdown Instrument +
  Dari/Sampai tanggal + Preview/Commit) — Giel bilang redundan dengan "Cek &
  Preview Semua Gap" yang sudah cek semua instrument sekaligus. Endpoint
  backend yang jadi tidak terpakai ikut dihapus: `GET /api/data_gaps`,
  `POST /api/backfill/preview`, `POST /api/backfill/commit` (fungsi
  `_detect_gaps`/`INSTRUMENT_SOURCE` TETAP ada, masih dipakai
  `_all_instruments_with_gaps` utk jalur "semua gap").
- Diverifikasi: 404 test Python hijau, `npm run build` bersih, endpoint baru
  diverifikasi via Flask test-client (temp DB, `run_daily` di-monkeypatch
  supaya tidak fetch network beneran).

**Update — News Threads: batas 7 ACTIVE dicabut (28 Jul 2026):** Giel coba
aktifkan/bikin thread, kena blok batas 7 (keputusan #5, §20.1 kontrak) —
minta eksplisit batasan dihapus, dia sendiri yang tentukan berapa banyak
thread & mana yang ACTIVE/DORMANT lewat status field yang sudah ada.
- `MAX_ACTIVE_THREADS` + guard COUNT-check di `save_thread()` (`web/writes.py`)
  dihapus total. `patch_thread()` (reaktivasi DORMANT→ACTIVE) tidak pernah
  punya guard serupa, jadi tidak ada perubahan di situ.
- Frontend: teks "Maksimal 7 thread ACTIVE" + "{{activeCount}}/7 thread
  ACTIVE" di `ThreadsView.vue` diubah jadi cuma nampilkan jumlah, tidak
  nyebut batas lagi. `active_count`/`list_threads_with_stats` tetap ada
  (masih berguna sebagai info, cuma bukan lagi angka thd batas keras).
- Test lama `test_save_thread_enforces_max_active` diganti
  `test_save_thread_no_longer_caps_active_count` (bikin 8 thread ACTIVE
  sekaligus, harus sukses semua).
- `docs/phase_j_build_contract_v1_3_LOCKED.md` §20.1: teks keputusan #5
  di-strikethrough + dianotasi (bukan dihapus, historinya tetap kelihatan).
- Diverifikasi: pytest full suite hijau, `npm run build` bersih.

Sesuai `plan.txt`: **jangan lompat phase tanpa instruksi baru.** Kalau ada
kebutuhan mendesak di luar urutan (seperti Phase 1 kemarin), itu boleh — tapi
harus tercatat di sini dengan jelas kenapa keluar urutan, supaya roadmap tetap
mencerminkan kenyataan, bukan rencana ideal yang sudah basi.