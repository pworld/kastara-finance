# Kastara Finance — Data Flow

> Companion to [ARCHITECTURE.md](ARCHITECTURE.md) (what & why) — this document
> focuses on **how data moves** through the system. Diagrams use Mermaid
> (renders automatically on GitHub/VS Code; if your viewer doesn't support it,
> read the text version in each section).

---

## 1. Daily Flow (`pipeline/run_daily.py`)

Run via **per-user crontab** `0 0 * * *` (system TZ is already WIB, see
README §5), or manually at any time.

> Note: the diagram below depicts the core of Phase A (5 macro scrapers). Since
> Phase D/J+ `run_daily` also calls `positioning.py` (COT+ETF), `coinalyze.py`
> (OI/liquidation), `idx_foreign_flow.py` + `idx_stock_foreign_flow.py` (IHSG &
> per-stock), and `equity_universe.py` (stock OHLCV) — identical pattern (`safe_call`
> → `source_flags` → merge), just adding branches, not changing the flow.

```mermaid
flowchart TD
    A[python -m pipeline.run_daily] --> B[init_db - ensure 22 tables exist]
    B --> C{Call macro+equity scrapers}
    C --> C1[crypto.py + coinalyze.py]
    C --> C2[macro_yf.py + equity_universe.py]
    C --> C3[macro_fred.py: FRED 7 series]
    C --> C4[news.py: RSS feeds]
    C --> C5[econ_calendar.py + positioning.py + idx_*_flow.py]

    C1 --> D[Each scraper: safe_call per sub-request]
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    D --> D1{Success?}
    D1 -->|yes| D2[flags.ok - continue]
    D1 -->|failed| D3[flags.fail or skip - print warning, continue]

    D2 --> E[Merge all source_flags into 1 dict]
    D3 --> E

    E --> F[Build asset_ohlcv rows: BTC + 5 from yfinance]
    F --> G[UPSERT asset_ohlcv by date+instrument]
    G --> H[Compute volume_ma20 per instrument from history]
    H --> I[UPDATE asset_ohlcv SET volume_ma20]

    E --> J[Build daily_market: merge crypto+yf+fred]
    J --> K[Compute net_liquidity = walcl - rrp - tga]
    K --> L[UPSERT daily_market by date, including source_flags JSON]

    E --> M[INSERT OR IGNORE daily_news]
    M --> N[Dedup enforced by UNIQUE INDEX date+headline]

    E --> P1[UPSERT econ_calendar by event_date+event_name+country]
    P1 --> P2[Natural key enforced by UNIQUE INDEX - forecast is refreshed]

    I --> O[Print summary: N ok / N fail / N skip]
    L --> O
    N --> O
    P2 --> O
```

**Key points:**
- Stage C (calling scrapers) **never crashes** — each scraper catches
  internal errors via `safe_call`, so one dead API doesn't stop the
  others.
