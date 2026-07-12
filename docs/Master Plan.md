# KASTARA FINANCE — MASTER PLAN
**Version:** 1.6
**Date:** 12 Juli 2026 (revisi dari v1.5, 11 Juli 2026)
**Author:** Giel × Claude
**Status:** Locked — v1.6 adalah revisi korektif, bukan penambahan fitur:
(1) label 4 lensa Panel 4 dikoreksi — label lama menukar domain AKELA/RIVAN
dan memberi label "Sentimen & Psikologi" yang bukan milik lensa mana pun
(Section 6), (2) context weight IHSG disinkronkan dengan keputusan
IHSG-foreign-flow (Section 3, 4.3), (3) ketegangan SBN flow antara prompt
persona v4 dan masterplan DISELESAIKAN — SBN eksklusif Forward Panel, tidak
pernah masuk slice persona (Section 4.2), (4) build order Phase J+ tidak
lagi menyalin nomor langkah — Build Contract v1.3 ditetapkan sebagai single
source of truth spesifikasi (Section 12), status "5 tabel draft" ditutup.
Detail eksekusi harian tetap di [ROADMAP.md](ROADMAP.md).

---

## 0. CARA MEMBACA SISTEM INI (Mental Model)

Dokumen ini besar. Sebelum tenggelam di detail, pegang dulu peta ini. Kalau bingung kapan pun, balik ke sini.

### Tiga sisi, satu sistem
Tabel, Panel, dan Sprint **bukan tiga hal berbeda** — itu satu sistem dilihat dari tiga sisi:
```
TABEL   = bagaimana data DISIMPAN    (gudang)
PANEL   = bagaimana data DITAMPILKAN (etalase)
SPRINT  = urutan kamu MEMBANGUN      (jadwal tukang)
```
Contoh: tabel `daily_market` dan Panel 1 "Data Snapshot" itu benda yang sama, dilihat dari sisi simpan vs sisi layar.

### Spine — seluruh sistem cuma satu garis lurus
```
①  KUMPUL  →  ②  SIMPAN  →  ③  OLAH  →  ④  SAJI  →  ⑤  BACA & PREDIKSI  →  ⑥  AKSI & SKOR
  (data masuk)  (bank data)   (tools)   (dashboard)   (kursi Giel)         (trade + nilai)
```
Semua komponen jatuh ke salah satu kotak:
```
① KUMPUL    scraper (CoinGecko, Binance, FRED, yfinance, alt.me, RSS)
            + manual fetch tool + input artikel manual
② SIMPAN    semua tabel di Section 4
③ OLAH      indicator engine, S&R detector, signal engine (Section 7)
④ SAJI      6 panel dashboard (Section 6)
⑤ BACA      Forward Panel + Reading Workspace + prediction_log
            ← KURSI GIEL. Mesin tidak duduk di sini.
⑥ AKSI      approve signal → trading_journal, nilai prediksi → skor,
            opsional jadi konten
```

### Prinsip inti yang tidak boleh lupa
- **Mesin merakit, Giel memprediksi.** "Mesin prediksi" hidup di kotak ⑤–⑥ saja. Kotak ①–④ adalah pipa: dibangun sekali, jalan sendiri tiap pagi.
- **Forward layer mengatur LANE, bukan trigger ENTRY.** Bacaan arah kebijakan menggeser bias; entry tetap butuh breakout + retest + volume.
- **Setiap output otomatis butuh approval Giel** sebelum jadi keputusan (flag `giel_approved` / `validated_by_giel` di level data).
- **Prediksi dicatat dan dinilai** (`prediction_log`) — ini yang membedakan analis dari pundit.
### Rasa pakainya — pagi Giel, ~20 menit
```
07.00  Panel 1 cek data masuk · Panel 2 baca & flag news
07.05  Panel 3 Forward → set LANE hari ini (FedWatch, COT, rhetoric)
07.10  Panel 4 Reading → tulis 4 lensa + konflik
07.15  Panel 5 Chart → setup valid? approve/skip
07.18  Panel 6 → synthesis + catat 1 prediksi ke prediction_log
07.20  Selesai. Opsional jadikan konten.
```

---

## 1. VISION & POSITIONING

### Konsep Inti
Kastara Finance adalah **engineer yang menjadi finance analyst** — bukan influencer yang pakai AI sebagai gimmick, dan bukan AI yang fully-automated tanpa manusia. Tools yang dibangun **bukan untuk dijual**, tapi untuk membantu Giel sendiri membaca market lebih tajam. Goal utamanya bukan jualan tools — goal-nya adalah **personal brand finance influencer** yang kredibel karena proses analisanya transparan dan didukung tools buatan sendiri.

### Proposisi Nilai
```
TOOLS BANTU LIHAT (chart, S&R, indikator, suggest buy limit)
         +
GIEL BACA SEMUA (news, data, bahkan output AI lain seperti
                  TradingAgents, qrak/LLM_trader, dll)
         =
PEMAHAMAN & SYNTHESIS GIEL (bukan output AI murni)
```

Tools menjawab "apa yang chart tunjukkan." Giel menjawab "apa artinya, dan apa yang harus dipercaya." 4 Persona (GEMA, LEON, AKELA, RIVAN) adalah **framework berpikir Giel sendiri** saat membaca berita.

> **Deviasi eksplisit (v1.5, atas permintaan Giel):** awalnya dirancang diisi
> manual oleh Giel sendiri. Sejak Panel 4 dibangun ulang, ke-4 lensa jadi
> **AI-generated** lewat OpenRouter (`llm/persona_analysis.py`) — dipicu manual
> per kartu (tombol "Jalankan Analisa"), hasil read-only di popup, TIDAK bisa
> diedit. System prompt tiap persona ditulis manual Giel sendiri (`prompts/
> persona_<lens>.txt`, IP pribadi, gitignored) — jadi keluarannya tetap
> "framework berpikir Giel", cuma dieksekusi AI, bukan diketik Giel kata per
> kata. Giel tetap yang approve/pakai/buang hasilnya; tidak ada output yang
> otomatis jadi keputusan. Sejak v4 prompt (Juli 2026), ke-4 persona juga
> menerima **konteks data yang BERBEDA per lensa** (Shared Core + Slice —
> lihat Section 4.2, 6), bukan satu blob identik — supaya ke-4 sudut pandang
> benar-benar independen dan bisa berkonflik secara produktif, bukan 4 gaya
> bicara yang membaca data sama.

Kalau dipakai di konten, itu mensimulasikan cara Giel memecah analisa, bukan keluaran bot murni tanpa kurasi.

### Diferensiasi dari Finance Influencer Biasa
| Influencer Biasa | Kastara Finance |
|---|---|
| Opini + gut feel | Rules-based system (breakout + retest, locked) |
| Sembunyikan proses | Show the work — tools dan bank data terbuka |
| Bergantung pada satu sumber/feel | Adu banding banyak sumber (RSS, AI agent lain, data sendiri) sebelum simpulkan |
| Satu sudut pandang | 4 lensa (GEMA/LEON/AKELA/RIVAN) — konflik dicatat, bukan disembunyikan |
| Konten reaktif/viral | Konten terstruktur + repeatable, berbasis bank data harian |

### Konteks Riset Pasar (GitHub Landscape)
Ada banyak proyek open-source yang serupa secara teknikal (TradingAgents — multi-agent debate; qrak/LLM_trader — multi-persona dengan claim validation dan R:R 1.5 enforced; Freqtrade/FreqAI; Sibyl). Semua proyek ini **fully automated tanpa human gate**, gratis, dan tidak punya konteks Indonesia (BI, IDR, IHSG). Moat Kastara Finance bukan di kecanggihan tools — tapi di kombinasi: human judgment sebagai filter akhir, konteks lokal Indonesia, sistem yang transparan/locked (bukan black box), dan personal brand yang audiens percaya karena prosesnya kelihatan.

