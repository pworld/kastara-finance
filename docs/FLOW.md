# Kastara Finance — Data Flow

> Pendamping [ARCHITECTURE.md](ARCHITECTURE.md) (apa & kenapa) — dokumen ini
> fokus ke **bagaimana data bergerak** lewat sistem. Diagram pakai Mermaid
> (render otomatis di GitHub/VS Code; kalau viewer tidak support, baca versi
> teks di tiap bagian).

---

## 1. Alur Harian (`pipeline/run_daily.py`)

Dijalankan via **crontab per-user** `0 0 * * *` (TZ sistem sudah WIB, lihat
README §5), atau manual kapan saja.

> Catatan: diagram di bawah menggambarkan inti Phase A (5 scraper makro). Sejak
> Phase D/J+ `run_daily` juga memanggil `positioning.py` (COT+ETF), `coinalyze.py`
> (OI/liquidation), `idx_foreign_flow.py` + `idx_stock_foreign_flow.py` (IHSG &
> per-saham), dan `equity_universe.py` (OHLCV saham) — pola identik (`safe_call`
> → `source_flags` → merge), cuma menambah cabang, tidak mengubah alur.

```mermaid
flowchart TD
    A[python -m pipeline.run_daily] --> B[init_db - pastikan 22 tabel ada]
    B --> C{Panggil scraper makro+ekuitas}
    C --> C1[crypto.py + coinalyze.py]
    C --> C2[macro_yf.py + equity_universe.py]
    C --> C3[macro_fred.py: FRED 7 series]
    C --> C4[news.py: RSS feeds]
    C --> C5[econ_calendar.py + positioning.py + idx_*_flow.py]

    C1 --> D[Tiap scraper: safe_call per sub-request]
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    D --> D1{Sukses?}
    D1 -->|ya| D2[flags.ok - lanjut]
    D1 -->|gagal| D3[flags.fail atau skip - print warning, lanjut]

    D2 --> E[Gabung semua source_flags jadi 1 dict]
    D3 --> E

    E --> F[Susun asset_ohlcv rows: BTC + 5 dari yfinance]
    F --> G[UPSERT asset_ohlcv by date+instrument]
    G --> H[Hitung volume_ma20 per instrument dari histori]
    H --> I[UPDATE asset_ohlcv SET volume_ma20]

    E --> J[Susun daily_market: merge crypto+yf+fred]
    J --> K[Hitung net_liquidity = walcl - rrp - tga]
    K --> L[UPSERT daily_market by date, termasuk source_flags JSON]

    E --> M[INSERT OR IGNORE daily_news]
    M --> N[Dedup ditegakkan oleh UNIQUE INDEX date+headline]

    E --> P1[UPSERT econ_calendar by event_date+event_name+country]
    P1 --> P2[Natural key ditegakkan UNIQUE INDEX - forecast di-refresh]

    I --> O[Print ringkasan: N ok / N fail / N skip]
    L --> O
    N --> O
    P2 --> O
```

**Poin penting:**
- Tahap C (panggil scraper) **tidak pernah crash** — tiap scraper menangkap
  error internal via `safe_call`, jadi satu API mati tidak menghentikan yang
  lain.
- Tahap G→H urutannya sengaja: `asset_ohlcv` ditulis dulu, baru
  `volume_ma20` dihitung dari histori (termasuk baris hari ini) dan
  di-`UPDATE` kembali.
- Idempotent: jalan 2× untuk tanggal sama → `UPSERT`/`INSERT OR IGNORE`
  membuat hasil akhir sama (bukan baris ganda). Sudah diverifikasi test.

---

## 2. Alur Backfill (`pipeline/backfill.py`)

Dipakai manual untuk mengisi histori (mis. 5 tahun ke belakang), sedikit demi
sedikit per instrument/range.

```mermaid
flowchart TD
    A["python -m pipeline.backfill --instrument X --from --to"] --> B{Map instrument ke sumber}
    B -->|BTC| C1[Binance klines range]
    B -->|SP500/IHSG/GOLD/USDIDR/USDJPY| C2[yfinance history range]
    B -->|DXY/US10Y/VIX/WALCL/RRP/TGA/HY| C3[FRED observations range]

    C1 --> D{Binance gagal?}
    D -->|ya| E[Fallback yfinance BTC-USD]
    D -->|tidak| F[rows]
    E --> F
    C2 --> F
    C3 --> F

    F --> G[Cek date yang SUDAH ADA di DB untuk instrument ini]
    G --> H[Hitung: N baris baru vs N duplikat]
    H --> I["PREVIEW dicetak ke terminal"]
    I --> J{User konfirmasi y/N ATAU --yes}
    J -->|N / tidak| K[Batal - TIDAK ADA yang ditulis]
    J -->|y / --yes| L[UPSERT ke asset_ohlcv ATAU daily_market]
    L --> M[Print: N baris baru ditulis, N duplikat di-skip]
```

**Poin penting:**
- **Preview selalu tampil sebelum commit** — tidak ada jalur yang menulis
  tanpa lihat preview dulu (kecuali `--yes` untuk automasi/testing, yang tetap
  menampilkan preview, hanya skip prompt-nya).
