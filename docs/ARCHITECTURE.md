# Kastara Finance — Technical Architecture

> Status as of this document: **Phase A–F+ complete + Phase J+ (equity
> expansion) build-complete on the code side.** The dashboard now has **8
> write-enabled panels**, **22 tables**, an S&R/signals engine + Emiten
> Grader + sizing engine + 4 Persona Analyses. See [ROADMAP.md](ROADMAP.md)
> for the status of each phase & locked decisions, [FLOW.md](FLOW.md) for
> the data flow, [SOP.md](SOP.md) for the usage rhythm,
> [migrationFE.md](migrationFE.md) for the FE → Vue migration plan.
>
> This document explains the Phase A–C foundations in depth (the rationale
> in §6 still applies); step-by-step execution details for Phase D/E/F+/J+
> are in the ROADMAP.

---

## 1. System Overview

Kastara Finance is a **data layer + read-only dashboard** for monitoring
macro context (crypto, equities, FX, global liquidity) and financial news,
as a basis for manual analysis (and later semi-automated analysis in
Phase B+).

Core design principles (locked from the start, see [plan.txt](../plan.txt)):

- **Data layer first, logic later.** Phase A is purely about pulling &
  storing raw data. There is no trading/signal logic here.
- **Hands, not the brain.** Architectural decisions are locked in the
  planning doc; execution follows the spec — no major design improvisation
  without new instructions.
- **Fail resiliently, not silently.** Every failed data source has its
  status recorded (`source_flags`); the pipeline keeps running — it never
  crashes entirely because one API is down, and it never hides that
  failure.
- **Idempotent.** Running the pipeline or backfill multiple times for the
  same date = an update, not duplicate rows.