### Vertical dalam Kastara Ecosystem
- Kastara Tools (security) — sudah live
- Kastara HR — sudah live
- **Kastara Finance** — in development
---

## 2. PHASE ROADMAP

```
PHASE 1 — FOUNDATION          (sekarang)
Bank data + tools analisa pribadi
Belum ada konten publik wajib

PHASE 2 — CONTENT             (setelah tools dipakai harian & stabil)
Konten analisa berdasarkan proses nyata Giel
4 persona sebagai format publik (manual, bukan auto-generate)
Platform: X + Telegram

PHASE 3 — COMMUNITY            (setelah ada audience)
Telegram paid community
Tools TETAP tidak dijual sebagai produk utama —
  akses dashboard/jurnal hanya sebagai bonus member, bukan core offer

PHASE 4 — EDUKASI / B2B        (validated demand, opsional)
Cara Giel build tools ini sendiri
Konsultasi jika ada permintaan
```

**Catatan penting:** roadmap monetisasi tools sengaja dilonggarkan dibanding draft sebelumnya — goal utama Phase 1–2 adalah personal brand & kemampuan analisa Giel sendiri, bukan jualan produk.

---

## 3. TRADING SYSTEM — RULES YANG DI-CODE

### Instrumen — Satu Gerbang, Banyak Aset
Kastara Finance dirancang sebagai **satu gerbang analisa prediktif untuk banyak aset**: BTC, IHSG, S&P 500, Gold, Forex (mis. USD/IDR, USD/JPY). Pipeline-nya identik (spine ①–⑥) — yang berbeda hanya data yang di-feed dan cara penyajian per aset. Engine S&R + breakout/retest bersifat universal (price-action berlaku sama di semua chart), jadi tidak ditulis ulang per aset.

- **Trade Engine (eksekusi sinyal):** mulai BTC/USDT, lalu duplikasi ke aset lain bertahap (daily timeframe)
- **Context Engine:**
  - *Tier 1 (mandatory):* DXY, S&P 500, US10Y, BTC Dominance, Fear & Greed, **VIX, USD/JPY, Net Liquidity (WALCL−RRP−TGA), Economic Calendar**
  - *Tier 2:* IHSG, USD/IDR, Gold
  - *Optional (tercatat, aktif saat scaling):* stablecoin supply, BI–Fed spread
  - ~~BTC L/S ratio + liquidation (Coinglass)~~ — **implemented (Juli 2026)**
    lewat **Coinalyze** (gratis, bukan Coinglass berbayar): OI agregat lintas
    exchange, L/S ratio, dan liquidation **dipisah long vs short** (bukan 1
    angka gabungan — RIVAN perlu baca komposisi untuk bedakan short-covering
    dari pembelian spot murni). Lihat Section 4 kolom `btc_oi_aggregate`/
    `btc_liq_long_24h`/`btc_liq_short_24h`.
  - ~~HY credit spread~~ — **implemented**, FRED `BAMLH0A0HYM2` (dicek: dibatasi
    rolling 3-tahun oleh lisensi sumber ICE Data, bukan gap scraper kita).
**Penting — context weight per aset tidak sama.** Pipeline universal, tapi driver dominan tiap aset berbeda. Engine harus tahu aset apa yang sedang dibaca agar context-nya dibobot benar:
```
BTC      → net liquidity, ETF flow, F&G, BTC dominance
GOLD     → real yield (US10Y−inflasi), DXY, geopolitik
S&P 500  → earnings, Fed path, net liquidity
IHSG     → IHSG foreign flow (ihsg_ff), IDR, BI rate, komoditas
           (SBN foreign flow = pelengkap manual mingguan, Forward Panel only
            — lihat 4.2 Stage 2)
FOREX    → rate differential / carry, trade balance
```
Tanpa pembobotan ini, IHSG akan salah dibaca (lebih sensitif ke foreign flow & IDR daripada ETF BTC). Lihat Section 4.3 untuk implementasi schema-nya.

**Disiplin build (non-negotiable):** multi-aset adalah *desain arsitektur sekarang, eksekusi bertahap nanti*. BTC dulu sampai mesinnya benar-benar jalan & teruji, baru duplikasi. Jangan bangun lima aset sekaligus — lebih baik satu sistem kuat daripada lima setengah jadi.

### Entry Rules (semua harus terpenuhi)
```
1. S&R VALID
   └── Zona disentuh minimum 2–3 kali historis
   └── Gunakan area/zona, bukan garis tunggal

2. BREAKOUT VALID
   └── Daily candle CLOSE di atas resistance (bukan wick)
   └── Volume breakout > moving average volume

3. RETEST VALID
   └── Harga kembali ke zona support baru (bekas resistance)
   └── Daily candle CLOSE di atas zona = konfirmasi
   └── Volume retest: hadir (tidak sepi)

4. ENTRY
   └── Buy limit = harga close candle retest konfirmasi

5. STOP LOSS
   └── Di bawah swing low / lower bound zona support
   └── Trigger: daily candle CLOSE di bawah zona (bukan wick)

6. TAKE PROFIT
   └── TP1 = resistance terdekat berikutnya (dari chart historis)
   └── Minimum R:R = 1:1.5
   └── Ideal R:R = 1:2.5 ke atas
   └── Jika R:R < 1:1.5 → SKIP

7. INVALIDASI
   └── Daily candle close di bawah SL = cut loss, keluar
```

### Output Tools untuk Rule Ini
Tools **men-suggest**, tidak men-generate keputusan: deteksi zona S&R (semi-otomatis + validasi manual Giel), deteksi breakout/retest valid, hitung R:R otomatis, suggest entry/SL/TP1. Giel yang approve, reject, atau modify sebelum dianggap sinyal final di trading_journal.

---

## 4. DATA ARCHITECTURE

### Filosofi
**Satu snapshot per hari.** Bukan real-time stream. Scraper jalan otomatis dini hari, data siap sebelum jam 07.00 WIB. Giel duduk satu kali per sesi pagi untuk baca, analisa, dan tulis di Reading Workspace — bukan AI yang generate analisa untuknya.

### Bank Data — Schema

> **Catatan arsitektur multi-aset:** `daily_market` adalah **konteks makro global yang dibagi semua aset** (DXY, US10Y, net liquidity, F&G, VIX, dst) — satu row per tanggal. Harga aset yang ditradingkan (BTC, IHSG, Gold, Forex) pindah ke tabel universal `asset_ohlcv` (lihat 4.3). Kolom `btc_*` di bawah tetap ada karena BTC dominance/funding/OI berfungsi ganda sebagai sinyal makro crypto, bukan hanya harga.