- Duplikat (`date`+`instrument` sudah ada) **di-skip, bukan error** — aman
  dijalankan berulang untuk range yang overlap.
- Cocok untuk pola "tarik sedikit-sedikit": jalankan per instrument, per
  range beberapa bulan, berkali-kali sampai 5 tahun tercakup — tidak perlu
  1 kali tarik semua sekaligus.

---

## 3. Alur Dashboard (`web/app.py`, read **+ write** sejak Phase C)

```mermaid
flowchart LR
    Browser -->|GET /| Flask[Flask app]
    Flask -->|render shell statis| HTML[templates/index.html + 8 partial]
    HTML -->|fetch JS| GET[33 endpoint GET /api/*]
    HTML -->|postJSON| POST[24 endpoint POST /api/*]

    GET --> DB[(kastara-finance.db\nmode DELETE + busy_timeout)]
    POST -->|web/writes.py + reuse pipeline| DB

    Pipeline[pipeline/run_daily.py + backfill.py + run_analysis + run_grader] --> DB
```

**Poin penting:**
- Sejak Phase C dashboard **membaca DAN menulis**: input manual (jurnal,
  prediksi, policy, intake, override grade, validasi lane, dll) lewat 24 POST
  endpoint. Penulisan tetap tidak menaruh logic baru di route — reuse
  `web/writes.py` (pure, testable) + fungsi pipeline yang sudah teruji.
- Route `/` cuma render **shell statis tanpa data server** — semua isi
  di-fetch client-side dari `/api/*` (batas data bersih → fondasi migrasi
  FE → Vue, [migrationFE.md](migrationFE.md)).
- Tetap **single-writer secara praktik**: penulisan dashboard singkat & jarang
  bersamaan dengan `run_daily`. Mode **DELETE** + `busy_timeout=5000` (bukan
  WAL — [ARCHITECTURE.md §6.1](ARCHITECTURE.md#61-sqlite-vs-postgres-vs-nosql))
  menjaga akses lintas Windows↔WSL predictable.
- `/api/latest` mengurai `source_flags` JSON jadi struktur siap-render
  (dot indikator ok/fail/skip di UI).

---

## 4. Siklus Hidup `source_flags`

```mermaid
sequenceDiagram
    participant S as Scraper (mis. macro_fred.py)
    participant F as SourceFlags
    participant P as run_daily.py
    participant DB as daily_market.source_flags

    S->>F: safe_call("fred_dxy", fetch_fn, flags)
    alt sukses
        F->>F: flags.ok("fred_dxy")
    else exception tertangkap
        F->>F: flags.fail("fred_dxy")
    else sengaja dilewati (mis. no API key)
        F->>F: flags.skip("fred_dxy")
    end

    S-->>P: return dict + source_flags per scraper
    P->>P: merge semua source_flags (semua scraper jadi 1 dict)
    P->>DB: simpan sebagai JSON di kolom source_flags
    Note over DB: {"fred_dxy":"ok","binance_ohlcv":"fail","rss_Kontan":"skip",...}
```

Dict ini adalah **audit trail** — dipakai untuk debug ("kenapa DXY kosong hari
ini?") dan ditampilkan langsung di dashboard sebagai indikator status per
sumber.

---

## 5. Ringkasan Siapa-Menulis-Apa

| Komponen | Baca DB? | Tulis DB? | Tabel yang disentuh |
|---|---|---|---|
| `pipeline/run_daily.py` | ya (`volume_ma20`) | **ya** | `daily_market`, `asset_ohlcv`, `daily_news`, `econ_calendar`, `positioning` (COT/ETF/IHSG flow), `earnings_calendar` |
| `pipeline/backfill*.py` | ya (cek duplikat) | **ya** | `asset_ohlcv`, `daily_market`, `fundamentals_quarterly`, `earnings_calendar` |
| `pipeline/run_analysis.py` | ya (histori) | **ya** | `sr_zones`, `trade_signals` |
| `pipeline/run_grader.py` | ya | **ya** | `emiten_grade`, `grader_log` |
| `web/app.py` + `web/writes.py` (dashboard) | ya | **ya** (Phase C+) | input manual: `reading_workspace`, `trading_journal`, `prediction_log`, `expectations`, `policy_tracker`, `intake_log`, `instrument_metadata`, `emiten_grade` (override), `lane_validation_log`, `fundamentals_quarterly` (rasio bank), dll |
| `indicators/calc.py` | ya (`volume_ma20_for_instrument`) | tidak | — |

Meski penulis kini lebih banyak, secara **praktik tetap single-writer**:
`run_daily`/backfill/analysis/grader dijalankan manual/cron berurutan (bukan
paralel), dan penulisan dashboard singkat & jarang bertabrakan. Kalau nanti
butuh writer paralel sungguhan (mis. multi-user setelah deploy), itu salah satu
trigger meninjau ulang SQLite → Postgres (lihat
[ARCHITECTURE.md §6.1](ARCHITECTURE.md#61-sqlite-vs-postgres-vs-nosql)).