- **Free & lightweight.** All data sources are no-key or free-tier. No
  heavy dependencies (no ML/tensorflow), no heavy infrastructure (local
  SQLite, not Postgres/cloud) — see [§6](#6-design-decisions--rationale)
  for when this needs to be revisited.

---

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ (run on 3.14 via WSL) | Mature data/scraping ecosystem |
| Database | SQLite (`kastara-finance.db`), **DELETE** mode + `busy_timeout` | See [§6.1](#61-sqlite-vs-postgres-vs-nosql) |
| HTTP client | `requests` | Simple, sufficient for REST/JSON |
| Price data | `yfinance` | Free, no key, broad coverage (equities/FX/commodities) |
| Light transforms | `pandas` | Used only as needed (OHLC aggregation), not ML |
| RSS | `feedparser` | News feed parsing |
| Env/secrets | `python-dotenv` | Config via `.env`, no hardcoded keys |
| Web/API | `Flask` | Small, sufficient for the read-only Phase 1 dashboard |
| Test | `pytest` | Python's de-facto standard |

All in [requirements.txt](../requirements.txt). No heavy dependencies
(no ML framework) — in line with the constraint in `plan.txt`.

---

## 3. Folder Structure

```
kastara-finance/
├── .env / .env.example     # secrets & config (FRED/OpenRouter/Coinalyze key, etc.)
├── db/
│   ├── schema.sql           # DDL for 22 tables + indexes
│   └── connection.py        # get_connection(), init_db(), EXPECTED_TABLES,
│                              _migrate_columns() (ADD COLUMN for old DBs), WSL/Win path
├── scrapers/                # 1 file = 1 data source, each file runs independently
│   ├── base.py               # http_get retry, SourceFlags, safe_call, proxy, WIB
│   ├── crypto.py             # CoinGecko + Binance + Alternative.me
│   ├── coinalyze.py          # aggregate OI (3 exchanges) + liquidation L/S + LS ratio
│   ├── macro_fred.py         # FRED (DXY, US10Y, VIX, WALCL, RRP, TGA, HY)
│   ├── macro_yf.py           # yfinance (SP500, IHSG, Gold, USD/IDR, USD/JPY)
│   ├── news.py               # RSS + rule-based scoring (not AI)
│   ├── econ_calendar.py      # ForexFactory calendar (future events)
│   ├── investing_calendar.py # SECOND pass: fills in HIGH-only `actual` from investing.com
│   ├── positioning.py        # COT (CFTC) + BTC ETF flow (farside.co.uk)
│   ├── idx_foreign_flow.py   # IHSG market-level foreign flow (idx.co.id, curl_cffi)
│   ├── idx_stock_foreign_flow.py  # PER-STOCK foreign flow (J-8)
│   ├── idx_uma.py            # per-emiten UMA integrity flag (J-11)
│   └── equity_universe.py    # daily OHLCV for the stock universe (yfinance .JK/US, J-2)
├── pipeline/
│   ├── run_daily.py          # daily orchestrator, idempotent UPSERT
│   ├── run_investing_actual.py  # SECOND cron (afternoon/evening, SEPARATE from run_daily)
│   ├── backfill.py           # pull historical OHLCV, preview-before-commit
│   ├── backfill_fundamentals.py / backfill_earnings.py  # fundamentals & earnings (J-4/J-7)
│   ├── add_article.py        # CLI for manual_articles (historical research)
│   ├── run_analysis.py       # S&R + signal orchestrator (Phase B/F+/J-3)
│   ├── run_grader.py         # Emiten Grader orchestrator (J-11)
│   ├── seed_context_weight.py / seed_universe.py  # seed driver weights + universe
│   ├── compose_briefing.py / send_briefing.py     # Daily Briefing (Phase E)
│   └── compose_persona_context.py  # assemble context for the 4 Analyses (shared-core + slice)
├── indicators/calc.py        # net_liquidity, volume_ma20 (calculated fields, Phase A)
├── analysis/                  # PURE engine (does not read/write DB) — Phase B + J+
│   ├── indicators.py / sr_zones.py / signals.py  # MA, S&R zones, breakout/retest
│   ├── calibration.py          # zone tolerance per IDX price fraction (J-3, DRAFT)
│   ├── sizing.py               # 2.5% position sizing + 1.5x ARA/ARB buffer (J-3b)
│   └── grader.py               # Emiten Grader two-axis → quadrant (J-11)
├── llm/persona_analysis.py    # OpenRouter call for the 4 Persona Analyses (Panel 4)
├── notify/telegram.py         # one-way push send_message (Phase E)
├── tools/review_signal.py     # CLI to approve/reject trade_signals (by explicit id)
├── prompts/persona_*.txt      # system prompt for each persona (gitignored, Giel's IP)
├── web/                      # dashboard: read (Phase 1) + write (Phase C+/J+)
│   ├── app.py                 # Flask, 57 JSON endpoints + shell, 8 panel tabs
│   ├── writes.py               # pure DB-write functions (testable without Flask)
│   ├── templates/index.html + partials/panel1..8_*.html  # shell + 1 file per tab
│   └── static/css/dashboard.css + js/{core,panel1..8,main}.js
│                              # core = shared helpers + table engine; per-panel
│                              # JS separated; load order matters (global, not module)
│                              # → to be migrated to web/frontend/ (Vue, see migrationFE.md)
├── tests/                    # 1 test file per main module (287 tests)
└── docs/                     # this document + ROADMAP/FLOW/SOP/Master Plan/migrationFE
```

Modular rule: **every scraper must be runnable & testable on its own**
(`python -m scrapers.crypto`, etc.) — none depend on one another.

---

## 4. Database Schema

**22 tables total** (11 base tables from Phase A + 3 forward-layer tables
from Phase D + 7 equity tables from Phase J+ + 1 `lane_validation_log`).
The authoritative list is maintained in
`db/connection.py::EXPECTED_TABLES` (asserted by `tests/test_db.py`).
Unlike when this document was first written, most tables are now
**populated** (Phase B–J+ have been executed) — no longer structure-only.
§4.2 & §4.5 below summarize by group; per-table detail is in the
`db/schema.sql` comments.

### 4.1 Active tables (Phase A + B)

| Table | Grain | Contents |
|---|---|---|
| `daily_market` | 1 row / date | Global macro snapshot: BTC, DXY, S&P500, IHSG, VIX, Fear&Greed, net liquidity, etc. + `source_flags` (JSON status per API) |
| `asset_ohlcv` | 1 row / (date, instrument) | Universal OHLCV for all tradeable assets: BTC, SP500, IHSG, GOLD, USDIDR, USDJPY |
| `daily_news` | 1 row / unique headline | RSS headline + `impact_level` (HIGH/MED/LOW, rule-based) |
| `econ_calendar` | 1 row / unique event (`event_date`+`event_name`+`country`) | Future economic events (FOMC/CPI/etc.) from ForexFactory, UPSERT (forecasts can change as release nears) |
| `sr_zones` | 1 row / unique zone (relative bucket, per instrument+zone_type) | S&R zones detected by `analysis/sr_zones.py`, UPSERT from `pipeline/run_analysis.py`. `validated`/`notes` are manual — never overwritten by re-runs. |
| `trade_signals` | 1 row / signal event (append-only) | Breakout/retest results from `analysis/signals.py`. `approved` is always 0 from code — reviewed manually via `tools/review_signal.py`. |
| `asset_context_weight` | 1 row / (instrument, driver) | Driver weighting per asset (Master Plan §4.3). BTC seeded via `pipeline/seed_context_weight.py`. |
| `manual_articles` | 1 row / article | Manual historical research (RSS can't backfill) via `pipeline/add_article.py`. |

### 4.2 Phase C/D tables (now populated)

`reading_workspace`, `trading_journal`, `prediction_log` (Phase C, written
via `web/writes.py` from Panel 4/6/7) + `expectations`, `positioning`,
`policy_tracker` (Phase D forward-layer, Master Plan §4.2 —
`positioning` is filled automatically with COT+ETF+IHSG-flow on every
`run_daily`, the rest manually via Panel 3). When this document was first
written, all of these were still structure-only; they are now actively
used.

> **Deliberate FK deviation:** the Master Plan describes the `date`
> column in these tables as a *"FOREIGN KEY → daily_market."*
> `schema.sql` does not implement a real SQL `FOREIGN KEY` — the
> relationship is by-convention only (matching `date` values). This is
> consistent with `plan.txt` (the execution plan actually used), not an
> unintentional deviation.

### 4.3 Indexes

Added to keep queries fast as history grows (target: backfill up to
~5 years of daily data):

| Index | Columns | Serves |
|---|---|---|
| `idx_asset_ohlcv_instrument_date` | `(instrument, date)` | `WHERE instrument = ? ORDER BY date` — used by the chart, `volume_ma20`, backfill dedup-check |
| `idx_daily_news_dedup` (**UNIQUE**) | `(date, headline)` | Headline dedup **enforced at the DB level**, not just in app code |
| `idx_daily_news_impact_date` | `(impact_level, date DESC)` | Serves the dashboard's `/api/news?impact=HIGH` filter + `ORDER BY date` in one go (no temp sort) |
| `idx_econ_calendar_dedup` (**UNIQUE**) | `(event_date, event_name, country)` | Natural key for UPSERT — the same event gets refreshed (forecast changes as release nears), not duplicated |

`daily_market.date` is already `PRIMARY KEY` (automatic index). Phase B/D
tables have not been given indexes yet since there is no real query load
against them.

### 4.4 `source_flags` — an important contract

Every `daily_market` row has a `source_flags` column containing JSON:

```json
{"coingecko_ohlcv": "ok", "binance_ohlcv": "fail", "fred_dxy": "skip", "yf_SP500": "ok"}
```

Values: `"ok"` (success), `"fail"` (attempted, error), `"skip"`
(deliberately skipped, e.g. Binance disabled via env, or `FRED_API_KEY`
empty). This is the **audit trail** for every run — never delete or
summarize it; the dashboard and debugging depend on it.

### 4.5 Phase J+ equity tables (Build Contract v1.3)

7 equity tables + 1 lane-validation table, all for the individual-stock
universe (currently BBCA + TSLA):

| Table | Grain | Contents |
|---|---|---|
| `instrument_metadata` | 1 row / instrument | Stock metadata: `market`, `sector`, `lot_size`, `lane` (TRADE/INVEST/BOTH/NONE), `lane_validated_at`, `has_daily_limit` (ARA/ARB), `is_financial`. Determines the engine lane & calibration. |
| `fundamentals_quarterly` | 1 row / (instrument, quarter) | Revenue/net income/FCF (yfinance) + bank ratios CAR/NPL/NIM/LDR (manual, never overwritten). `confidence` FULL/LOW_CONFIDENCE. |
| `earnings_calendar` | 1 row / event | Earnings/corporate-action schedule — enforces the no-hold-through-earnings rule for US stocks. |
| `emiten_grade` | 1 row / grading | Grader result: `fund_score`, `integrity_flags` (JSON), `quadrant`, `giel_override` (JSON — the machine's original value is never overwritten). |
| `grader_log` | append-only | Audit of quadrant changes + 3/6-month widget outcome (anti-overtuning). |
| `intake_log` | append-only | Candidate intake decisions (universe/watchlist/reject) + mandatory reason. |
| `sector_benchmark` | 1 row / (sector, quarter) | Sector benchmark structure (J-5) — not yet populated (not yet worth it at 1 ticker/sector). |
| `lane_validation_log` | append-only | Trail of bar-replay lane validations — the **only** writer of `lane_validated_at`, only via `web/writes.py::validate_lane()`, `evidence` mandatory. |

Key principle of Phase J+: **same engine, different lane** — `lane`
determines whether `trade_signals` gets generated; new instruments must
go through manual bar-replay validation (§13.1) before their lane is
raised to TRADE. Zone calibration per IDX price fraction
(`analysis/calibration.py`) only applies to `market='IDX'`, DRAFT until
Giel confirms. The 1.5× ARA/ARB buffer (`analysis/sizing.py`) is already
locked (§18).

---

## 5. Modules & Responsibilities

### 5.1 `scrapers/base.py` — shared contract
- `http_get` / `http_get_json`: retry + backoff, supports proxy via
  `KASTARA_PROXY`.
- `SourceFlags`: status accumulator (`ok`/`fail`/`skip`) per source per
  run.
- `safe_call(name, fn, flags)`: wraps every API call — exceptions are
  caught, marked `fail`, **never propagated to the pipeline**.
- `today_wib()` / `now_wib()`: all times in WIB (UTC+7), dates stored as
  `YYYY-MM-DD`.

### 5.2 Scrapers (each returns a standard dict + `source_flags`)
- `crypto.py`: Binance is the primary source for BTC OHLCV (can be
  disabled/rerouted via `.env` — see
  [§6.2](#62-binance-region-block)); falls back automatically to
  CoinGecko if Binance fails/is disabled.
- `macro_yf.py`: 5 yfinance tickers, computes `change_pct` vs. the
  previous close.
- `macro_fred.py`: FRED API, each series is independent — one failing
  doesn't fail the others. Without `FRED_API_KEY` → everything is
  `skip`ped (not an error).
- `news.py`: RSS feeds (can go down/move at any time, marked `fail` not
  a crash) + rule-based scoring (keyword, word-boundary match — not an
  LLM).
- `econ_calendar.py`: ForexFactory (unofficial JSON endpoint, free
  no-key — see
  [§6.5](#65-economic-calendar--unofficial-source)). Future events,
  UPSERT by `(event_date, event_name, country)` since forecasts can
  change as the release nears.

### 5.3 `pipeline/run_daily.py` — orchestrator
Calls every scraper → merges results → computes calculated fields
(`net_liquidity`, `volume_ma20`) → UPSERT into `daily_market` +
`asset_ohlcv` → `INSERT OR IGNORE` into `daily_news` (dedup via unique
index) → UPSERT `econ_calendar` (natural key, refresh forecast) → prints
ok/fail/skip summary. **Idempotent**: safe to run repeatedly for the
same date. Scheduled via **per-user crontab** (`0 0 * * *`) — see
[README §5](../README.md#5-automation-cron).

### 5.4 `pipeline/backfill.py` — historical fetch
CLI with a **mandatory preview before commit**: computes new vs.
duplicate rows, displays them, asks for `[y/N]` confirmation (or
`--yes` for non-interactive use). Duplicates (`date`+`instrument`
already present) are skipped, not errored.

### 5.5 `indicators/calc.py`
Pure functions (`net_liquidity`, `volume_ma20_from_values`) + one
function that queries the DB (`volume_ma20_for_instrument`) to compute
the 20-day average volume from `asset_ohlcv` history.

### 5.6 `web/app.py` + `web/writes.py` — dashboard (Phase 1 read-only + Phase C write)

Phase 1 endpoints (`/api/latest`, `/api/daily_market`, `/api/asset_ohlcv`,
`/api/news`, `/api/assets`, `/api/health`) **remain read-only, unchanged**
since Phase C work began. New Phase C endpoints **write**, but do NOT
write new logic directly in the route — everything reuses existing,
already-tested functions:
- Backfill (`/api/backfill/all/preview`, `/api/backfill/all/commit`) →
  calls `pipeline.backfill.backfill()` per instrument that has a gap
  (see §6.8 on `preview_only`). The old per-instrument endpoints
  (`/api/data_gaps`, `/api/backfill/preview`, `/api/backfill/commit`)
  were removed 28 Jul 2026 — redundant with "Check & Preview All Gaps,"
  which already checks all instruments at once.
- Manual article (`/api/articles/add`) →
  `pipeline.add_article.insert_article()`.
- Approve/reject signal (`/api/signals/review`) →
  `tools.review_signal.set_review()`.
- Reading workspace, trading journal, prediction log, policy tracker,
  key-trigger flag → new functions in `web/writes.py` (pure, testable
  without Flask — `tests/test_web_writes.py`; there are no direct
  Flask-route tests, endpoints are verified manually via the preview
  browser instead).

Navigation across **8 tabs** (a single page, JS `display:none/block`,
not a reload): Snapshot → News → Forward → Reading → Chart → Synthesis
(the morning TRADE-lane flow, Master Plan §0) + **History** (archive) +
**Universe & Grader** (Phase J+, weekly/quarterly INVEST-lane rhythm).
Panel 4 "4 Analyses" calls OpenRouter via `llm/persona_analysis.py` with
context from `pipeline/compose_persona_context.py` (shared-core + per-
persona slice) — the single AI/LLM touchpoint in the system, triggered
by a manual button. `web/app.py` now has **57 endpoints** (33 GET + 24
POST); the `/` route just renders the static shell (no server-side
data) — a clean data boundary, the foundation for the FE → Vue
migration ([migrationFE.md](migrationFE.md)).

**No authentication** (a conscious decision, `plan_c.txt` §6.4) —
local-only, `WEB_HOST=127.0.0.1` by default. Login/auth is planned
alongside the FE migration (Phase 3 of migrationFE.md) & Track A
deployment — not present yet.

**Chart Panel 5 (added after early Phase C):** candlestick + MA50/100/200
overlay + volume bar/MA20 + 4 context mini-charts (DXY/S&P500/US10Y/
Fear&Greed) — an item that had been deferred in `plan_c.txt` decision
#2, done later. All MAs are computed **client-side in JS**
(`rollingMA()`, the JS version of `analysis/indicators.py::rolling_ma`),
not a new endpoint — the chart fetches `/api/asset_ohlcv` with a
`limit` larger than what's displayed (120 visible + 220 historical
padding) so MA200 is valid from the LEFTMOST visible candle onward, not
just from the 200th point on. Context mini-charts use
`/api/daily_market` (already existing, no new endpoint), independent of
the selected instrument.

### 5.7 `analysis/` — Phase B engine (PURE, does not read/write DB)

Separated from `indicators/calc.py` (Phase A) because of different
concerns and different usage patterns — see the full rationale in
`plan_b.txt` §2. All modules are generic per-instrument (no BTC
hardcoding); instrument filtering happens in the orchestrator
(`pipeline/run_analysis.py`), not here.

- `indicators.py`: `moving_average`/`rolling_ma` (MA — different from
  `indicators/calc.py`; here a full window is REQUIRED, None if data is
  insufficient), `ma_stack_order`, `volume_ratio`, `is_breakout_volume`
  (>1.5x MA), `is_volume_present` (>=80%, the "not thin" threshold
  during a retest).
- `sr_zones.py`: `find_swing_points` (symmetric ±20-day lookback — a
  new point is only confirmed 20 days AFTER it forms, suited to a
  morning review rather than real-time), `cluster_points` (merges swing
  points within ±0.5%, compared against the cluster's LOWEST price so
  it doesn't "creep"), `find_touches` (counts touch episodes, not
  per-day), `detect_zones` (the full pipeline), `zone_bucket_key`
  (log-scale natural key for stable UPSERT even when zone boundaries
  shift slightly between runs).
- `signals.py`: `detect_signals` — breakout (close > resistance +
  volume) → retest (close > zone_lower + volume present) →
  entry/SL/TP1/R:R. A low-R:R signal is STILL returned (`is_valid=0`),
  not silently dropped. It never includes `approved` in its output at
  all (a stricter design than just "always 0" — that field only exists
  at the point of writing to the DB).

### 5.8 `pipeline/run_analysis.py` — Phase B orchestrator
Reads `asset_ohlcv` history → `analysis/sr_zones.py` → UPSERT
`sr_zones` (preserving `validated`/`notes`) → reloads active zones →
`analysis/signals.py` → INSERT into `trade_signals` (manual dedup by
date+instrument+signal_type+zone bounds, no UNIQUE index — see §6.6).
`approved` is **hardcoded to 0** at exactly this `INSERT` point — the
only place automated code writes to `trade_signals`.

**Important finding during execution:** the `volume_ma20` column in
`asset_ohlcv` turned out to only be populated for days processed by
`run_daily.py` — rows produced by `backfill.py` (the majority of
historical data) were all NULL. The orchestrator re-derives
`volume_ma20` from the full volume history via `rolling_ma()`, rather
than relying on the stored column.

### 5.9 `tools/review_signal.py` — approve/reject CLI
Same pattern as `pipeline/add_article.py`. `approve`/`reject`
**require an explicit `--id`** — there is no approve-all mode (Master
Plan §3: Giel does the approving, not the machine). `reject` only sets
`notes` (approved stays 0) — the difference from "not yet reviewed"
(approved=0, notes=NULL) is that notes is filled in.

---

## 6. Design Decisions & Rationale

### 6.1 SQLite vs Postgres vs NoSQL

**Decision: stick with SQLite**, including for the ~5-year daily-data
backfill target.

- The data is tabular/relational (OHLCV, dated snapshots) — a good fit
  for relational storage; NoSQL (document DB) adds no benefit and makes
  indicator queries (joins, aggregation) harder.
- Realistic volume: `asset_ohlcv` ≈ tens of thousands of rows for 5
  years × several instruments; `daily_news` (the largest) ≈ hundreds of
  thousands of rows. SQLite is comfortable up to millions of rows.
- Concurrency is handled with **DELETE mode** (SQLite's default,
  deliberately chosen) + `busy_timeout=5000` — automatic retry for up
  to 5 seconds on a brief lock, instead of an immediate `SQLITE_BUSY`.
  **WAL** mode was tried for the same purpose, but WAL needs shared
  memory (`-shm`), which is **not reliable across the Windows↔WSL
  boundary** — a real case: DBeaver on Windows accessing the file via
  `\\wsl.localhost\...` (effectively a network share/9P from Windows'
  side) while the pipeline runs natively in WSL; WAL just produced the
  same `SQLITE_BUSY`, in a different shape. DELETE + `busy_timeout` is
  more predictable for this kind of mixed access pattern. Our writes
  (pipeline, dashboard) are short (<1 second), so the exclusive-lock
  trade-off at commit time is small.
- **Trigger for moving to Postgres** (not now): if the dashboard needs
  to be accessed by many concurrent users, or needs many simultaneous
  writer processes, or needs managed cloud hosting. This is about
  concurrency/deployment, not historical data volume.

### 6.2 Binance region-block

Binance is often DNS-level blocked in some networks/regions. Solution:
automatic fallback to CoinGecko for OHLC if Binance fails, and every
Binance endpoint is configurable via `.env`:
`BINANCE_BASE`, `BINANCE_FAPI_BASE`, `BINANCE_ENABLED`, `KASTARA_PROXY`.
Funding rate & open interest (Binance-futures-specific) will be empty
if Binance is unreachable — this is a **known condition**, not a bug.

### 6.3 WSL/Windows path resolution

The app runs inside WSL, but the user sometimes fills `KASTARA_DB_PATH`
with a Windows UNC path (`\\wsl.localhost\<distro>\...`) — e.g. copied
from a SQL client on the Windows side. `db/connection.py` translates
this path into the native Linux path pointing to the same file, so it
doesn't create a duplicate/stray file due to a different path
representation.

**The DB is deliberately kept outside the project folder**
(`kastara-finance-data/`, a sibling of `kastara-finance/`), configured
via `KASTARA_DB_PATH` in `.env`. Reason: the DB changes every day
(pipeline/cron), the code doesn't — separating the two avoids data
files accidentally getting tracked/committed to git (on top of the
`.gitignore` protection that already exists). All path resolution
(`get_db_path()` / `_resolve_db_path()`) remains the single source of
truth for the DB location — no DB path is hardcoded in any other
module (scrapers, pipeline, web).

### 6.4 Rule-based, not AI/LLM

News impact scoring (`news.py`) and all of Phase A's logic are purely
rule-based (keyword matching). This isn't a technical limitation — it's
a decision locked in `plan.txt` to keep the system transparent and
predictable at the data layer; external AI/LLM (if used) lives in the
*reading workspace* layer (Phase C), not the data layer.

### 6.5 Economic Calendar — unofficial source

Master Plan §10 names ForexFactory/Trading Economics as economic
calendar sources. **Trading Economics is deliberately not used** — its
official API requires a paid key for full country coverage (the guest
key only gives a few sample countries), which violates the "NO paid
APIs" rule.

ForexFactory itself has no official API; `econ_calendar.py` uses the
unofficial JSON endpoint (`nfs.faireconomy.media`) used by the
ForexFactory calendar widget — free, no key, but **undocumented** and
can change/get rate-limited at any time (observed during testing: HTTP
429 after several calls in quick succession). Handled the same way as
the RSS feeds: `safe_call` + `source_flags`, failure → `fail`, the
pipeline still continues. For a daily run (1x/day via cron) this
rate-limit risk is low — the 429s observed were purely an artifact of
repeated manual testing.

Other limitations of this source: it only gives a rolling "this week"
window (no history or upcoming week), and doesn't provide an `actual`
(release result) column — that column stays `NULL` from this scraper.

### 6.6 `trade_signals` — dedup without a UNIQUE index

Unlike `daily_news`/`econ_calendar` (UNIQUE index, `INSERT OR IGNORE`),
`trade_signals` **deliberately has no UNIQUE index** (locked in
`plan_b.txt` §5) — an exact-match breakout/retest event on the same
date naturally recurs rarely, so the benefit of a UNIQUE index is small
compared to the complexity of defining the right natural key for this
kind of append-only data. Dedup is checked manually in
`pipeline/run_analysis.py::insert_signal_dedup()` — a SELECT first by
`(date, instrument, signal_type, zone_lower, zone_upper)` before
INSERT. `trade_signals` volume is far smaller than `daily_news`
(hundreds per instrument vs. hundreds of thousands), so one extra
SELECT per signal isn't a performance concern.

### 6.7 `sr_zones` — UPSERT without a stored bucket-key column

The natural key for `sr_zones` UPSERT (`zone_bucket_key()` in
`analysis/sr_zones.py`) is **recomputed in Python every time**, rather
than stored as a DB column. Reason: the `sr_zones` schema has been
locked since Phase A (`zone_lower`, `zone_upper`, no extra columns) and
adding a new column would mean changing an already-locked schema — this
is avoided as long as the migration-free alternative (recompute at
lookup time, a small cost since the number of zones per instrument is
still in the hundreds) is good enough. If the number of zones per
instrument grows dramatically later (many instruments, Phase F+), this
is the first candidate for optimization (e.g. a stored generated column
+ index).

### 6.8 `pipeline.backfill.backfill()` — `preview_only` (Phase C extension)

The backfill CLI (Phase A) uses `input()` to confirm a commit — this
would **hang** if called from a web request (no stdin). Rather than
duplicating the fetch+dedup-check logic in `web/app.py` (violating the
reuse principle), `backfill()` was given a new parameter
`preview_only: bool = False`: it returns right after the preview is
computed, BEFORE either the `input()` prompt or the commit. Default is
`False` — the CLI and all existing tests are completely unchanged;
Dashboard Panel 1 calls it with `preview_only=True` (for the Preview
button), then `assume_yes=True` (for the Confirm & Commit button, 2
separate requests, re-fetching data — accepted as a trade-off since
each fetch is cheap, see §6.1).

### 6.9 Bug found during browser verification: `/api/news` didn't SELECT `id`

The `/api/news` endpoint (Phase 1, read-only) had never needed the `id`
column before. When Panel 2 added a "flag key trigger" button (which
needs `id` to know which row to update), the button silently didn't
appear at all — `r.id` was always `undefined` in JS. It was found
precisely because verification was done DIRECTLY in the browser (not
just pytest, which wouldn't have caught this since there was no test
for the old JSON endpoint's response shape). Fixed by adding `id` to
the `SELECT`. A lesson reinforcing the `plan_c.txt` §5 principle:
"verified via the preview browser, not just pytest."

### 6.10 `hy_credit_spread` — a real-world example of "a FRED series can be provider-restricted"

`scrapers/macro_fred.py` had already warned since Phase A: *"FRED
series ids sometimes change/get deprecated... don't assume."* Here's
the concrete case: `hy_credit_spread` (`BAMLH0A0HYM2`) only has 787
rows in the DB (vs. ~4,100 for `dxy_close`/`vix_close`) — initially
suspected to be a backfill gap, but it turned out **not to be**.
Checked directly against FRED metadata (`/fred/series`): the data owner
(ICE Data Indices) restricts this series to a **rolling 3 years** due
to its license with FRED (*"Starting in April 2026, this series will
only include 3 years of observations"*) — longer history is only
available directly from ICE Data (paid), outside the "no paid API"
scope. Confirmed via a `backfill.py` re-run: 0 new rows (the DB already
has everything FRED provides). No further action needed — this is a
data-source limit, not a bug.

### 6.11 `scrapers/positioning.py` — Cloudflare needs browser-realistic headers

Phase D research (`plan_d.txt`) had concluded that farside.co.uk (BTC
ETF flow) "can be scraped," based on one successful `curl` test (200,
full HTML table). Once implemented using `requests` (the library the
scraper actually uses) with `scrapers/base.py::DEFAULT_HEADERS`'s
default (an honest bot UA `kastara-finance/0.1` +
`Accept: application/json`), the response instead came back as a
Cloudflare **"Just a moment..."** page (a bot challenge), not the
table. `curl` passed because its header/TLS fingerprint happened to
resemble a browser's; `requests` with generic headers did not.

Fix: send browser-realistic headers SPECIFICALLY for this request (a
Chrome UA + `Accept: text/html...` + `Accept-Language`), overriding
`DEFAULT_HEADERS` via the `headers=` parameter in `http_get()` — not
changing `DEFAULT_HEADERS` globally (that's used by other JSON scrapers
that specifically need an honest `Accept: application/json`). Lesson:
if scraping feasibility research is only tested via manual `curl`, the
result isn't necessarily representative of the request actually sent
by the Python HTTP library — re-validate using the exact same code
that will run in production, not a different-fingerprint proxy tool.

CFTC COT, in contrast: tested directly using the Socrata API
(`publicreporting.cftc.gov/resource/<id>.json`), free, WITHOUT an API
key — confirmed to work exactly as the initial research suggested, no
surprises.

### 6.12 Telegram Daily Briefing — manual PUSH, deliberately NOT attached to `run_daily`

Master Plan §5/§8 (Phase E) describes "push daily briefing" as if it
were an automatic daily process like the other scrapers. But the
briefing's content (4 Lenses, approved Signal) is only complete AFTER
Giel finishes Panels 4-6 (~07:20) — `run_daily` runs at 07:00, well
before that. If `compose_daily_briefing()` were called automatically
at the end of `run_daily`, its most important sections (lenses &
signals) would ALWAYS be empty, since `pull data` and `Giel's manual
analysis` are two events separated in time.

Decision: `pipeline/send_briefing.py` is a SEPARATE action (CLI +
Panel 6 button), triggered by Giel himself whenever ready — not an
automatic step in `pipeline/run_daily.py`. This is consistent with the
"the machine assembles, Giel predicts" principle:
`compose_daily_briefing()` just assembles text from rows that ALREADY
exist in the DB (written manually by Giel in Panels 4-6), never
waiting/polling for data that doesn't exist yet.

**A deliberately different testing pattern from other scrapers:** all
scrapers (`scrapers/*.py`) are tested with LIVE network calls (see
`test_econ_calendar.py`, `test_positioning.py`) because that's a READ
operation — safe to repeat many times. `notify/telegram.py` is a SEND
operation (pushing a message to a real chat) — if its tests were also
live, every `pytest` run would actually send a message to Giel's
Telegram. So `tests/test_notify_telegram.py` is mocked using
`monkeypatch` (the first time this test suite has used mocking) — the
one deliberate exception to the "test scrapers against a real network"
habit.

### 6.13 Bug found during initial setup: `notify/telegram.py` didn't call `load_dotenv()` itself

Every module that reads env vars (`scrapers/macro_fred.py` via
`FRED_API_KEY`, etc.) had "for free" gotten `.env` loaded because every
entry point (`run_daily`, `backfill`, `web.app`) imports `db.connection`
first, and `db/connection.py` is the one that calls `load_dotenv()`.
`notify/telegram.py` was also designed to be runnable STANDALONE
(`python -m notify.telegram` — the official way to get the `chat_id`
the first time, see README), but this module doesn't import
`db.connection` at all -> `.env` never got loaded,
`os.getenv("TELEGRAM_BOT_TOKEN")` was always empty even though it was
set in `.env`.

Found when Giel actually set up the real token (not in tests — the
tests pass `token=`/`chat_id=` explicitly so they weren't affected).
Fix: `notify/telegram.py` now calls `load_dotenv()` itself at module
level, without depending on some other module being imported first.

**A second bug (not code, but configuration)**: the `TELEGRAM_CHAT_ID`
value Giel had entered was off by 1 digit from the real chat_id
(`...443` vs. the correct `...442`) — only discovered after
`get_latest_chat_id()` was called AFTER Giel actually sent a message to
the bot (a valid chat_id can only be obtained from a real update, not
guessed/copied from elsewhere). Telegram's error message
`"Bad Request: chat not found"` turned out to be the right diagnostic
signal for this case — confirmed to match.

### 6.14 `scrapers/investing_calendar.py` — why it is NOT merged into `run_daily`

Initial research (filling `econ_calendar.actual` for HIGH-importance
events from investing.com, a source ForexFactory genuinely doesn't
have) had briefly been concluded as "skip" — a direct test
(`curl_cffi impersonate=chrome`, same pattern as
`idx_foreign_flow.py`) hit an HTTP 429 that didn't recover after ~5-6
research requests within a few minutes, and the AJAX endpoint for date
navigation ("Yesterday") couldn't be found (the URL parameter was
ignored, SSR always returned investing.com's "today" version).

What was realized later: that problem was purely about the RESEARCH
PATTERN (a fast burst of requests), not PRODUCTION use (1x/day).
Because investing.com's default view is already sufficient IF scraped
in the AFTERNOON/EVENING (not morning) — HIGH events for that day
typically already have their actual released by then — date navigation
turns out not to be needed at all. The solution:
`pipeline/run_investing_actual.py` is a SEPARATE entrypoint with its
own cron (evening, not merged into the morning 00:00 `run_daily`). This
too is a conscious DECISION, not an oversight: "merge all scrapers into
1 extra GET per `run_daily`" initially looked simpler, but would mean
other block-prone scrapers (`idx_foreign_flow.py`,
`idx_stock_foreign_flow.py`) would also get hit with 2x requests/day
for no benefit — see the discussion in `docs/ROADMAP.md`.

**Bug found during first live verification**: matching investing.com ->
`econ_calendar` uses fuzzy event-name matching
(`difflib.SequenceMatcher`,
`pipeline/run_investing_actual.py::_normalize_name`) because the two
sources use different terms for the same event (ForexFactory "CPI m/m"
vs. investing.com "CPI (MoM) (Jun)"). The first normalization stripped
ALL text in parentheses (including the "(MoM)"/"(YoY)" marker), so
"CPI (MoM)" and "CPI (YoY)" both became "cpi" -> identical score ->
`_best_match` deliberately skips when ambiguous (better empty than
mismatched) -> first run: 3 events fetched, 0 matches, 3 skipped. Fix:
normalize `m/m`/`(MoM)` into the token `mom` (and likewise yoy/qoq)
BEFORE stripping parentheses, then remove the rest (month/quarter
names). After the fix, a second run against the real DB: 3/3 correct
matches (CPI m/m, Core CPI m/m, CPI y/y — MoM/YoY not swapped). The
same lesson as §6.11: verify using the code that ACTUALLY runs in
production, not just a unit test with self-made data (the initial unit
test passed because its candidates were deliberately not made
ambiguous).