#### Tabel: `daily_market` (konteks makro global — satu row per tanggal)
```
date                DATE        PRIMARY KEY
btc_open            FLOAT
btc_high            FLOAT
btc_low             FLOAT
btc_close           FLOAT
btc_volume          FLOAT
btc_volume_ma20     FLOAT       (calculated)
btc_dominance       FLOAT
btc_funding_rate    FLOAT
btc_oi              FLOAT       (single-exchange, Binance)
btc_oi_aggregate    FLOAT       (v1.5 — agregat lintas exchange: Binance+
                                OKX+Bybit, sumber Coinalyze, dijumlah manual
                                krn API tidak punya simbol gabungan siap pakai)

dxy_close           FLOAT
dxy_change_pct      FLOAT

sp500_close         FLOAT
sp500_change_pct    FLOAT

us10y_yield         FLOAT
us10y_change_bps    FLOAT

vix_close           FLOAT       (mandatory — carry-unwind signal)
usd_jpy             FLOAT       (mandatory — BOJ/JPY carry tracking)

walcl               FLOAT       (Fed balance sheet, FRED)
rrp                 FLOAT       (reverse repo, FRED)
tga                 FLOAT       (treasury general account, FRED)
net_liquidity       FLOAT       (calculated: WALCL − RRP − TGA)

fear_greed_value    INT
fear_greed_label    TEXT

ihsg_close          FLOAT       (Tier 2)
ihsg_change_pct     FLOAT       (Tier 2)
usd_idr             FLOAT       (Tier 2)
gold_close          FLOAT       (Tier 2)

btc_long_short_ratio FLOAT      (v1.5 — TERISI, sumber Coinalyze bukan Coinglass)
btc_liquidation_24h  FLOAT      (LEGACY, sengaja dibiarkan kosong — diperuntukkan
                                Coinglass di draft awal, tidak pernah diisi;
                                lihat 2 kolom liq long/short di bawah sbg
                                penggantinya, bukan dihapus krn migrasi
                                DROP COLUMN berisiko utk DB yang sudah hidup)
btc_liq_long_24h     FLOAT      (v1.5 — sumber Coinalyze, DIPISAH dari short:
                                RIVAN perlu baca komposisi, mis. rebound dgn
                                short-liq dominan = short-covering bukan
                                pembelian spot murni — 1 angka gabungan tidak
                                bisa jawab itu)
btc_liq_short_24h    FLOAT      (v1.5 — pasangan kolom di atas)
stablecoin_supply    FLOAT      (optional — dry powder proxy, belum dikerjakan)
hy_credit_spread     FLOAT      (TERISI, FRED BAMLH0A0HYM2 — dibatasi rolling
                                3-tahun oleh lisensi sumber ICE Data, bukan gap)
bi_fed_spread        FLOAT      (optional — calculated: BI rate − Fed rate,
                                belum dikerjakan)

created_at          TIMESTAMP
source_flags        JSON        (status per API: ok/fail)
```

#### Tabel: `asset_ohlcv` (universal — harga semua aset yang ditradingkan)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE
instrument          TEXT        (BTC / IHSG / SP500 / GOLD / USDIDR / USDJPY / dll)
open                FLOAT
high                FLOAT
low                 FLOAT
close               FLOAT
volume              FLOAT
volume_ma20         FLOAT       (calculated)
created_at          TIMESTAMP

UNIQUE(date, instrument)

Satu tabel untuk SEMUA aset. Nambah aset baru = nambah row dengan label
instrument berbeda, BUKAN nambah tabel. Engine ③ (OLAH) baca tabel ini,
jalankan logika S&R + breakout/retest yang sama, output per instrument.
Inilah yang bikin pipeline "satu mesin, banyak aset".
```

#### Tabel: `econ_calendar` (sumbu waktu prediksi — berisi event MASA DEPAN)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
event_date          DATE        (tanggal event — bisa di masa depan)
event_time          TEXT        (jam rilis, kalau ada)
event_name          TEXT        (FOMC / CPI / NFP / RDG BI / options expiry)
country             TEXT        (US / ID / JP / dll)
importance          TEXT        (HIGH/MED/LOW)
forecast            TEXT        (konsensus, kalau ada)
previous            TEXT        (rilis sebelumnya)
actual              TEXT        (diisi setelah rilis)
is_watched          BOOLEAN     (Giel flag sebagai katalis kunci)
created_at          TIMESTAMP

Sumber: ForexFactory / Trading Economics (scrape). Ini satu-satunya tabel
yang menyimpan tanggal DEPAN — jadi tulang punggung "katalis apa, kapan".
Dipakai juga oleh rule SOP: pindahkan SL ke breakeven sebelum event HIGH.
```

#### Tabel: `daily_news` (dari RSS aggregator, tampil mentah — tanpa AI summary otomatis)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE        FOREIGN KEY → daily_market
source              TEXT        (FED/BI/MACRO/CRYPTO/NASDAQ)
headline            TEXT
raw_url             TEXT
impact_level        TEXT        (HIGH/MED/LOW — rule-based keyword scoring, bukan LLM)
is_key_trigger      BOOLEAN     (flag manual oleh Giel setelah baca)
created_at          TIMESTAMP
```

#### Tabel: `reading_workspace` (analisa manual Giel — pengganti "daily_analysis" versi lama)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE        FOREIGN KEY → daily_market
lens                TEXT        (GEMA/LEON/AKELA/RIVAN/SYNTHESIS)
notes               TEXT        (ditulis manual oleh Giel)
external_ai_ref     TEXT        (opsional: catatan banding dari TradingAgents/qrak/dll)
verdict             TEXT        (satu kalimat, ditulis Giel)
created_at          TIMESTAMP
```

#### Tabel: `trade_signals` (suggest dari tools, sebelum di-approve Giel)
```
id                  INT         PRIMARY KEY
date                DATE        FOREIGN KEY
instrument          TEXT        (BTC default)
signal_type         TEXT        (BREAKOUT/RETEST/WAIT)
entry_price         FLOAT
sl_price            FLOAT
tp1_price           FLOAT
tp2_price           FLOAT       (optional)
rr_ratio            FLOAT
zone_lower          FLOAT
zone_upper          FLOAT
volume_confirmed    BOOLEAN
is_valid            BOOLEAN     (R:R >= 1.5)
giel_approved       BOOLEAN     (default false — diisi manual)
notes               TEXT
created_at          TIMESTAMP
```

#### Tabel: `sr_zones` (bank zona S&R — semi-otomatis + validasi manual)
```
id                  INT         PRIMARY KEY
instrument          TEXT
zone_lower          FLOAT
zone_upper          FLOAT
touch_count         INT
zone_type           TEXT        (SUPPORT/RESISTANCE)
first_seen          DATE
last_touched        DATE
is_active           BOOLEAN
validated_by_giel   BOOLEAN     (default false)
notes               TEXT
```

#### Tabel: `manual_articles` (input manual — bukan dari scraper otomatis)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE
source              TEXT
url                 TEXT
headline            TEXT
full_text           TEXT
personal_notes      TEXT        (catatan/interpretasi Giel)
tags                TEXT        (comma-separated, custom)
is_key_event        BOOLEAN     (flag event yang mengubah view)
created_at          TIMESTAMP
```

#### Tabel: `trading_journal` (catatan analisa & hasil trade personal — final record)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE
instrument          TEXT
setup_type          TEXT        (breakout/retest/lainnya)
entry_price         FLOAT
sl_price            FLOAT
tp1_price           FLOAT
outcome             TEXT        (WIN/LOSS/ONGOING)
personal_notes      TEXT
lesson_learned      TEXT
created_at          TIMESTAMP
```

#### Tabel: `prediction_log` (catatan & skor prediksi — jantung "mesin prediksi")
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date_made           DATE        (kapan prediksi dibuat)
horizon             TEXT        (1w / 2w / 1m)
claim               TEXT        (mis. "BTC tembus $70K sebelum FOMC")
confidence          INT         (% keyakinan saat dibuat)
basis               TEXT        (data/lensa apa yang dipakai)
target_date         DATE        (kapan prediksi jatuh tempo dinilai)
outcome             TEXT        (BENAR/SALAH/PARTIAL — diisi nanti)
was_actioned        BOOLEAN     (apakah jadi trade beneran?)
lesson              TEXT        (apa yang dipelajari dari hasilnya)
created_at          TIMESTAMP