- The G→H order is intentional: `asset_ohlcv` is written first, then
  `volume_ma20` is computed from history (including today's row) and
  written back via `UPDATE`.
- Idempotent: running it twice for the same date → `UPSERT`/`INSERT OR IGNORE`
  produce the same end result (not duplicate rows). Already verified by tests.

---

## 1b. Evening/Night Flow (`pipeline/run_investing_actual.py`)

The SECOND cron, **separate** from the flow above (different schedule, not yet in
crontab — see README §5). Purpose: fill in `econ_calendar.actual` for HIGH-importance
events whose forecast/previous were already populated by the morning flow
(ForexFactory never provides `actual`, see
[ARCHITECTURE.md §6.14](ARCHITECTURE.md#614-scrapersinvesting_calendarpy--why-it-is-not-merged-into-run_daily)
for why this isn't simply added to `run_daily`).

```mermaid
flowchart TD
    A[python -m pipeline.run_investing_actual] --> B[investing_calendar.py: 1x GET default page]
    B --> C{HTTP ok?}
    C -->|failed/rate-limit| C1[source_flags fail, empty items, done]
    C -->|ok| D[Parse: ONLY 3-star HIGH importance, actual already filled]
    D --> E{For each scraped event}
    E --> F[Find econ_calendar candidates: HIGH + actual NULL + same country + event_date +-1 day]
    F --> G[Fuzzy-match event name - difflib, threshold 0.5]
    G --> H{Unique & confident match?}
    H -->|no/ambiguous| H1[Skip - actual stays empty]
    H -->|yes| I[UPDATE econ_calendar.actual via set_econ_actual]
    I --> J[Print summary: fetched/matched/skipped]
    H1 --> J
    C1 --> J
```

**Key points:**
- DELIBERATELY conservative: ambiguous candidates (2+ equally high scores) are skipped,
  not guessed — better for `actual` to stay empty (fillable manually via
  the dashboard) than to attach it to the wrong event.
- Event-name normalization aligns terms between the 2 sources ("m/m" ForexFactory
  vs "(MoM)" investing.com become the same `mom` token) BEFORE stripping
  parentheses — if parentheses were stripped first, the MoM/YoY marker would be
  lost too and different events would look the same (found during live
  verification, see ARCHITECTURE.md §6.14).
- Never crashes, same `safe_call`/`source_flags` pattern as other scrapers.

---

## 2. Backfill Flow (`pipeline/backfill.py`)

Used manually to fill in history (e.g. 5 years back), bit by bit,
per instrument/range.

```mermaid
flowchart TD
    A["python -m pipeline.backfill --instrument X --from --to"] --> B{Map instrument to source}
    B -->|BTC| C1[Binance klines range]
    B -->|SP500/IHSG/GOLD/USDIDR/USDJPY| C2[yfinance history range]
    B -->|DXY/US10Y/VIX/WALCL/RRP/TGA/HY| C3[FRED observations range]

    C1 --> D{Binance failed?}
    D -->|yes| E[Fallback yfinance BTC-USD]
    D -->|no| F[rows]
    E --> F
    C2 --> F
    C3 --> F

    F --> G[Check dates that ALREADY EXIST in DB for this instrument]
    G --> H[Compute: N new rows vs N duplicates]
    H --> I["PREVIEW printed to terminal"]
    I --> J{User confirms y/N OR --yes}
    J -->|N / no| K[Cancelled - NOTHING written]
    J -->|y / --yes| L[UPSERT into asset_ohlcv OR daily_market]
    L --> M[Print: N new rows written, N duplicates skipped]
```

**Key points:**
- **Preview always shown before commit** — there's no path that writes
  without showing the preview first (except `--yes` for automation/testing, which still
  displays the preview, only skipping the prompt).
- Duplicates (`date`+`instrument` already exists) **are skipped, not errored** — safe
  to run repeatedly for overlapping ranges.
- Well suited to a "pull a little at a time" pattern: run per instrument, per
  range of a few months, repeatedly until 5 years are covered — no need to
  pull everything at once in one go.

---

## 3. Dashboard Flow (`web/app.py`, read **+ write** since Phase C)

```mermaid
flowchart LR
    Browser -->|GET /| Flask[Flask app]
    Flask -->|render static shell| HTML[templates/index.html + 8 partial]
    HTML -->|fetch JS| GET[33 endpoint GET /api/*]
    HTML -->|postJSON| POST[24 endpoint POST /api/*]

    GET --> DB[(kastara-finance.db\nmode DELETE + busy_timeout)]
    POST -->|web/writes.py + reuse pipeline| DB

    Pipeline[pipeline/run_daily.py + backfill.py + run_analysis + run_grader] --> DB
```

**Key points:**
- Since Phase C the dashboard **reads AND writes**: manual input (journal,
  predictions, policy, intake, grade override, lane validation, etc.) via 24 POST
  endpoints. Writing still doesn't put new logic in the route — it reuses
  `web/writes.py` (pure, testable) + already-tested pipeline functions.
- The `/` route only renders a **static shell with no server-side data** — all content
  is fetched client-side from `/api/*` (a clean data boundary → the foundation for the
  FE migration to Vue, [migrationFE.md](migrationFE.md)).
- Still **single-writer in practice**: dashboard writes are brief & rarely
  concurrent with `run_daily`. **DELETE** mode + `busy_timeout=5000` (not
  WAL — [ARCHITECTURE.md §6.1](ARCHITECTURE.md#61-sqlite-vs-postgres-vs-nosql))
  keeps Windows↔WSL cross-access predictable.
- `/api/latest` parses the `source_flags` JSON into a render-ready structure
  (ok/fail/skip indicator dots in the UI).

---

## 4. Lifecycle of `source_flags`

```mermaid
sequenceDiagram
    participant S as Scraper (e.g. macro_fred.py)
    participant F as SourceFlags
    participant P as run_daily.py
    participant DB as daily_market.source_flags

    S->>F: safe_call("fred_dxy", fetch_fn, flags)
    alt success
        F->>F: flags.ok("fred_dxy")
    else caught exception
        F->>F: flags.fail("fred_dxy")
    else deliberately skipped (e.g. no API key)
        F->>F: flags.skip("fred_dxy")
    end

    S-->>P: return dict + source_flags per scraper
    P->>P: merge all source_flags (all scrapers into 1 dict)
    P->>DB: store as JSON in the source_flags column
    Note over DB: {"fred_dxy":"ok","binance_ohlcv":"fail","rss_Kontan":"skip",...}
```

This dict is an **audit trail** — used for debugging ("why is DXY empty
today?") and displayed directly on the dashboard as a per-source status indicator.

---

## 5. Summary of Who-Writes-What

| Component | Reads DB? | Writes DB? | Tables touched |
|---|---|---|---|
| `pipeline/run_daily.py` | yes (`volume_ma20`) | **yes** | `daily_market`, `asset_ohlcv`, `daily_news`, `econ_calendar`, `positioning` (COT/ETF/IHSG flow), `earnings_calendar` |
| `pipeline/run_investing_actual.py` (evening/night, separate) | yes (finds match candidates) | **yes** | `econ_calendar.actual` only (existing HIGH events, no new row insertion) |
| `pipeline/backfill*.py` | yes (checks duplicates) | **yes** | `asset_ohlcv`, `daily_market`, `fundamentals_quarterly`, `earnings_calendar` |
| `pipeline/run_analysis.py` | yes (history) | **yes** | `sr_zones`, `trade_signals` |
| `pipeline/run_grader.py` | yes | **yes** | `emiten_grade`, `grader_log` |
| `web/app.py` + `web/writes.py` (dashboard) | yes | **yes** (Phase C+) | manual input: `reading_workspace`, `trading_journal`, `prediction_log`, `expectations`, `policy_tracker`, `intake_log`, `instrument_metadata`, `emiten_grade` (override), `lane_validation_log`, `fundamentals_quarterly` (bank ratios), etc. |
| `indicators/calc.py` | yes (`volume_ma20_for_instrument`) | no | — |

Even though there are now more writers, in **practice it's still single-writer**:
`run_daily`/backfill/analysis/grader are run manually/via cron sequentially (not
in parallel), and dashboard writes are brief & rarely collide. If a real
parallel writer is needed later (e.g. multi-user after deployment), that's one
trigger to revisit SQLite → Postgres (see
[ARCHITECTURE.md §6.1](ARCHITECTURE.md#61-sqlite-vs-postgres-vs-nosql)).