Kenapa wajib: tanpa tabel ini, yang dibangun cuma dashboard — bukan mesin
prediksi. Mesin prediksi sejati BELAJAR dari skornya sendiri. Track record
terukur ini juga moat brand: "ini prediksi saya 3 bulan lalu, ini skornya."
```

### 4.1 Manual Data Input — Filter Pull (Backfill)

Selain scraper otomatis harian, bank data punya **jalur input manual** yang dikontrol penuh oleh Giel — kapan pull, instrumen apa, rentang tanggal berapa. Tidak hardcoded ke rentang waktu tertentu.

```
INPUT FORM — Manual Backfill
├── Instrument     [dropdown: BTC / DXY / S&P500 / IHSG / Gold / USD-IDR]
├── Date Range     [from] — [to]
├── Timeframe      [1D default]
├── Source         [auto-mapped per instrument, lihat tabel di bawah]
└── [PULL] → preview jumlah row baru vs duplikat → [CONFIRM & SAVE]

SOURCE MAP per instrument
├── BTC            → Binance historical API
├── DXY, US10Y     → FRED API
├── S&P500, IHSG,
│   Gold, USD/IDR  → yfinance historical
```

Logic intinya: fetch → cek overlap dengan data yang sudah ada di `daily_market` → tampilkan preview (jumlah row baru, jumlah duplikat, rentang tanggal aktual yang berhasil ditarik) → baru commit ke database setelah dikonfirmasi. Mencegah data dobel atau korup tanpa sepengetahuan Giel.

Article (`manual_articles`) dan jurnal trading (`trading_journal`) lewat jalur input manual serupa — form sederhana, paste URL/teks atau tulis catatan langsung, sistem simpan dengan tanggal dan tag, bisa di-query nanti untuk riset historis (contoh: "apa yang saya pikirkan saat DXY breakout Maret 2026").

### 4.2 Forward-Looking Layer — dari Lagging ke Prediktif

**Masalah yang diselesaikan:** Semua data di `daily_market` adalah *lagging* — reaksi pasar terhadap sesuatu yang sudah terjadi. Untuk analisa prediktif, Kastara Finance perlu data *leading*: apa yang akan/diharapkan terjadi, dan ke mana arah pengambil kebijakan bergerak sebelum harga merespons.

**Prinsip penempatan (non-negotiable):** Forward-Looking Layer **menentukan lane, bukan menentukan entry.** Pembacaan arah Warsh/Purbaya/dll menggeser *bias* (lane mana yang boleh dimainkan), tapi entry tetap wajib breakout + retest + volume. Layer ini adalah bahan baca di Reading Workspace — bukan tombol/veto di chart engine. Ini menjaga decision chain tetap utuh dan mencegah framework prediksi dipakai untuk override sistem.

Dibangun bertahap dalam 3 stage:

#### Stage 1 — Layer B: Expectations (angka, paling konkret)
Data yang secara eksplisit forward-looking dan membingkai semua bacaan lain.

```
Tabel: expectations
├── id, date
├── metric           (cme_fedwatch_cut_prob / dot_plot_median /
│                      bond_implied_rate / dll)
├── value            FLOAT
├── horizon          TEXT   (next_meeting / EOY2026 / dll)
├── source           TEXT
└── created_at

Sumber:
├── CME FedWatch     → probabilitas rate cut implied (scrape,
│                       endpoint perlu diverifikasi saat build)
└── Fed Dot Plot/SEP → proyeksi internal Fed (manual, rilis kuartalan)
```

#### Stage 2 — Layer C: Positioning (apa yang DILAKUKAN, bukan dikatakan)
Validator untuk Layer A — kalau retorika dan posisi uang besar berbeda arah, itu disonansi yang patut dibaca.

```
Tabel: positioning
├── id, date
├── instrument       (BTC / DXY / GOLD / S&P / SBN / dll)
├── metric           (cot_net_long / etf_net_flow / sbn_foreign_flow)
├── value            FLOAT
├── source           TEXT
└── created_at

Sumber:
├── COT report       → CFTC, gratis, rilis mingguan (cadence pas
│                       untuk swing)
├── BTC ETF flow     → net flow harian
├── SBN foreign flow → DJPPR / data Indonesia — MASIH MANUAL (situs SPA,
│                       tidak scrape-able reliable, dicek langsung)
│                       ⚠️ ATURAN KONSUMSI (v1.6, menyelesaikan ketegangan
│                       dgn prompt persona v4): SBN flow EKSKLUSIF untuk
│                       bacaan manual Giel di Forward Panel (Layer C).
│                       TIDAK PERNAH masuk slice persona mana pun — prompt
│                       v4 melarang GEMA/LEON mengutipnya, dan larangan itu
│                       TETAP BERLAKU meski datanya kadang tersedia. Alasan:
│                       cadence manual-mingguan tidak cocok untuk analisa
│                       harian AI (risiko data basi dikutip sbg segar);
│                       untuk mata manusia yang tahu kapan data diinput,
│                       risiko itu tidak ada.
└── IHSG foreign flow → v1.5, OTOMATIS. Sumber: idx.co.id internal JSON API
    "Digital Statistic" (undocumented, ditemukan lewat source code proyek
    open-source NeaByteLab/IDX-API, dikonfirmasi live), tanpa API key, cuma
    session cookie. BUKAN pengganti SBN — SBN itu flow asing di obligasi,
    ini flow asing di ekuitas, dua metrik beda tapi saling melengkapi.
    Disimpan 3 komponen MENTAH terpisah + 1 net terhitung (metric prefix
    `ihsg_ff_*`), BUKAN cuma net — supaya slice persona (Section 6) bisa
    baca komposisi, bukan cuma arah:
      foreignForeign  (F2F) = Foreign Sell − Foreign Buy (asing-ke-asing,
                              BUKAN sinyal arah — rotasi internal)
      foreignDomestic (F2D) = Foreign Sell − Domestic Buy (sinyal distribusi
                              yang sah)
      domesticForeign (D2F) = Domestic Sell − Foreign Buy
      Foreign Net Buy = D2F − F2D (tervalidasi vs angka nyata 2026-06-02)
    Koreksi penting: label kolom `foreignForeign`/`foreignDomestic` di
    library referensi NeaByteLab/IDX-API keliru memetakannya sbg "buy"/
    "sell" langsung — label ASLI (dari `columns[].Title` response IDX
    sendiri) sudah dikonfirmasi ulang di atas.
```

#### Stage 3 — Layer A: Policy Maker Rhetoric (tinggi nilai, manual)
Crown jewel — bukan masalah scraper, tapi knowledge management. Tools hanya menyediakan struktur untuk menangkap pernyataan dan melacak *drift* arahnya dari waktu ke waktu. Interpretasi tetap kerja Giel.

```
Tabel: policy_tracker
├── id, date
├── speaker          (Warsh / Powell / Purbaya / dll)
├── institution      (Fed / BI / Kemenkeu / dll)
├── source_url
├── literal_statement   TEXT   ← apa yang BENAR-BENAR dikatakan (testable)
├── stance_score        INT    ← skala arah (mis. -2 dovish s/d +2 hawkish,
│                                atau fiskal ekspansif/kontraktif)
├── giel_inference      TEXT   ← baca arah/intent (your read)
├── inference_flag      TEXT   ← TESTABLE / SPEKULATIF
├── drift_note          TEXT   ← berubah dari pernyataan sebelumnya?
└── created_at
```

**Disiplin editorial wajib (built into schema):** setiap entry Layer A memisahkan `literal_statement` (yang testable) dari `giel_inference` (pembacaan), dan setiap inferensi diberi `inference_flag`. Inferensi spekulatif boleh dicatat, tapi **harus ditandai SPEKULATIF** — tidak boleh menyamar jadi fakta. Tanpa pemisahan ini, Layer A pelan-pelan jadi ruang konspiratif; dengan pemisahan ini, dia tetap analitis. Ini bagian dari identitas analitis Kastara Finance: klaim ekonomi yang testable dianalisa, framing spekulatif/ideologis dinamai sebagai spekulatif.

### 4.3 Multi-Asset Context Weighting

Pipeline universal, tapi tiap aset punya driver dominan berbeda. Supaya engine membaca tiap aset dengan context yang benar (bukan menyamaratakan), perlu tabel pemetaan bobot.

```
Tabel: asset_context_weight
├── instrument        (BTC / IHSG / SP500 / GOLD / FOREX)
├── driver            (net_liquidity / us10y / dxy / ihsg_foreign_flow /
│                       sbn_foreign_flow / etf_flow / dll)
├── weight            (HIGH / MED / LOW — seberapa dominan driver ini)
└── notes

Contoh isi (v1.6 — baris IHSG disinkronkan dgn keputusan IHSG foreign flow):
BTC   → net_liquidity=HIGH, etf_flow=HIGH, fear_greed=MED, dxy=MED
GOLD  → real_yield=HIGH, dxy=HIGH, geopolitik=MED
SP500 → earnings=HIGH, fed_path=HIGH, net_liquidity=MED
IHSG  → ihsg_foreign_flow=HIGH, usd_idr=HIGH, bi_rate=HIGH,
        sbn_foreign_flow=MED (manual/mingguan — Forward Panel only,
        bukan slice persona), komoditas=MED
FOREX → rate_differential=HIGH, trade_balance=MED
```

Fungsinya: saat Forward Panel & Reading Workspace membaca suatu aset, panel menyorot driver ber-bobot HIGH untuk aset itu lebih dulu. IHSG tidak dibaca lewat lensa ETF BTC; dibaca lewat foreign flow & IDR. Ini mencegah salah-baca saat sistem di-scale ke banyak aset. Bobot awal di-seed manual oleh Giel (judgment), bisa di-refine seiring data `prediction_log` menunjukkan driver mana yang benar-benar prediktif per aset.

---

## 5. PIPELINE ARCHITECTURE

### Jadwal Eksekusi
```
00.00 WIB     → Scraper otomatis jalan (US market sudah close)
00.00–05.00   → Pull semua data Tier 1 + Tier 2, simpan ke daily_market
                Pull & rank RSS news ke daily_news (rule-based scoring, bukan LLM)
05.00–06.00   → Indicator engine jalan: MA, volume ratio, S&R zone re-check,
                breakout/retest detection → tulis ke trade_signals (giel_approved=false)
06.00–06.30   → Chart render siap (BTC + 4 context chart)
06.30         → Dashboard siap dibuka
07.00         → Giel buka dashboard:
                baca daily_news, isi reading_workspace manual,
                review/approve trade_signals, opsional cross-check
                dengan AI agent eksternal (TradingAgents/qrak/dll)
07.30+        → Tulis ke trading_journal kalau ambil posisi
                Opsional: jadikan bahan konten
```

### Tech Stack
```
SCRAPER LAYER
├── Python (requests, yfinance, feedparser)
├── CoinGecko API         → BTC price, dominance
├── Binance Public API    → OHLCV, funding rate, OI
├── FRED API              → DXY, US10Y
├── Yahoo Finance         → S&P500, IHSG, USD/IDR, Gold
├── Alternative.me        → Fear & Greed
└── RSS Parser            → Reuters, Kontan, CNBC ID, Fed RSS, BI scraper

DATABASE LAYER
├── SQLite (development / awal)
└── PostgreSQL (kalau scale / multi-device access)

ANALYSIS LAYER (tools — bukan AI agent otomatis)
├── Python + pandas         → indicator calculation
├── pandas-ta                → MA, RSI, volume analysis
├── Custom S&R detector      → zone clustering + touch count
├── Signal engine            → breakout + retest + R:R validator
└── (opsional, manual trigger) Anthropic API → bantu Giel ringkas 1 artikel
    saat diminta — bukan proses otomatis tiap pagi
    + OpenRouter (llm/persona_analysis.py) → 4 lensa Panel 4, dipicu manual
    per kartu (deviasi v1.5, lihat Section 1)

DASHBOARD LAYER
├── Python + Flask/FastAPI → backend API
├── HTML + JS              → frontend dashboard
└── Chart: custom SVG/Canvas → bukan TradingView dependency

CONTENT OUTPUT (Phase 2+, opsional, tidak wajib di Phase 1)
├── Telegram bot           → push daily briefing kalau sudah mulai publish
└── X/Twitter              → short-form insight manual
```

**Catatan:** Anthropic API/LLM bukan proses wajib yang jalan otomatis tiap pagi. Posisinya jadi *alat bantu opsional* yang Giel panggil manual kapan perlu (misal minta ringkas satu artikel panjang) — bukan generator analisa 4 persona otomatis.

---

## 6. DASHBOARD STRUCTURE

### Layout Utama (6 Panel)

```
┌─────────────────────────────────────────────────────┐
│  HEADER: Kastara Finance · tanggal · run status     │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│   SIDEBAR    │         MAIN CONTENT AREA            │
│              │                                      │
│  • Nav       │   [Panel aktif berdasarkan step]     │
│  • Macro     │                                      │
│    snapshot  │                                      │
│  • Signal    │                                      │
│    status    │                                      │
│              │                                      │
└──────────────┴──────────────────────────────────────┘
```

### Panel 1 — Data Snapshot
**Tujuan:** Konfirmasi semua data berhasil di-pull
**Isi:** 9 metric cards (BTC OHLCV, DXY, S&P500, US10Y, F&G, BTC Dom, Funding Rate, IHSG, USD/IDR), source + timestamp per data point, log eksekusi scraper, flag merah kalau ada source gagal. Tombol akses ke form Manual Backfill (Section 4.1) ada di panel ini.

### Panel 2 — News Briefing
**Tujuan:** Bahan baca, bukan kesimpulan jadi
**Isi:** News cards ranked by impact (HIGH/MED/LOW, rule-based keyword scoring), source label + timestamp, tombol flag manual "key trigger" yang Giel klik sendiri setelah baca. Tombol "+ Add Manual Article" untuk masuk ke `manual_articles`.

### Panel 3 — Forward Panel (Prediction Layer)
**Tujuan:** Membingkai bacaan harian dengan data leading sebelum Giel menulis analisa
**Posisi:** Sengaja ditaruh SEBELUM Reading Workspace — karena ekspektasi, positioning, dan arah retorika harus dibaca dulu sebagai konteks.
**Isi:**
- **Expectations (Layer B):** CME FedWatch cut probability, Dot Plot median terakhir — angka, ringkas
- **Positioning (Layer C):** COT net long BTC/DXY/Gold, ETF flow, IHSG foreign flow (otomatis), SBN foreign flow (manual mingguan — **hanya tampil di panel ini**, tidak masuk slice persona) — arah uang besar
- **Policy Tracker (Layer A):** entri terbaru dari `policy_tracker`, dengan `literal_statement` dan `giel_inference` terpisah jelas, flag SPEKULATIF terlihat. Tombol "+ Add Policy Note" untuk input manual.
- **Economic Calendar:** event HIGH/MED yang datang (dari `econ_calendar`) — countdown ke FOMC/CPI/RDG BI berikutnya. Ini sumbu waktu: "katalis apa, berapa hari lagi."
- **Disonansi flag:** kalau retorika (Layer A) dan positioning (Layer C) berlawanan arah, panel menandai — ini sinyal yang patut dibaca, bukan kesimpulan otomatis.
> Reminder di panel: layer ini menggeser BIAS/LANE, bukan trigger entry. Entry tetap dari Panel 5 (chart) dengan breakout + retest + volume.

### Panel 4 — Reading Workspace
**Tujuan:** Tempat Giel membaca 4 lensa analisa sebagai struktur berpikir sebelum synthesis
**Isi (v1.6 — label lensa DIKOREKSI dari v1.5):** 4 kartu berlabel fungsi — kode internal GEMA/LEON/AKELA/RIVAN disembunyikan dari UI:

```
Kartu 1 (GEMA)  : "Makro Global & Arus Modal"
Kartu 2 (LEON)  : "Kebijakan & Sistem Domestik"
Kartu 3 (AKELA) : "Timing, Ekspektasi & Pricing"
Kartu 4 (RIVAN) : "Struktur & Fundamental Aset"

⚠️ Koreksi v1.6: label v1.5 ("On-chain-Fundamental" untuk AKELA dan
"Sentimen & Psikologi Pasar" untuk RIVAN) MENUKAR domain kedua lensa dan
memberi label yang tidak dimiliki lensa mana pun. Per prompt v4: AKELA
BUKAN analis sentimen (F&G/funding hanya INPUT pricing-in miliknya), dan
RIVAN BUKAN analis psikologi (dia realis struktural — funding/OI/likuidasi
adalah "neraca"-nya kripto). Tidak ada lensa "Sentimen & Psikologi" di
sistem ini — itu by design, bukan kelalaian: sentimen adalah input, bukan
sudut pandang. Label UI dibaca setiap pagi; label yang salah pelan-pelan
membentuk ulang cara lensa dipakai.
```

Tombol "Jalankan Analisa" per kartu memicu 1 panggilan OpenRouter (`llm/persona_analysis.py`), hasil tampil read-only di popup modal. System prompt tiap persona (`prompts/persona_<lens>.txt`) ditulis manual oleh Giel sendiri — jadi arah analisanya tetap ditentukan Giel, bukan default model.

**Shared Core + Slice (system prompt v4):** ke-4 persona TIDAK menerima data yang sama lagi (desain awal panel ini). Semua dapat **Shared Core** (tanggal, berita key, BTC close+delta) — lalu tiap lensa dapat **slice berbeda** dari kolom Panel 1/3 sesuai fokusnya:
- **GEMA** (Makro Global & Arus Modal): DXY/US10Y/VIX/Net Liquidity/USD-JPY/Gold/SP500/BTC Dominance, COT DXY, ETF flow, IHSG foreign flow dibaca sbg **arah arus modal asing**, Policy Tracker speaker asing.
- **LEON** (Kebijakan & Sistem Domestik): IHSG/USD-IDR, IHSG foreign flow dibaca sbg **rapor kepercayaan kebijakan**, econ calendar ID, Policy Tracker speaker domestik.
- **AKELA** (Timing, Ekspektasi & Pricing): econ calendar penuh (forecast/previous/actual), FedWatch/Dot Plot, Disonansi Flag, Fear & Greed histori + funding rate **sebagai input pricing-in/exhaustion — bukan lensa sentimen**, VIX, Vol MA20, delta semua horizon.
- **RIVAN** (Struktur & Fundamental Aset): funding rate, OI agregat+delta, liquidation long/short 24h, L/S ratio, ETF flow, volume vs MA — dibaca sebagai **struktur/neraca aset**; untuk emiten: fundamental kuartalan (Phase J+).

Field yang sama sengaja diberikan ke 2 slice dengan framing beda (mis. funding rate ke AKELA & RIVAN, IHSG foreign flow ke GEMA & LEON) dianggap "konflik produktif", bukan duplikasi yang perlu dihapus. **SBN foreign flow tidak masuk slice mana pun** (lihat 4.2 Stage 2).

Kolom opsional "External AI Check" untuk catat & banding hasil dari TradingAgents/qrak/LLM_trader/lainnya — diadu, bukan diikuti otomatis. Area "Conflict Notes" bebas untuk catat poin yang Giel sendiri belum sepakat antar lensa. Hasil 4 lensa (AI) + External AI Check + Conflict Notes semua tersimpan ke `reading_workspace` — TIDAK ada tabel baru untuk pivot ini, cuma isinya yang sekarang campuran AI-generated (lensa) dan manual (sisanya).

### Panel 5 — Chart + Technical Analysis
**Tujuan:** Visual konfirmasi setup trading, dengan suggestion dari engine
**Isi:**

BTC Chart (Trade Engine): daily OHLCV candles (90 hari dari bank data), MA50/100/200 overlay, volume bars + volume MA20, S&R zones overlay (dari `sr_zones`), marker breakout/retest point, anotasi entry/SL/TP1 kalau ada sinyal di `trade_signals`. Tombol "Approve Signal" / "Reject" yang menulis ke `giel_approved`.

Context charts (4 kecil): DXY, S&P 500, US10Y, Fear & Greed — masing-masing 30 hari, untuk baca lingkungan makro, bukan untuk trading langsung.

### Panel 6 — Synthesis (Personal Record)
**Tujuan:** Tempat Giel menulis kesimpulan harian — bukan output otomatis
**Isi:** Textarea bebas untuk paragraf synthesis pribadi (ditarik dari isi Panel 4, ditulis ulang oleh Giel sendiri). Outlook per instrumen (Bullish/Bearish/Neutral) — dropdown manual, bukan dihitung sistem. Kartu sinyal trading yang sudah di-approve dari Panel 5, ditampilkan ulang sebagai ringkasan akhir sebelum disimpan ke `trading_journal`.

**Prediction capture:** form ringkas untuk catat 1 prediksi ke `prediction_log` (claim, horizon, confidence, basis, target_date). Plus widget "Skor Prediksi": tampilkan prediksi lama yang sudah jatuh tempo, minta Giel nilai BENAR/SALAH/PARTIAL. Ini calibration loop — bagian yang bikin sistem makin tajam tiap bulan.

```
SIGNAL: BREAKOUT DETECTED / WAIT RETEST / NO SETUP
─────────────────────────────────────────
Instrument  : BTC/USDT
Setup       : Breakout + Retest
Entry       : $68,200
Stop Loss   : $66,800  (daily close di bawah zona)
TP1         : $71,500  (resistance terdekat)
R:R         : 1 : 2.4
Volume      : ✓ Confirmed
Status      : SUGGESTED — menunggu approve Giel
```

---

## 7. CHART ANALISA — TECHNICAL ENGINE

### Indikator yang Di-compute dari Bank Data
```
TREND
├── MA20, MA50, MA100, MA200 (simple)
├── Price vs MA position (above/below)
└── MA stack order (bullish/bearish alignment)

VOLUME
├── Volume MA20
├── Volume ratio (hari ini vs MA20)
└── Breakout volume flag (ratio > 1.5 = confirmed)

MOMENTUM (opsional, Phase 2)
├── RSI 14
└── MACD (12, 26, 9)

S&R DETECTION (custom, semi-otomatis)
├── Swing high / swing low detection (lookback 20 hari)
├── Zone clustering (harga dalam range ±0.5%)
├── Touch count per zone
├── Zone validity (minimum 2–3 touches)
└── Validasi akhir tetap manual Giel sebelum zone dianggap aktif

SIGNAL DETECTION
├── Breakout: close > resistance zone upper + volume confirmed
├── Retest: price returns to zone + close above zone lower + volume hadir
└── Suggest entry = close candle retest, suggest SL = bawah zona, suggest TP1 = resistance berikutnya, R:R auto-calculated
```

---

## 8. CONTENT OUTPUT (Phase 2+ — opsional, tidak prasyarat Phase 1)

Konten dibuat dari isi `reading_workspace` dan `trading_journal` yang sudah ditulis Giel — bukan template auto-generate. Format berikut adalah kerangka, isinya tetap tulisan manual.

### Daily Briefing (kalau publish ke Telegram/X)
```
🔷 KASTARA FINANCE · [tanggal]

📊 MARKET SNAPSHOT
BTC: $XX,XXX (+X.X%) | DXY: XX.XX | F&G: XX

📰 KEY EVENTS
[headline yang Giel flag sebagai key trigger]

🧠 4 LENSA (ditulis Giel)
GEMA: [satu kalimat]
LEON: [satu kalimat]
AKELA: [satu kalimat]
RIVAN: [satu kalimat]

📈 SIGNAL
[status dari trade_signals yang sudah di-approve, kalau ada]

⚠️ Ini bukan rekomendasi finansial.
Keputusan ada di tangan kamu.
```

### Video Format (kalau dan kapan mulai bikin konten video)
```
00:00  Sapa audience + state event hari ini
00:30  Buka Panel 1 — Data Snapshot
01:30  Panel 2 — News Briefing
02:30  Panel 3 — Reading Workspace, jelaskan proses berpikir per lensa
05:00  Panel 4 — Chart BTC, jelaskan setup
07:00  Context chart — DXY, S&P, US10Y
08:30  Panel 5 — Synthesis pribadi
09:30  Signal card kalau ada, dan kenapa diambil/dilewatkan
10:00  Close
```

---

## 9. STRATEGI ADOPSI REPO — License & Borrow Policy

Kastara Finance dibangun dengan ATM (Amati, Tiru, Modifikasi): tidak ada konsep baru yang perlu ditemukan ulang, jadi adopsi dari repo lain mempercepat drastis. Tapi adopsi punya dua rambu yang tidak boleh dilanggar: **rambu lisensi** (hukum) dan **rambu pipa-vs-otak** (strategi).

### 9.1 Prinsip "Frankenstein yang waras"
Bukan membangun ulang lima sistem — tapi mencabut **satu organ terbaik** dari tiap repo dan merakitnya untuk tujuan baru yang tidak satu pun donornya punya: **gerbang analisa untuk manusia memutuskan, bukan mesin mengeksekusi.** Kelima repo mengarah ke otomasi (hilangkan manusia); Kastara membalik arah ke augmentasi (pertajam manusia). Organ sama, tujuan berlawanan, spesies berbeda.

```
DARI                AMBIL ORGAN                 BUANG
──────────────────────────────────────────────────────────────
Nautilus (MIT)    → pola async/event-driven   → execution engine
FinRL (MIT)       → cara hitung indikator      → RL / black-box
OpenBB (AGPL!)    → ingestion multi-source     → JANGAN copy code;
                                                 pakai via API saja
Deltalytix        → ide log + statistik        → IB integration
                    (cek lisensi dulu)
Streamlit ecosys  → kecepatan bikin UI         → kedangkalannya
```

### 9.2 Rambu lisensi (hukum — tidak bisa ditawar)
Lisensi tidak peduli seberapa banyak code diubah. Modifikasi berat tetap menghasilkan *derivative work* yang terikat lisensi asal. Yang menentukan cuma dua: **lisensi sumber** dan **cara pakai**.

```
LISENSI SUMBER
├── MIT / Apache 2.0  → AMAN. Copy, modif, komersil, proprietary OK.
│                       Cukup pertahankan notice lisensinya.
├── GPL               → copy code = SELURUH proyek wajib jadi GPL.
└── AGPL  ⚠️          → lebih ketat. Akses lewat JARINGAN (web/Telegram/
                        dashboard) sudah dihitung distribusi → wajib buka
                        SELURUH source, termasuk moat. RACUN untuk proyek
                        proprietary seperti Kastara.

CARA PAKAI (menentukan untuk repo copyleft)
├── Copy/modif code ke repo Kastara → derivative work → lisensinya menular
└── Pakai sebagai service/library terpisah (API call) → Kastara cuma
    CONSUMER → code Kastara tetap milik sendiri → AMAN

Contoh konkret OpenBB (AGPLv3, terverifikasi):
✅ pip install openbb → panggil obb.equity.price.historical(...) → aman
❌ copy file source OpenBB ke dalam repo Kastara → AGPL menular
(catatan: batas "linking vs derivative" untuk AGPL itu area abu-abu hukum;
 amannya pakai via API publik, jangan tarik source ke dalam repo.)
```

**Checklist 30 detik sebelum adopsi repo apa pun:**
```
[ ] Buka file LICENSE — MIT/Apache? GPL/AGPL?
[ ] Kalau MIT/Apache → copy/modif bebas, simpan notice
[ ] Kalau GPL/AGPL → JANGAN copy code; pakai via API kalau bisa,
    atau tulis ulang idenya clean-room (lihat 9.3)
[ ] Catat asal tiap potongan code → biar jelas mana milik siapa
```

### 9.3 Rambu pipa-vs-otak (strategi)
"Cepat adopsi semua" benar untuk pipa, jebakan untuk otak.

```
PIPA (kotak ①–④)        → ADOPSI AGRESIF
data, storage, indikator,   commodity — semua repo punya. Copy yang MIT,
chart, dashboard            rewrite yang AGPL. Hemat berbulan-bulan.

OTAK (kotak ⑤–⑥)        → TULIS SENDIRI
forward layer, reading,     TIDAK ADA repo yang punya ini. Tidak ada yang
prediction log,             bisa diadopsi — memang harus orisinal. Justru
konteks Indonesia           DI SINI letak "barang barunya". Kalau semua bisa
                            diadopsi, Kastara cuma remix. Yang bikin baru
                            adalah bagian yang harus ditulis tangan.
```

**Rumus:** cepat di pipa, orisinal di otak. Kecepatan adopsi di ①–④ membebaskan waktu — supaya energi tertumpah ke ⑤–⑥, bagian yang benar-benar Kastara dan tidak bisa di-clone siapa pun.

### 9.4 ATM versi aman
```
AMATI       → bebas. Pelajari arsitektur/pola repo apa pun, tanpa batas.
              Ide tidak berlisensi.
TIRU        → untuk AGPL: "tiru" = tulis ULANG idenya clean-room dengan
              code sendiri. BUKAN copy lalu modif. Untuk MIT/Apache: copy boleh.
MODIFIKASI  → modif code copyleft TIDAK melepas lisensi. Modif sebanyak
              apa pun tetap turunan. Hanya MIT/Apache yang aman dimodif bebas.
```

---

## 10. BUILD ORDER (Hands-On)

Dibagi dua dimensi. **PHASE A–E = bangun mesin sekali untuk BTC** (full pipeline jadi & teruji). **PHASE F+ = replikasi ke aset lain** (murah, karena pipeline sama — tinggal data + context weight + penyajian). Disiplin: jangan masuk Phase F sebelum A–E solid untuk BTC.

> **Status v1.6: Foundation A–E ✅ dan Expansion F–I ✅ SELESAI.** Checklist di
> bawah dipertahankan sebagai arsip desain. Build aktif = Phase J+ (Section 12).

```
═══════════════════════════════════════════════════════
  FOUNDATION — bangun mesin sekali (instrument = BTC)   ✅ SELESAI
═══════════════════════════════════════════════════════

PHASE A — DATABASE & SCRAPER
[x] Setup SQLite schema (semua tabel: daily_market, asset_ohlcv,
    daily_news, econ_calendar, reading_workspace, trade_signals,
    sr_zones, manual_articles, trading_journal, prediction_log,
    asset_context_weight + tabel forward layer)
[x] Scraper: CoinGecko + Binance (BTC → asset_ohlcv + makro crypto)
[x] Scraper: FRED (DXY, US10Y, VIX, WALCL/RRP/TGA → net liquidity, HY spread)
[x] Scraper: yfinance (S&P500, Gold, USD/IDR, USD/JPY → context)
[x] Scraper: Alternative.me (Fear & Greed)
[x] Scraper: Economic Calendar (ForexFactory/Trading Economics)
[x] RSS parser: news ingestion + rule-based impact scoring
[x] Manual fetch tool (filter instrument + date range)
[x] Scheduler: cron job lokal 00.00 WIB (VPS nanti)

PHASE B — ANALYSIS ENGINE (universal, di-test di BTC dulu)          ✅
PHASE C — DASHBOARD (6 panel, instrument = BTC)                     ✅
PHASE D — FORWARD-LOOKING LAYER (Stage 1–3, lihat 4.2)              ✅
PHASE E — TELEGRAM (jendela baca dari luar)                         ✅

═══════════════════════════════════════════════════════
  EXPANSION — replikasi ke aset lain (pipeline sama)     ✅ SELESAI
═══════════════════════════════════════════════════════

PHASE F — GOLD    ✅   PHASE G — IHSG   ✅
PHASE H — S&P 500 ✅   PHASE I — FOREX  ✅

* Catatan: data context (DXY, US10Y, dst) sudah ditarik sejak Phase A,
  jadi expansion sebagian besar = penyajian + pembobotan, bukan scraping baru.
```

---

## 11. OPEN QUESTIONS — Status

```
1. Database location  → RESOLVED: local dulu, VPS nanti
2. Scheduler          → RESOLVED: cron lokal dulu, VPS nanti
3. Dashboard access   → RESOLVED: Telegram sebagai jendela baca dari luar
4. S&R zones awal     → RESOLVED: hybrid — auto-detect kasih kandidat,
                        Giel validasi (validated_by_giel), bisa seed manual
                        beberapa zona kunci sebagai baseline
5. Backfill awal      → RESOLVED: manual fetch tool naik ke Phase A sebagai
                        bootstrap; Giel tarik data historis manual sebelum live
6. SBN vs persona     → RESOLVED (v1.6): SBN flow eksklusif Forward Panel
                        (bacaan manual Giel); tidak pernah masuk slice persona.
                        Prompt v4 dan masterplan kini sinkron. (lihat 4.2)
```

---

## 12. PHASE J+ — EQUITY EXPANSION (Multi-Market, Saham Individual)

**Status: Build Contract v1.3 LOCKED (11 Juli 2026), kickoff berjalan.**

> **Single Source of Truth (aturan v1.6):**
> - **SPESIFIKASI** (schema final, rubrik grader, kalibrasi per-market, sizing,
>   execution layer, keputusan G1–G7) = **`phase_j_build_contract_v1_3_LOCKED.md`**.
>   Section ini TIDAK menyalin nomor langkah atau detail field dari kontrak —
>   kalau ada beda antara section ini dan kontrak, KONTRAK yang benar.
> - **EKSEKUSI HARIAN** (checklist, changelog) = [ROADMAP.md](ROADMAP.md).
> - **Masterplan (dokumen ini)** = strategi & konsep inti saja.
>
> Catatan v1.5 "5 tabel draft karena dokumen sumber belum diberikan" DITUTUP:
> kontrak v1.3 berisi spesifikasi final `fundamentals_quarterly`,
> `earnings_calendar`, `sector_benchmark`, `emiten_grade`, `grader_log` —
> serahkan file kontrak ke Claude Code, sinkronkan schema.sql, cabut tanda draft.

### Kenapa expansion ini beda dari Section 3/Phase F-I

Phase F–I memperluas **satu gerbang analisa** ke aset makro/index — instrumen
sedikit dan tetap. Phase J+ memperluas gerbang yang SAMA ke **saham individual**
(mulai IDX, lalu US) — populasi instrumen jauh lebih besar dan tiap instrumen
bawa kompleksitas baru yang tidak ada di aset makro: fundamental kuartalan,
kalender earnings, klasifikasi sektor, ARA/ARB (daily limit), lot size, dan
risiko "instrumen baru asal ditambahkan langsung bisa ditradingkan tanpa
validasi" — karena itu Phase J+ dirancang dengan **gerbang (gate) eksplisit**,
bukan tinggal "nyalain instrument baru" seperti Phase F-I.

### Prinsip inti Phase J+ (ringkasan strategis — detail di kontrak)

- **`lane` per instrumen (TRADE / INVEST / BOTH / NONE)** — menentukan APAKAH
  instrumen boleh dipakai mesin untuk generate `trade_signals`. Instrumen baru
  WAJIB masuk `INVEST`/`NONE` dulu sampai divalidasi bar-replay
  (`lane_validated_at`). Perpanjangan langsung "Mesin merakit, Giel
  memprediksi" (Section 0).
- **Hierarki keputusan (kalimat resmi, keputusan terkunci #1):** persona
  menentukan LANE → engine menemukan KANDIDAT trigger → **Giel memutuskan di
  gerbang akhir.** Rules Entry (Section 3) tidak berubah — expansion menambah
  CAKUPAN, bukan mengubah validasi sinyal.
- **3 Gerbang (G1 lane+SOP, G2 universe, G3 sumber fundamental)** — semua
  butuh input Giel langsung, tidak bisa diasumsikan.
- **Emiten Grader** — dua sumbu (kualitas fundamental 0–100 × flag integritas
  pasar) → kuadran INVESTABLE/WATCH/SPECULATIVE/AVOID. Grade = context &
  filter universe, BUKAN trigger. `grader_log` = satu-satunya jalur legal
  revisi bobot (anti-overtuning). OSINT sosial = Phase 2 grader, backlog
  bersyarat.
- **Sizing & lot quantization** — pembulatan KE BAWAH, skip
  `RISK_CAPACITY_EXCEEDED`, larangan geser SL untuk memuat lot, buffer
  ARA/ARB 1.5× (default guideline, revisi hanya lewat jurnal). Sistem bicara
  satuan risiko, bukan "mahal/murah".
- **Execution manual-only (Stockbit/IBKR)** — larangan API trading broker
  berlaku untuk fase J–K; pertimbangan ulang di masa depan wajib lewat review
  tertulis terpisah, dilakukan saat TIDAK dalam posisi/drawdown (guard di
  kontrak Section 15).
- **Aturan earnings saham AS: versi penuh** — posisi ditutup sebelum tanggal
  earnings, tanpa kompromi size.

### Yang menunggu Gerbang (bukan gap teknis)

Universe list penuh (G2 — build dimulai dari BBCA sebagai instrumen tunggal),
lane final semua instrumen + amandemen SOP v4.1 (G1), sumber fundamental final
(G3), UI manual-input dashboard (backlog eksplisit — saat ini via CLI
`pipeline/seed_universe.py`), dan modul Emiten Grader itu sendiri.

---

*Kastara Finance Master Plan v1.6 — Foundation A–E ✅, Expansion F–I ✅,
persona AI-generated dgn label lensa terkoreksi (Section 6), SBN-persona
tension resolved (Section 4.2, 11), Phase J+ locked dgn kontrak v1.3 sebagai
single source of truth spesifikasi (Section 12). Living document — histori
perubahan & eksekusi harian ada di [ROADMAP.md](ROADMAP.md).*