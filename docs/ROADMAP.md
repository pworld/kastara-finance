# Kastara Finance — Roadmap

> Reference source: **[Master Plan.md](Master%20Plan.md)** (v1.5, full strategy
> document) → derived into **[plan.txt](../plan.txt)** (Phase A execution
> scope that was actually worked on) + additional decisions made during
> execution sessions (Phase 1, dashboard). This document is a living
> document — update the status here every time a new phase is finished or
> whenever a new gap is found against the Master Plan.

## Status Summary

| Phase | Name | Status |
|---|---|---|
| **A** | Database & Scraper (data layer) | ✅ **Fully complete** — matches `plan.txt` **and** Master Plan §10 checklist (see [status](#anchor-gap-phase-a)); the cron daemon needs 1 manual sudo step, see note |
| **1** | Read-only dashboard (Flask) | ✅ Complete — became the foundation for Panels 1/2/5 in Phase C |
| **B** | S&R detection, breakout/retest engine | ✅ **Complete for BTC** — `plan_b.txt` (deleted after completion) fully executed, 46 new tests, verified with real data |
| **C** | Full Dashboard/UI (6 panels, write-enabled) | ✅ **Complete** — `plan_c.txt` (deleted after completion) fully executed, all panels verified via browser |
| **D** | Forward layer (FedWatch, COT, policy) | ✅ **Complete** — `plan_d.txt` (deleted after completion) fully executed, COT+ETF flow automated, Expectations/SBN manual, Dissonance flag working |
| **E** | Telegram bot | ✅ **Complete (one-way push)** — `plan_e.txt` (deleted after completion) fully executed, manual Daily Briefing (CLI + Panel 6 button); two-way bot commands deferred to backlog |
| **F+** | Multi-asset expansion | 🟡 **GOLD/SP500/IHSG/USDIDR/USDJPY active** (S&R+signals+context weight) — other altcoins/stocks/commodities not yet |
| **J+** | Equity expansion (individual stocks IDX→US) | 🔶 **Build Contract v1.3 LOCKED (11 Jul 2026) + Addendum A Tab 8 (12 Jul 2026, FULLY COMPLETE 13 Jul 2026), Gates G1/G2/G3 ANSWERED (13 Jul 2026)** — universe = **BBCA + TSLA**; **J-2/J-3(groundwork)/J-3b/J-4/J-6/J-7/J-8/J-10/J-11/J-12/J-13/J-14/J-15 COMPLETE**; remaining: **J-5** (deferred, not yet worth it with 1 ticker/sector), **J-9** (persona prompt v5, needs Giel's own writing), + manual bar-replay validation & §13 calibration (Giel's decision, not automatic) |

---

<a id="anchor-gap-tersisa"></a>
## 📍 Remaining Gaps (13 Jul 2026) — quick summary, NO need to scroll down

All build/code from the contract is complete. What remains only needs
Giel's own action/decision, not further development:

1. **Track A — Deploy infra** (auth, Docker/Railway, two-way Telegram bot) —
   deliberately deferred ("save for release time"), not started at all.
2. **Bar-replay validation** — the mechanism ALREADY EXISTS (Panel 8
   "Validation Lane", see the §"Update — Lane validation mechanism" section
   under Phase J+ below), but not a single instrument has been validated
   yet. BBCA & TSLA are still `lane=INVEST`, not yet `TRADE`.
3. **Final §13 calibration** — `IDX_ZONE_TOLERANCE_TICKS = 2` in
   `analysis/calibration.py` is still DRAFT, waiting for Giel to confirm/
   revise after seeing real bar-replay (see the §"Update — J-3: ARA/ARB..."
   section below).
4. **J-9 persona prompt** — draft text already exists at
   [`docs/j9_equity_slice_prompt_draft.md`](j9_equity_slice_prompt_draft.md),
   not yet merged into `prompts/persona_rivan.txt`/`persona_akela.txt`
   (needs to be in Giel's own voice, not my final version).
5. **J-5 — sector benchmark** — deferred, not worth the effort yet with
   only 1 ticker per sector in the current universe.

Full detail for each item is in the "🔶 Phase J+" section below (search for
the latest "**Update —**" heading per topic) — the points above are just a
summary so you don't need to scroll through the full history.

---

<a id="anchor-cross-check"></a>
## 🔍 Cross-check vs Master Plan v1.4

Written after `Master Plan.md` (the full strategy document) was added to
`docs/` — previously execution only referenced `plan.txt` (a narrower
derived scope for Phase A). Results of the re-read:

### ✅ Consistent
- 11 main tables (Master Plan Section 4) — matches `schema.sql` exactly.
- Tech stack (Section 5): SQLite dev → Postgres if scale/multi-device
  requires it, Flask, custom chart (not TradingView) — all match.
- Core principles: `source_flags`, rule-based scoring (not AI), no
  execution/trading logic, no AGPL code — all consistent.
- Manual backfill tool (Section 4.1: preview → confirm → commit) — matches
  `pipeline/backfill.py` exactly.

<a id="anchor-gap-phase-a"></a>
### ✅ Phase A gap checklist (Master Plan §10) — now closed

`plan.txt` (which was executed first) deliberately narrowed the Phase A
scope. Master Plan §10 defines Phase A more broadly; the following three
items were gaps for a while, now addressed:

1. **Economic Calendar scraper** ✅ — `scrapers/econ_calendar.py`, source
   ForexFactory (unofficial JSON endpoint, free, no key required;
   **Trading Economics is deliberately not used** because its official API
   requires a paid key for full coverage — that would violate the "no paid
   API" rule). UPSERT by `(event_date, event_name, country)` into
   `econ_calendar`, integrated into `pipeline/run_daily.py`. This endpoint
   is unofficial/undocumented — it may change/rate-limit at any time;
   already fail-safe (`source_flags`, doesn't crash the pipeline). The
   `actual` column stays NULL from this scraper (the source doesn't provide
   release-result data).
2. **3 forward-layer tables** ✅ — `expectations`, `positioning`,
   `policy_tracker` (Section 4.2) have already been added to `schema.sql`
   (structure only, per Master Plan §10). They'll be populated once Phase D
   really starts.
3. **Automatic 00:00 WIB cron job** 🟡 — the per-user crontab has been
   **installed and verified to run correctly** (simulated exactly matching
   the cron environment: `env -i` + `/bin/sh`, exit 0, log written to
   `logs/run.log`). What's still **missing**: the cron **daemon** itself
   needs `sudo service cron start` (requires an interactive password —
   outside the control of automated execution, must be run manually once by
   Giel). See full instructions in
   [README §5](../README.md#5-automation-cron).

Total tables now **14** (11 Phase A + 3 forward-layer), up from 11.

### Small intentional deviations (not bugs)

The Master Plan writes the `date` column in `daily_news` (and other
tables) as *"FOREIGN KEY → daily_market"*. The `schema.sql` implementation
does **not** write this as an actual SQL `FOREIGN KEY` — it's only a
by-convention relation (a matching `date` column). This is consistent with
`plan.txt` (which indeed doesn't define a literal FK), so it's left as is —
noted here to make clear this is a conscious choice, not something missed.

---

## ✅ Phase A — Database & Scraper (fully complete)

**Complete per `plan.txt` scope AND the Master Plan §10 checklist**: SQLite
+ 14 tables (11 Phase A + 3 forward-layer structure), 5 modular scrapers
(crypto, macro FRED, macro yfinance, news, economic calendar), an
idempotent daily pipeline, a backfill tool with preview-before-commit, cron
installed (the daemon needs 1 manual step — see the [gap](#anchor-gap-phase-a)
above).

**Deliverables:**
- `db/schema.sql` — 14 tables + indexes sized for a 5-year scale.
- `scrapers/{crypto,macro_fred,macro_yf,news,econ_calendar}.py` — each
  source independent, resilient to API failure (`source_flags`).
- `pipeline/run_daily.py` — orchestrator, idempotent UPSERT, including the
  economic calendar.
- `pipeline/backfill.py` — historical fetch, preview mandatory before
  commit.
- `indicators/calc.py` — `net_liquidity`, `volume_ma20`.
- Per-user crontab installed (`0 0 * * *`, system TZ already Asia/Jakarta =
  WIB, no conversion needed).
- 29 tests, all green.

**Definition of Done** — all criteria in `plan.txt §8` **and** the Master
Plan §10 checklist are met.

---

## ✅ Phase 1 — Read-Only Dashboard (complete, became the foundation for Phase C)

Not in the original `plan.txt` (which placed the dashboard in Phase C), but
worked on earlier at direct request because it was needed immediately for
visual verification of data that had already come in. It later became the
foundation for Panels 1/2/5 when Phase C was fully built.

**Deliverables:**
- `web/app.py` — Flask, read-only JSON endpoints (`/api/latest`,
  `/api/daily_market`, `/api/asset_ohlcv`, `/api/news`, `/api/assets`,
  `/api/health`). Does not write to the DB — the pipeline remains the sole
  writer (still true for these endpoints; Phase C adds NEW write-enabled
  endpoints, these old endpoints are NOT changed).
- `web/templates/index.html` — single-page UI (snapshot cards,
  `source_flags` status, SVG price chart per instrument, news table with
  impact filter).
- Verified end-to-end via preview: all endpoints 200, chart renders from
  backfilled data, HIGH/MED/LOW filter works.

<a id="anchor-panel-breakdown"></a>
### History: Phase 1 vs Phase C (6 panels) — historical breakdown

This note was written when Phase 1 had just finished and Phase C had not
been worked on at all (breakdown per panel from Master Plan §6). **No
longer accurate** — see [Phase C's current status](#anchor-phase-c-status)
for what actually exists now. Kept here as history, not an active status:

| Panel (Master Plan §6) | Status AT THAT TIME (Phase 1 just finished) |
|---|---|
| Panel 1 — Data Snapshot | 🟡 Partial: cards + `source_flags` exist; Manual Backfill button doesn't exist |
| Panel 2 — News Briefing | 🟡 Partial: list + impact badge exist; manual "key trigger" flag button & "+ Add Manual Article" button don't exist |
| Panel 3 — Forward Panel | ⬜ Doesn't exist (needs the Phase D tables first: `expectations`/`positioning`/`policy_tracker`) |
| Panel 4 — Reading Workspace | ⬜ Doesn't exist (needs the 4-lens input form) |
| Panel 5 — Chart + Technical Analysis | 🟡 Partial: plain price chart exists; MA overlay, S&R zone overlay, approve/reject signal don't exist (needs Phase B) |
| Panel 6 — Synthesis | ⬜ Doesn't exist (needs `prediction_log` capture + prediction scoring) |

---

## ✅ Phase B — S&R Detection & Breakout/Retest Engine (complete, BTC)

**Execution plan: `plan_b.txt` (deleted after completion)** — the 7 Open
Questions in §7 were reviewed & locked in by Giel, executed exactly per
that.

**Deliverables:**
- `analysis/indicators.py` — `moving_average`, `rolling_ma` (full rolling
  MA, used to re-derive `volume_ma20` because that column in `asset_ohlcv`
  is only ever populated for days processed by `run_daily.py` — rows from
  historical backfill are all NULL, discovered during execution),
  `ma_stack_order`, `volume_ratio`, `is_breakout_volume`,
  `is_volume_present`.
- `analysis/sr_zones.py` — swing high/low (symmetric lookback §7.1),
  ±0.5% clustering, touch-count per episode (not per-day), zone_type by
  majority-vote approach direction, zones with <2 touches are still stored
  with `is_active=0` (§7.3). `zone_bucket_key()` — a log-scale natural key
  for stable UPSERT (§7.4).
- `analysis/signals.py` — breakout (close > resistance + volume >1.5x MA)
  → retest (close > zone_lower + volume >=80%, §7.2) → entry/SL/TP1/R:R.
  A breakout without a retest is stored as a separate row (§7.5), R:R < 1.5
  is still stored with `is_valid=0` (not silently dropped).
- `pipeline/run_analysis.py` — orchestrator, BTC-only filter (§4, generic
  in `analysis/*`), zone UPSERT (preserving human-entered
  `validated`/`notes` on re-run), deduplicated signal INSERT, `approved`
  **hardcoded 0** at the single write point.
- `tools/review_signal.py` — CLI approve/reject **by explicit id**, no
  approve-all mode (Master Plan §3: Giel approves, not the machine).
- `pipeline/seed_context_weight.py` — BTC seed (`net_liquidity`/`etf_flow`
  =HIGH, `fear_greed`/`dxy`=MED, exactly per Master Plan §4.3).
- 46 new tests (80 total), all green. Also verified with REAL BTC data
  (4,313 rows, 2014-2026): 119 zones (117 active), 455 signals — **0 of
  them `approved=1`** (a regression guard, not just in synthetic tests).
- Cron: **not** scheduled automatically (§7.6) — run manually, in line with
  the decision that production cron will move to a server, local is dev
  only.

**Not yet included** (per `plan_b.txt` §9 scope boundary): dashboard
approve button (Phase C), instruments other than BTC (Phase F+), forward
layer (Phase D).

---

<a id="anchor-phase-c-status"></a>
## ✅ Phase C — Full Dashboard/UI (complete)

**Execution plan: `plan_c.txt` (deleted after completion)** — the 5 Open
Questions in §6 were reviewed & locked in by Giel, executed exactly per
that. The dashboard is now **write-enabled** (for the first time, previously
100% read-only in Phase 1) — 6-tab navigation following the morning flow in
Master Plan §0/§6.

**Deliverables per panel:**
- **Panel 1** (Data Snapshot): + Manual Backfill form, preview-then-confirm
  (reuses `pipeline.backfill.backfill(preview_only=True)`, a small
  backward-compatible extension — the CLI is unchanged).
- **Panel 2** (News Briefing): + key-trigger flag button
  (`daily_news.is_key_trigger`), + "Add Manual Article" form (reuses
  `pipeline.add_article.insert_article()`). *Bug found & fixed during
  verification: the `/api/news` endpoint never SELECTed the `id` column
  (not needed in the Phase 1 read-only version) — the flag button needs it,
  now added.*
- **Panel 3** (Forward Panel): Economic Calendar shows REAL data (76+
  events from Phase A) with a day countdown; Policy Tracker manual form +
  list (independent of Phase D, per decision #1); Expectations/Positioning/
  Dissonance show an explicit **empty state** (not an error) — waiting on
  Phase D.
- **Panel 4** (Reading Workspace): 4 lenses GEMA/LEON/AKELA/RIVAN + External
  AI Check (manual paste, NOT an AI call) + Conflict Notes. Only saves
  fields that are filled in (skips empty ones) to `reading_workspace`
  (`lens` ∈ {GEMA,LEON,AKELA,RIVAN,EXTERNAL_AI,CONFLICT,SYNTHESIS}).
- **Panel 5** (Chart + TA): upgraded from the Phase 1 line chart to a
  **candlestick OHLCV + S&R zone overlay + breakout/retest markers +
  Approve/Reject** (reuses `tools.review_signal.set_review()`, `approved`
  remains manual). MA50/100/200 overlay + volume bar/MA20 + 4 context
  mini-charts (DXY/S&P 500/US10Y/Fear&Greed) were briefly deferred
  (decision #2), **later completed anyway** — see [Small Backlog](#anchor-backlog).
- **Panel 6** (Synthesis): synthesis textarea (→ `reading_workspace`
  lens=SYNTHESIS) + outlook dropdown for **5 instruments** (BTC/SP500/
  IHSG/GOLD/USDIDR, USDJPY excluded — decision #5) + Trading Journal form +
  Prediction Log + prediction score widget (BENAR/SALAH/PARTIAL = CORRECT/
  WRONG/PARTIAL).

**Verification:** not just pytest (92 tests, all green) — each panel was
tried DIRECTLY via browser preview (fill form → submit → check it saved in
DB via direct query → test data cleaned up again). Approve/reject signal,
key-trigger flag, both Panel 3/4/6 forms, all confirmed to write correctly
to the right table.

**Not yet included** (per `plan_c.txt` boundary, not missed): automated
scraper for Expectations/Positioning/Policy Tracker (Phase D), Telegram bot
(Phase E), multi-instrument analysis engine (Phase F+), authentication
(not needed yet — local-only). The Panel 5 MA/volume/context-chart backlog
item **has also now been completed** (see [Small Backlog](#anchor-backlog)).

---

## ✅ Phase D — Forward Layer

**Complete** — `plan_d.txt` (deleted after completion) fully executed.
Scope (Master Plan §4.2, 3 stages): Policy Tracker (Stage 3/Layer A) was
already done earlier in Phase C (independent of the Phase D ordering).
Remaining scope:

- **Source research before execution** (checked directly, not assumed):
  - CME FedWatch: NO free API (official one starts at $25/month) →
    **manual**.
  - Fed Dot Plot/SEP: released as a quarterly PDF → **manual** (per the
    original plan).
  - COT report: CFTC Socrata API is **free, no API key** (confirmed via
    a live query) → **automated**.
  - BTC ETF flow: farside.co.uk has no official API, and the site sits
    behind Cloudflare — `requests` with default headers (`Accept:
    application/json`, bot UA) hits a challenge page, browser-realistic
    headers (Chrome UA + `Accept: text/html` + `Accept-Language`) get
    through → **automated** (HTML scrape, same risk profile as
    ForexFactory/RSS: if the site changes, `source_flags` fails and
    continues, doesn't crash).
  - SBN foreign flow: djppr.kemenkeu.go.id isn't reliably scrapable (a
    plain fetch doesn't get meaningful content, indicating an SPA) →
    **manual**.
- **`scrapers/positioning.py`**: `fetch_cot_positioning()` (BTC/DXY/GOLD/
  SP500, metric `cot_net_long` = noncommercial long−short from the CFTC
  Legacy Futures Only report) + `fetch_btc_etf_flow()` (last 10 days from
  farside.co.uk, metric `etf_net_flow`). Integrated into `run_daily`
  (called every day; COT only adds a row when there's actually a new
  weekly release — idempotent).
- **`positioning` UPSERT**: `idx_positioning_dedup` UNIQUE(date,
  instrument, metric) added to the schema;
  `pipeline/run_daily.py::upsert_positioning()`.
- **Generic manual entry** (`web/writes.py::insert_positioning_manual`):
  one form used both for SBN foreign flow (free-text metric) AND for
  manual correction of scraped rows (e.g. ETF flow) — `ON CONFLICT DO
  UPDATE` by natural key, per decision #2 in `plan_d.txt`.
- **Expectations** (`insert_expectation`/`list_expectations`): manual form
  for CME FedWatch cut probability & Dot Plot median.
- **Dissonance Flag** (`compute_disonansi`): a simple v1 rule (NOT AI) —
  compares the sign of the latest `stance_score` (Policy Tracker) vs the
  14-day trend of `cot_net_long` for DXY; if they diverge → flagged.
  Returns `{"available": false}` if there isn't enough data yet (needs ≥1
  stance_score AND ≥2 DXY COT rows within the window) — an explicit empty
  state, not an error.
- **Dashboard Panel 3**: the 3 old empty states (Expectations/Positioning/
  Dissonance) replaced with real tables+forms.
- **New tests**: `tests/test_positioning.py` (scraper, live network + unit
  parse helper) + 6 new tests in `tests/test_web_writes.py` — 108 tests
  total.
- **Not yet automated** (noted, not missed): SBN foreign flow (source not
  scrapable), CME FedWatch/Dot Plot (no free API) — all by design, not a
  technical gap.

---

## ✅ Phase E — Telegram Bot

**Complete (one-way push)** — `plan_e.txt` (deleted after completion)
fully executed.

- **Why MANUAL PUSH, not auto from `run_daily`**: the briefing content (4
  Lenses, approved Signal) is only complete AFTER Giel finishes Panels 4-6
  (~07:20) — `run_daily` runs at 07:00, well before that. Auto-push tied
  to `run_daily` would always be empty in the most important part. Full
  detail: [ARCHITECTURE.md §6.12](ARCHITECTURE.md#612-telegram-daily-briefing--manual-push-deliberately-not-attached-to-run_daily).
- **`notify/telegram.py`**: `send_message()` (push via Bot API
  `sendMessage`, using plain `requests` — NO heavy new dependency) +
  `get_latest_chat_id()` (one-time setup helper via `getUpdates`).
- **`pipeline/compose_briefing.py`**: assembles the briefing text EXACTLY
  per the Master Plan §8 format (Market Snapshot, Key Events, 4 Lenses,
  Signal, mandatory disclaimer) — a pure function, purely reads data that
  Giel has ALREADY filled in manually, doesn't generate anything.
- **`pipeline/send_briefing.py`**: CLI (`--dry-run`/`--date`) + "Send to
  Telegram" button on the dashboard's Panel 6 (`POST /api/briefing/send`).
- **Empty sections** (e.g. a lens not yet filled in) show `(belum diisi)`
  ("not filled in yet") — not hidden, so Giel notices something was
  missed. Key Events is dropped entirely if there really is no news
  flagged as a key trigger that day (a different case — not "Giel must
  fill this in").
- **More than 1 approved signal** on the same day -> all are shown, 1 line
  per signal (not just the latest one).
- **Tests**: `tests/test_compose_briefing.py` (pure function, no network) +
  `tests/test_notify_telegram.py` (mocked with `monkeypatch` — the ONLY
  scraper/notify module whose tests are not live-network, because this is
  a SEND operation, not READ — see ARCHITECTURE.md §6.12).
- **Deferred to backlog** (needs an always-on host, not a gap): two-way
  bot commands (`/snapshot`, `/news` on-demand) — needs a long-polling
  process that's always running, a local laptop isn't always on.
  Consistent with the DB & scheduler decision "local first, VPS later".
- **Manual setup that can't be automated**: Giel needs to create a bot via
  `@BotFather` + get his own `chat_id` (see README §Telegram Setup) — same
  pattern as `FRED_API_KEY`.

---

## 🟡 Phase F+ — Multi-Asset Expansion

**GOLD/SP500/IHSG/USDIDR/USDJPY successfully activated** (Master Plan §10,
Phases F/G/H/I merged into 1 pass — `analysis/*.py` has been generic since
Phase B, so this is purely "turn it on for other instruments," not
building new features). USDJPY was originally excluded (decision #5 in
plan_c.txt, specific to the Panel 6 outlook dropdown) but since its data
has been complete since Phase A, Giel asked for it to be included in this
analysis engine too.

What previously only ran for BTC now runs for all six instruments:
- **`pipeline/run_analysis.py`**: `INSTRUMENTS = ["BTC","GOLD","IHSG","SP500",
  "USDIDR","USDJPY"]` — `python -m pipeline.run_analysis` (no flag)
  processes ALL at once; `--instrument X` can still run just one.
  `sr_zones`/`trade_signals` are now populated for all six instruments
  (GOLD 74 zones/433 signals, IHSG 73/251, SP500 90/123, USDIDR 65/0,
  USDJPY 64/0 — USDIDR & USDJPY have no valid breakout/retest in their
  history yet, not a bug).
- **`pipeline/seed_context_weight.py`**: `GOLD_WEIGHTS`/`SP500_WEIGHTS`/
  `IHSG_WEIGHTS`/`FOREX_WEIGHTS` (USDIDR)/`USDJPY_WEIGHTS` added, exactly
  matching the driver examples in Master Plan §4.3 (e.g. GOLD:
  real_yield/dxy/geopolitics; USDJPY: BOJ-vs-Fed rate differential/Japan-
  US trade balance). `main()` seeds all six instruments at once.
- **Dashboard Panel 5**: did NOT need changes — the instrument dropdown &
  `/api/asset_ohlcv`, `/api/sr_zones`, `/api/signals` have been generic
  since Phase C, chart+zones+signals display as soon as data exists.
  Verified in browser: GOLD/IHSG/SP500/USDIDR/USDJPY all render the
  relevant chart+zones+signal table correctly.
- **New tests**: `test_seed_context_weight.py` adds 1 test for the 5 new
  instruments. 121 tests green total.
- **Note**: Panel 6 "Outlook per Instrument" (`OUTLOOK_INSTRUMENTS` in
  `web/app.py`) STILL has 5 instruments without USDJPY — that's decision
  #5 from `plan_c.txt`, separate from this analysis engine, not yet asked
  to be changed.

**Not yet done** (outside the scope of "make sure these 4 instruments
work"): other altcoins, individual stocks, additional commodities,
revisiting SQLite if volume/concurrency changes significantly (see
[ARCHITECTURE.md §6.1](ARCHITECTURE.md#61-sqlite-vs-postgres-vs-nosql)).

---

<a id="anchor-backlog"></a>
## Small Backlog (not tied to one phase, can be done any time)

Concrete items that were identified during Phase A/1 but not yet done —
recorded here so they don't get lost, not a schedule commitment:

- [x] ~~Automatic cron for `run_daily`~~ — crontab installed & verified
      (see the [gap checklist](#anchor-gap-phase-a)). **Remaining:** run
      `sudo service cron start` once (needs an interactive password, can't
      be run automatically) + optionally `[boot] command=service cron
      start` in `/etc/wsl.conf` so cron starts automatically every time the
      WSL instance starts.
- [x] ~~Economic Calendar scraper~~ — `scrapers/econ_calendar.py` done,
      integrated into `run_daily`, 6 tests green.
- [x] ~~3 forward-layer tables~~ — `expectations`/`positioning`/
      `policy_tracker` already in `schema.sql`.
- [x] ~~Full 5-year backfill~~ — **done** for all instruments (`BTC`
      2014-2026, `SP500`/`IHSG`/`GOLD`/`USDIDR`/`USDJPY` 2010-2026, 4,000+
      rows each) + all FRED series (see the `hy_credit_spread` item below
      for why one series is shorter — **not a gap**, `walcl`/`tga` being
      low is also NORMAL, weekly publication series not daily).
- [x] ~~Panel 5 chart MA/volume/context~~ — MA50/100/200 overlay, volume
      bar+MA20, 4 context mini-charts (DXY/S&P500/US10Y/Fear&Greed) done,
      verified via browser (120 points across each MA line, no NaN).
- [x] ~~Panel 5 chart: date/month markers + range filter~~ — the chart's
      bottom axis now shows month/year labels (auto ticks at month
      changes, thinned to max 9 labels so they don't crowd during long
      ranges), plus 5 range filter buttons (1M/3M/6M/1Y/All) above the
      chart that change how many candles are fetched & shown
      (`CHART_VISIBLE`, default 90 days). "All" pulls up to 5,000 rows
      (cap in `/api/asset_ohlcv`, raised from 1,000) — enough for the full
      BTC history (~4,300 rows since 2014). Verified in browser: each
      filter button correctly changes the date range & number of candles
      (1M → 30 days/2 labels, All → 2014-2026/9 labels).
- [x] ~~Panel 5 chart: price (Y) axis + fix scale stretched by far zones~~ —
      added gridlines + price labels on the right of the chart so
      open/close numbers can be read directly. Found a bug while adding
      this: `sr_zones` was pulling in ALL active zones across the whole
      history (including the ~$200 BTC era), so the Y scale used to be
      stretched 199 → 124,457 and real candles looked flattened at the
      bottom of the chart. Fix: only zones overlapping ±50% of the
      currently visible price range are used for scaling & drawn
      (`relevantZones`); the "N/117 active zones" label shows how many of
      the total are relevant to the current price. Verified: 3M → 29/117
      relevant zones & axis 42,874-98,286 (makes sense), All → 117/117
      (full history span, correct).
- [x] ~~Investigate `hy_credit_spread`~~ — **NOT our bug/gap.** Checked
      directly against FRED (`/fred/series` metadata for `BAMLH0A0HYM2`):
      *"Starting in April 2026, this series will only include 3 years of
      observations. For more data, go to the source."* ICE Data (the
      owner of this data) deliberately limits this series to a rolling
      3-year window due to licensing with FRED, not a limitation of our
      scraper/backfill. Confirmed: our DB already has 787 of the 793 total
      observations FRED provides (re-run backfill: 0 new rows = coverage
      already complete). Longer history for this series **isn't available
      for free** — only directly through ICE Data (paid), outside the
      "no paid API" scope.
- [x] ~~Panel 3 Economic Calendar: show forecast/previous + fill in actual~~
      — `forecast`/`previous` had actually been scraped since the start
      but never displayed; now they appear as columns in the table.
      `actual` is **never** provided by ForexFactory (checked directly
      against the raw JSON endpoint — that field doesn't exist at all in
      the response), so it's filled in **manually** via the dashboard:
      inline input + a "Save" button per row (`POST
      /api/econ_calendar/actual`, `web/writes.py::set_econ_actual`),
      turning into an "Edit" button once filled. The `/api/econ_calendar`
      query was also expanded from "today + upcoming" to "D-7 through
      upcoming" so events that just released yesterday still show up to
      have their actual filled in. 2 new tests (`test_web_writes.py`),
      verified live in the browser + direct DB query.
- [x] ~~Forward panel: sort Economic Calendar by date + importance
      filter~~ — previously old events sat at the top of the table, now
      it's sorted (upcoming/today first, past events pushed down) + a
      dropdown filter defaulting to **HIGH only (3 stars)**, with a "HIGH
      + MED" option to see everything. Purely client-side
      (`ForwardView.vue`), no API change.
- [x] ~~Issuer earnings shown in the Forward panel (J-15 wave 2, contract
      §19.5)~~ — `earnings_calendar` (J-7 data existed for a long time,
      BUT was never surfaced: no endpoint, not in the UI) now shows in
      `ForwardView.vue`'s "Issuer Earnings" section, alongside the
      Economic Calendar ("visually combined" = separate section, not two
      schemas forced into one table). READ-ONLY (eps_actual is filled by
      the scraper, not manually). Columns: countdown, EPS forecast/actual,
      surprise (beat green/miss red). **Open-position earnings WARNING**
      (contract §18 decision #3): `trading_journal.outcome='ONGOING'`
      JOIN `earnings_calendar` upcoming → a red "must fully close" badge
      for US stocks (`hard_rule`, enforcing the no-hold-through-earnings
      rule), an informational badge for IDX (no full-close rule there, gap
      risk still exists). 2 new read helpers
      (`list_earnings_calendar`/`list_earnings_warnings`,
      `web/writes.py`) + 2 endpoints (`GET /api/earnings`,
      `/api/earnings/warnings`). 5 new tests (`test_web_writes.py`),
      verified direct-Python against the real DB (2026-07-22 earnings
      showed up at D-7) + a warning scenario against a temp DB (TSLA/US
      hard, BBCA/IDX soft, past/far positions skipped).
- [x] ~~News Threads N-1 foundation (Addendum B §20, Giel's addendum)~~ — a
      gap in Addendum B that had PREVIOUSLY not been built at all
      (different from Addendum A/Universe Panel, which was already done in
      J-14/J-15). **N-1 only** (foundation) — N-2 (Reading strip, digest
      injection into `compose_persona_context.py`, auto-DORMANT)
      DELIBERATELY not built yet, the contract itself splits it into 2
      waves and N-2 needs N-1 to be used for a few days first as test
      material.
      **Schema**: 3 new tables (`news_threads`, `news_thread_links`,
      `thread_relations` schema-only for N-2) + 1 UNIQUE dedup index —
      22→25 tables total.
      **Backend**: `scrapers/news.py::_matches` promoted to
      `scrapers/base.py::keyword_matches()` (reusing the rule-based
      matcher, not rewriting it, now used in 2 places). `web/writes.py` —
      `save_thread` (mandatory-title guard + **max 7 ACTIVE threads**,
      enforced in the write function not just the UI, decision #5),
      `patch_thread` (mandatory-verdict guard when status=CLOSED),
      `suggest_thread_links` (rule-based auto-suggest, ONLY scans ACTIVE
      threads, ALWAYS just SUGGESTED — never auto-CONFIRMED, human gate
      §20.0), `confirm_thread_link` (stance is MANDATORY — anti-
      confirmation-funnel decision #3 — `also_key_trigger` reuses the
      existing `flag_key_trigger()`), `reject_thread_link`,
      `add_thread_link_manual` (guards for known ref_table + dedup),
      `list_thread_links` (union of 3 manual sources: daily_news/
      manual_articles/policy_tracker), `attach_thread_suggestions`
      (CONFIRMED wins over SUGGESTED if one news item matches >1 thread).
      `pipeline/run_daily.py`: hooks `suggest_thread_links` AFTER
      `insert_news_dedup` (needs the actual row id), count included in
      `summary`. 7 new `/api/threads*` endpoints (mutations via POST, not
      PATCH — consistent with this app's convention of never using
      PATCH/PUT elsewhere) + `/api/news` extended to attach `thread_link`
      per row.
      **Frontend**: `NewsView.vue` — a "Suggestion: `<thread>`?" chip +
      Confirm (a Dialog to pick a stance, checkbox "also flag as key
      trigger") / Reject per row; `ThreadIndexView.vue` (new, `<DataTable>`
      + form to create a thread) + `ThreadDetailView.vue` (new, vertical
      timeline of CONFIRMED links + edit current_read/status/verdict +
      manual linking) — **the first route in this app with a dynamic
      `:id`, `/threads/:id`**. Sidebar nav "Threads" added to the Daily
      group (§20.6: confirming SUGGESTED = a morning ritual) — without
      this the new pages wouldn't be reachable through normal UI in N-1.
      19 new tests (`test_web_writes.py`, guards for 7-ACTIVE/mandatory-
      verdict/mandatory-stance/known-ref_table/dedup, auto-suggest
      idempotency, `also_key_trigger` genuinely reusing
      `flag_key_trigger`). 336 tests green total. **Verified live**:
      `init_db()` run against the real DB (new tables needed a migration —
      initially got a 500 "no such table" before this was realized), a
      full Flask test-client round-trip (create→list→detail→patch→3 guard
      400s), AND `suggest_thread_links` against REAL PRODUCTION headlines
      today — the keyword "hawkish" successfully matched a headline about
      the central bank turning more hawkish, Manulife IM recommending
      active investment management, with status SUGGESTED (not auto-
      CONFIRMED, the human gate proven to work). The verification thread
      was CLOSED again afterward (not left ACTIVE in the real DB).
      `npm run build` succeeded (349 modules, including
      `ThreadIndexView`/`ThreadDetailView` — proof the new SFC transform
      doesn't error; a console-check alone isn't enough because the
      lazy-loaded route behind the auth guard is never imported unless
      you're logged in).
- [x] ~~Faceted Tagging C-1 foundation (Addendum C §21, Giel's addendum)~~ —
      **C-1 only** (foundation), C-2 (manual feed into persona, tag-based
      thread matching) DELIBERATELY not built yet — the contract itself
      LOCKS this in (§21.9 decision #7: "build C-1+C-2 at once" explicitly
      appears on the "NOT to do" list, unlike News Threads which was only
      recommended against).
      **5 things in 1 package**: (a) a controlled-vocabulary tag facet
      dictionary (geo/org/who/sym/theme/sec, starting EMPTY), (b) a
      command-palette tagging UI, (c) `display_subtitle` (Giel's note, the
      original headline is NEVER overwritten), (d) a functional rename of
      `is_key_trigger` → `for_reading` (tag = objective classification,
      for_reading = subjective curation — two different questions that
      used to be crammed into 1 flag).
      **Schema**: 2 new tables (`tag_dictionary`, `content_tags` — 25→27
      tables) + 2 new columns on `daily_news` (`display_subtitle`,
      `for_reading`) via `_COLUMN_MIGRATIONS` (DIFFERENT from the News
      Threads new tables — `daily_news` already has live data, so it goes
      through the column-migration path, not `CREATE TABLE` — same
      pattern as `asset_context_weight.level`), including a one-time
      backfill `for_reading = is_key_trigger` (idempotent, doesn't re-run
      every `init_db()`).
      **Full rename, not an alias**: `flag_key_trigger()` →
      `set_for_reading()`, `/api/news/flag_key` → `/api/news/for_reading`,
      `confirm_thread_link`'s `also_key_trigger` → `also_for_reading` —
      swept across ~8 files (writes.py, app.py, 2 pipeline files, 2 Vue
      views, 3 test files) via a thorough grep, the OLD `is_key_trigger`
      is left frozen in the schema (don't DROP it, the DB is live) but is
      no longer read or written.
      **New backend**: `create_tag` (grammar validation — facet:value,
      lowercase-hyphen, `sym:` requires a region prefix — the FIRST regex
      in writes.py, but following the same raise-ValueError idiom as every
      other function), `list_tags`/`resolve_tag` (alias), `apply_tag`
      (guards that the tag must already exist in the dictionary + dedup +
      bumps usage_count), `remove_tag`,
      `list_content_tags`/`attach_content_tags` (batch, mirrors
      `attach_thread_suggestions`). 6 new `/api/tags*`+`/api/content_
      tags*` endpoints + `/api/news/<id>/display_subtitle`, all mutations
      via POST (not PATCH — consistent with this app's convention).
      **Frontend**: a new `TagAutocomplete.vue` (wraps PrimeVue's
      `AutoComplete`, already available zero-dep in v4.5.5 — grouped
      dropdown by facet + built-in chip+remove-X, confirmed via `npm run
      build` actually generating a `TagAutocomplete-*.js` chunk, not just
      assumed from package.json) used in 3 places: the per-row Tag column
      in `NewsView.vue`, the filter-chip bar (AND/OR toggle) in News, and
      the tag filter in `ReadingView.vue`. `NewsView.vue` also gets inline
      editing of `display_subtitle` (the endpoint was briefly unreachable
      from any UI before this was added — noticed during self-review) + a
      collapsible "Browse All Tags" (same pattern as `source_flags` in
      SnapshotView, using `DataTable.vue` as-is).
      **Bug found during implementation**: `attach_content_tags()`
      initially did NOT include `content_tags.id` per tag (only
      canonical+facet) — the UI would have had no way to call
      `remove_tag()` at all without it. Caught before it became a
      production problem (while wiring up NewsView, not via a bug report)
      — fixed + the related test updated.
      35 new tests (4 grammar-guard cases, create/apply dedup, alias
      resolve, batch attach, migration backfill). 354 tests green total.
      **Verified live**: `init_db()` against the real DB (1,973 real
      `daily_news` rows — 100% `for_reading` matches `is_key_trigger`
      after the backfill, even though the value is uniformly 0 since
      nothing had ever been flagged "key" before this session), a full
      Flask test-client round-trip (create tag → apply to a REAL news row
      → list → remove → confirm it's really gone) + all 4 grammar guard
      400s correct, `npm run build` succeeded (356 modules). The
      verification tag (`who:warsh-verify`) was DELIBERATELY left in the
      real dictionary (usage_count=0 after being removed) — there's no
      delete-from-dictionary endpoint in C-1 (that's genuinely not a C-1
      feature; dictionary cleanup happens via the quarterly review §21.7,
      not an ad-hoc button) — harmless, will get filtered out naturally at
      the first quarterly review.
- [x] ~~Bug: DXY/US10Y/VIX looked "stuck" even though there's no date gap
      (17 Jul 2026)~~ — Giel reported these 3 fields being frozen for
      several days, and had already checked himself that there's no
      missing date row. **Root cause was not a fetch failure** —
      `source_flags` for `fred_dxy`/`fred_us10y`/`fred_vix` were all `ok`
      (the API call succeeded every day). The problem:
      `scrapers/macro_fred.py::_fetch_series()` always grabs the LATEST
      observation available from FRED, then labels it with `run_daily`'s
      target date WITHOUT checking whether that observation is actually
      for that day. FRED itself publishes DXY/US10Y/VIX with a lag (not
      real-time) — checked directly: DXY (`DTWEXBGS`) was 7 days stale,
      US10Y/VIX 2 days stale when the bug was found. If FRED hasn't
      updated since the last fetch, the result is an IDENTICAL number for
      several days in a row (confirmed: 120.5046/4.55/15.67 exactly the
      same in `daily_market` for 14–17 Jul) — not a scraping bug, but the
      old `source_flags` couldn't distinguish "fresh" from "stale but
      fetched successfully".
      **Fix**: a `MAX_LAG_DAYS` per series (DXY/US10Y/VIX/RRP/TGA/HY=4
      days, WALCL=10 days — the H.4.1 weekly release comes out every
      Thursday) + a lag check in `fetch_macro_fred()`, overwriting the
      flag to `'stale'` (not `'ok'`) if the observation is older than its
      limit — **the value is STILL written** (a stale number is still more
      useful than NULL), it's just now visible as different on the
      dashboard. There was briefly a miscalibration of the DXY threshold
      to 10 days (assuming it was weekly) — DXY's own observation history
      (5 calendar days in a row) proves it's business-daily too, lowered
      to 4 so the newly found bug would actually get flagged. Frontend:
      `.dot.stale` (color `--med`, different from fail/ok/skip) +
      `SnapshotView.vue` sort order `fail→skip→stale→ok`. 2 new tests
      using monkeypatch (`tests/test_macro.py` — a live test can't
      deterministically control how stale FRED's real data is on a given
      day, same pattern as the `test_notify_telegram.py` exception). 356
      tests green total.
      **Verified live** against the real DB: `fred_dxy` is now `stale`,
      `fred_us10y`/`fred_vix` remain `ok` (2-day lag is still within
      reasonable weekend bounds) — confirmed via a real `/api/latest`
      call, not just a unit test.
- [x] ~~News Threads: automatic catch-up scan + edit title/keyword +
      multi-link in the News page (17 Jul 2026, 3 requests from Giel at
      once after checking the `/threads` page)~~ — Giel reported that a
      thread created midday had no links (a real ACTIVE thread, but 0
      SUGGESTED) even though a relevant headline already existed in
      `daily_news`. **Root cause**: `suggest_thread_links()` was only ever
      called by `run_daily` with headlines NEWLY FETCHED that day — it
      never rescanned history already in the DB. A thread created after
      the morning cron = missing every morning's news until tomorrow's
      cron. Patched manually first (68 real links found via a
      retroactive scan), then Giel asked for 3 things:
      **1) Automatic catch-up scan** — `THREAD_CATCHUP_DAYS = 7`,
      `save_thread()` & `patch_thread()` (when `keywords` change, for an
      ACTIVE thread) now scan `daily_news` 7 days back & run
      `suggest_thread_links()` immediately, instead of waiting for
      tomorrow's cron. Idempotent via the existing dedup UNIQUE index
      (safe to re-run/overlap windows).
      **2) Edit title/keywords in `/threads/:id`** — `patch_thread()`
      extended to accept `title` (non-empty guard) & `keywords` (JSON-
      encoded, same pattern as `persona_tags`); the `/api/threads/<id>`
      endpoint's field whitelist extended; `ThreadDetailView.vue` gets 2
      new inputs in the existing edit form.
      **3) Multi-thread-link in `/news`** — previously
      `attach_thread_suggestions()` only sent 1 'winning' `thread_link`
      (CONFIRMED beats SUGGESTED) per news item, so if one headline
      matched >2 threads Giel couldn't see/change/remove the others.
      Changed to send a `thread_links` array (all non-REJECTED links,
      CONFIRMED first). `NewsView.vue`'s Thread column now renders
      multiple chips at once (each chip has its own action — Confirm/
      Reject for SUGGESTED, Unlink for CONFIRMED, reusing `POST
      /api/threads/link/<id>/reject` which already accepts a link of any
      status) + a new "+ Link Thread" affordance (dropdown of ACTIVE
      threads + stance, reusing `POST /api/threads/<id>/links`'s
      `add_thread_link_manual` which already exists for
      `ThreadDetailView`, no new endpoint).
      9 new tests (`test_web_writes.py` — catch-up scan idempotency &
      window respect, empty-title guard, catch-up triggered when keyword
      changes, `attach_thread_suggestions` array shape including
      exclude-REJECTED). 364 tests green total. **Verified**: a Flask
      test-client round-trip against an isolated temp DB (create thread →
      manually link to a news item → shows up in `/api/news` as
      `thread_links` → reject → disappears again) — at one point
      MISTAKENLY used the env var `DB_PATH` (not `KASTARA_DB_PATH`) on
      the first attempt, unintentionally writing a test thread+link to the
      REAL PRODUCTION DB; caught via direct sqlite inspection, immediately
      cleaned up (`DELETE` thread id 5 + link id 70), confirmed the state
      was back to exactly how it was before continuing with the correct
      temp DB. `npm run build` succeeded (356 modules).
- [x] ~~Inline edit title/status/keywords/current reading directly on the
      `/threads` index (17 Jul 2026)~~ — previously editing these fields
      was only possible via the detail page (`/threads/:id`), Giel asked
      to be able to do it straight from the list. Same pattern as
      `subtitleInputs`/`editingIds` in `NewsView.vue`: an `editingIds` Set
      + an `editInputs` dict per row, "Edit"→input/select appears→"Save"
      POSTs to `/api/threads/<id>` (endpoint already existed, no backend
      changes). Verdict STAYS on the detail page only (rarely used,
      mandatory only when CLOSED) — if status is set to CLOSED from the
      index without a verdict, `patch_thread()` rejects it with an error
      toast, pointing to the detail page.
- [x] ~~Addendum C §21 FULLY complete: closing the C-1 gap (Settings page)
      + building C-2 (17 Jul 2026, Giel: "run addendum C" → an explicit
      override of the §21.8 wait-2-weeks clause, "Section 21 &
      C-1/C-2. FINAL")~~ — a re-audit found **1 real gap in C-1 itself**:
      §21.8 lists "Settings → Tag & Thread Management" (§21.11) as a C-1
      item, but it was never built (NewsView only had a read-only tag
      table, no merge/delete/edit-description, no thread-management page
      outside the per-row view). The rest of C-1 (schema, tag CRUD,
      command-palette, `for_reading`, `display_subtitle`) is genuinely
      complete & tested.
      **Part 1 (closing the C-1 gap)**: `web/writes.py` — `update_tag`
      (description/facet), `delete_tag` (guards usage_count>0 without
      force → ValueError, force deletes the tag + its content_tags),
      `merge_tag` (from becomes an alias of into, content_tags are re-
      pointed dedup-aware via INSERT OR IGNORE + DELETE of redundant rows,
      usage_count is RECOMPUTED from actual row count rather than summed —
      preventing miscounts when re-pointing collides), `list_orphan_tags`,
      `thread_stats`/`list_threads_with_stats` (CONFIRMED stance
      composition, pending SUGGESTED, age in days, a global `active_count`
      for "N/7 ACTIVE", plus thread facet tags by reusing
      `attach_content_tags(conn, "news_threads", rows)` — no new function
      needed since `news_threads` is already in
      `ALLOWED_CONTENT_TAG_REF_TABLES`). 5 new endpoints
      (`/api/tags/<id>{,/delete}`, `/api/tags/merge`, `/api/tags/orphans`,
      `/api/threads/stats`). A new `SettingsView.vue`, 2 tabs (Tags:
      inline edit/delete/merge + a merge form; Threads: a composition/age
      table + a "Manage Thread" Dialog (status/current_read/verdict/
      persona_tags 4-lens checkboxes/facet tags via a reused
      `TagAutocomplete`) — route `/settings` + a new "Settings" nav group
      (App.vue, separate from "Daily" since it's reflective/quarterly, not
      a daily ritual).
      **Part 2 (C-2)**: (a) `suggest_tags_for_news()` — rule-based auto-
      tagging (NOT an LLM, §21.9), keyword pool = `aliases +
      value.replace('-',' ')` per tag, result always `source='SUGGESTED'`,
      mirrors `suggest_thread_links()` exactly. (b) `suggest_thread_
      links()` extended to ADD a tag-overlap path (thread facet tags vs
      news facet tags) ALONGSIDE the old keyword match (the contract
      explicitly says keywords become "legacy/fallback," NOT removed — a
      thread with no facet tag automatically falls back to keyword-only,
      an empty union never matches). (c) `pipeline/run_daily.py` hook
      order: `insert_news_dedup` → `suggest_tags_for_news` → `suggest_
      thread_links` (tag first, then tag-match thread, so it can see the
      newly suggested tag in the same run) → `auto_dormant_stale_threads`
      (an ACTIVE thread stale >30 days automatically goes DORMANT, not
      deleted — `STALE_THREAD_DAYS` a new constant, same pattern as
      `THREAD_CATCHUP_DAYS`). (d) `compose_persona_context()` +param
      `extra_news_ids` (default `None`, fully backward-compatible) — an
      ADDITIONAL "GIEL'S SELECTED NEWS" block at the end of the context, a
      structural guard (the slice is ALWAYS called regardless of this
      parameter) guarantees manual selection NEVER replaces the slice
      (§21.4). `/api/persona/run` accepts an optional `news_ids`.
      `NewsView.vue` — a per-row checkbox + "Send to Lens →" button + a
      Dialog to choose the lens. (e) a new `tools/backfill_tag.py` CLI
      (`--thread-id --since`, same pattern as `tools/review_signal.py`) —
      directly reuses (a)+(b), NO new matching logic, NEVER writes
      stance/CONFIRMED/current_read (guard explicitly tested). LLM triage
      (§21.9, optional/gated) DELIBERATELY not built — the rule-based
      default is already enough, not in the "FINAL" scope. The Reading
      Page saved filter (§21.8, itself marked "optional bonus" in the
      contract) is also skipped for the same reason.
      A SUGGESTED tag chip (from auto-suggest) looks visually different
      from a MANUAL one (dashed border + "?" suffix) in `NewsView.vue` —
      `attach_content_tags()` now also sends `source` per tag (previously
      only canonical/facet/id).
      25 new tests (`test_web_writes.py`: update/delete/merge_tag +
      list_orphan_tags + thread_stats + suggest_tags_for_news idempotency
      + tag-overlap match without keywords + regression check that
      keyword-only-thread still works + auto_dormant only affects
      ACTIVE+stale; `test_compose_persona_context.py`: extra_news_ids
      block + guard-never-replaces-slice; a new `test_backfill_tag.py`:
      guards that stance/CONFIRMED is never written). 388 tests green
      total (no new tables/columns — schema stays at 27 tables, all reuse
      of existing Addendum C structures). 82 `/api/*` endpoints (up from
      77). **Verified**: a Flask test-client round-trip against an
      ISOLATED TEMP DB (not production this time — a lesson from the
      `DB_PATH` typo incident in the previous entry, `KASTARA_DB_PATH` set
      explicitly before any import in every ad-hoc verification script
      starting this session): create 2 tags → apply both to 1 news item →
      merge → 1 tag remains, no UNIQUE violation. `suggest_tags_for_news`+
      tag-match `suggest_thread_links` against a temp DB with a thread
      that has a facet tag but no keyword overlap → a SUGGESTED link
      appears purely from the tag match. `npm run build` clean,
      `SettingsView` shows up in the chunk list (proof the lazy route
      actually compiled, not just a console-check of the login page that
      was a blind spot last session). Same as always: no visual browser
      verification possible behind the login (Giel briefly offered his
      password directly, still declined — the credentials rule has no
      "it's your own" exception).
- [x] ~~Consolidate the `/threads` index into Settings > Threads tab (17
      Jul 2026, right after Settings was built)~~ — Giel: the `/threads`
      page (formerly: thread list + create-new form) became redundant/
      empty once Settings > Threads tab existed (2 places managing the
      same thread list). The content of `ThreadIndexView.vue` (status
      filter, inline-edit title/status/current-reading/keywords, "+ New
      Thread" form) was MOVED ENTIRELY into `SettingsView.vue`'s Threads
      tab, merged with the existing composition/age/facet-tags columns
      there — the `ThreadIndexView.vue` file was DELETED (not left dead,
      no references remain). `/threads/:id` (CONFIRMED link timeline,
      confirm/reject SUGGESTED, manual linking) REMAINS separate — a
      different function (reading daily results, not reflective curation)
      — but is removed from the sidebar nav, only reachable via the
      "Timeline" button in Settings or a thread chip in `/news`.
      `ThreadDetailView.vue`'s "Thread Index" button & error redirect now
      point to `/settings?tab=threads` (instead of the now-gone
      `/threads`) — `SettingsView.vue` reads `route.query.tab` on mount so
      a deep link opens the Threads tab directly. Sidebar nav: the
      "Threads" item removed from the Daily group (News + Forward +
      Reading + Chart + Synthesis + Snapshot = 6 items, Threads no longer
      among them). Also closed 1 small gap that didn't exist yet: **create
      a new tag directly from Settings** (`+ New Tag`, a form with
      canonical+aliases+description all at once — different from
      `TagAutocomplete`'s "+ create new tag" which is canonical-only/a
      quick path from News; in Settings Giel usually already knows the
      alias/description upfront). No backend/schema changes — purely a UI
      move & reorganization, all endpoints used already existed. 389 tests
      green (backend Python untouched at all).
      `npm run build` clean: 356 modules (down from 357 —
      `ThreadIndexView` gone from the chunk list, proof the file really
      is no longer bundled).
- [x] ~~Seed `tag_dictionary` + initial thread candidates (Addendum C
      §21.12, 17 Jul 2026, Giel sent `seed_tags_threads.md`)~~ — saved to
      `docs/seed_tags_threads.md`, imported via `pipeline/seed_tags.py`
      (`python -m pipeline.seed_tags`, same pattern as
      `seed_context_weight.py`: idempotent, no-arg, `init_db()` +
      `get_connection()` + a single commit). **Checked first before
      running**: the production DB already has 5 ACTIVE threads with
      their OWN titles & thesis direction ("Warsh Regime Dovish",
      "IHSG Strengthens, Stocks Bullish", etc.) that don't map 1:1 to the
      generic candidates in the doc (e.g. Candidate A wrote "Hawkish" — the
      OPPOSITE direction from the real thread "Warsh Regime Dovish").
      Asked Giel: seed all 8 candidates as **DORMANT** (not ACTIVE) — the
      script NEVER touches/closes existing threads, it only adds tags + 8
      new candidates with DORMANT status ready to be manually activated
      from Settings whenever the narrative is actually confirmed being
      tracked. `who:purbaya` DELIBERATELY skipped (title/spelling not yet
      verified, per the doc's own Usage Rule #3).
      **Bug found+fixed while testing**: 8 of 71 tags (`sym:btc`,
      `sym:eth`, `sym:xau`, `sym:dxy`, `sym:us10y`, `sym:vix`, `sym:sp500`,
      `sym:idx`) failed `_validate_tag_grammar`'s "sym: requires a region
      prefix" rule — even though contract §21.1 itself gives `sym:btc`/
      `sym:xau` as vocabulary EXAMPLES WITHOUT a prefix (a small
      contradiction in the contract text: the rule says "required" but the
      example violates it). Fixed: a new `_GLOBAL_SYM_EXEMPT` allowlist
      (`web/writes.py`) — global/macro symbols that aren't ambiguous
      across markets are exempted from the mandatory region prefix;
      individual stock tickers (`bbca`, etc.) STILL require the prefix
      (the old test `test_create_tag_sym_requires_region_prefix` is
      unchanged, a new test `..._global_symbols_exempt...` adds coverage).
      1 new test, 390 tests green total. **Result in the production DB**:
      71 new tags + 8 DORMANT thread candidates (ids 7–14) — confirmed via
      direct query: the 5 real ACTIVE threads (ids 1,2,3,4,6) COMPLETELY
      UNCHANGED, `tag_dictionary` went 1→72 rows. Verified first against an
      isolated temp DB (idempotency: re-running twice doesn't duplicate
      anything) before running against production.
- [x] ~~Article Digest D-1: plain RSS summary (Addendum D §22, 23 Jul 2026,
      Giel added 2 new addenda at once -- D §22 & E §23)~~ — Giel asked for
      one of them to be built ("yers" -- ambiguous, not specific to D or
      E). Checked first: `prediction_log` in production has 0 rows, while
      Addendum E (Meta-Layer) itself requires "≥1-2 months of content"
      before M-1 may be built -- so E CAN'T do anything right now, the
      decision fell to D-1 (the contract itself says "build now, it's
      cheap," no prerequisite). E is documented as deferred, not ignored.
      **Built (D-1 only, D-2 CONDITIONAL/not yet)**: `db/connection.py` --
      a new `rss_summary TEXT` on `daily_news` via `_COLUMN_MIGRATIONS`
      (a new column, no backfill -- unlike `for_reading` which needed old
      values copied over). `scrapers/news.py` -- `_clean_rss_summary()`:
      strip HTML using `BeautifulSoup` (already a dependency, used by
      `investing_calendar.py`/`positioning.py`), tidy whitespace, truncate
      to 400 chars + "…". `fetch_all_news()` fills `rss_summary` from
      feedparser's `.summary`/`.description` (feedparser's own alias),
      None if the feed doesn't include it -- NULL is expected, not an
      error. `pipeline/run_daily.py`::`insert_news_dedup` writes the new
      column (defensive `.get()` since other sources like `add_article.py`
      don't always have this field -- a different table actually,
      `manual_articles`, so it's never really hit, but the defensive
      guard is kept anyway). `web/app.py`: `/api/news` SELECT adds the
      column. `NewsView.vue`: a collapsible `<details>` "RSS summary"
      below the headline/subtitle, closed by default (not always shown --
      200 rows x 2-3 lines of summary each would make the table too long
      at all times). `compose_persona_context.py`: both `_key_news_lines`
      (the automatic slice) & `_manual_selection_block` (the §21.4 manual
      feed) now add a `[RSS summary]: ...` line below the headline/Giel's
      note -- the headline STAYS the first line/factual anchor, never
      replaced (§22.5 guard).
      Thread digest (§20.4) is NOT touched -- that path itself hasn't been
      built yet (News Threads N-2 doesn't exist yet).
      `pipeline/compose_briefing.py` (Telegram) is DELIBERATELY untouched
      -- it's not one of the "3 context paths to the lens" mentioned in
      §22.5, the Telegram message must stay concise.
      8 new tests (`test_news.py`: `_clean_rss_summary` None/HTML/truncate
      + a live-fetch check that the `rss_summary` key is always present;
      `test_db.py`: the new column is NULL-safe;
      `test_compose_persona_context.py`: the line appears when present,
      does NOT appear when empty, on both the slice+manual paths).
      **Also found along the way**: 2 old tests (`test_save_thread_runs_
      catchup_scan_against_existing_news`,
      `test_patch_thread_keyword_change_triggers_catchup`) FAILED not
      because of this work -- a hardcoded seed date `"2026-07-15"` had
      gone 8 days stale past the `THREAD_CATCHUP_DAYS=7` rolling window
      (real `today_wib()` is now 2026-07-23, proof real time is passing
      during this long session). Fixed: the seed date is now RELATIVE to
      `today_wib()` (not a hardcoded string), fixed once so it won't go
      stale again going forward. 1 live test
      (`test_earnings_yf.py::test_has_future_earnings_with_null_actual`)
      also failed for the same reason (TSLA's 22 Jul earnings, previously
      "future," has now had its actual released) -- LEFT AS IS, that's the
      inherent nature of live-data tests (not a bug, not touched).
      396 tests green total (excluding the 1 live test above that's
      sensitive to the calendar date). `npm run build` clean. **Not yet
      evaluated**: D-1 needs to be used for a few days before deciding
      whether to proceed with D-2 or stop here (the contract's own §22.3).
- [x] ~~WSL cron dead for 6 days + scope refinement making rss_summary
      HIGH-only (24 Jul 2026)~~ — Giel reported via Manual Backfill that
      "not everything came in" + asked whether News was also affected.
      **Root cause**: `service cron` on this WSL instance was NOT RUNNING
      (checked via `service cron status`) -- `run_daily` hadn't run since
      2026-07-17, 6 days stale (both market data AND news affected, not
      just one side). Explained to Giel: Backfill only covers
      `asset_ohlcv`+FRED macro fields per instrument (yfinance/FRED have
      historical APIs) -- News can NEVER be backfilled (RSS only serves
      LIVE entries right now, there's no "last week's headlines" API).
      The 07-18..07-22 News gap is permanently unrecoverable, that's an
      inherent limitation of the data source, not a bug. **Action**:
      `python -m pipeline.run_daily` run manually (rather than waiting for
      cron) -- 222 news items came in, 82 new tags, 57 new thread links
      (tag-match working for real for the first time with actual
      production data), all asset_ohlcv back to current. Giel was told to
      run `sudo service cron start` himself (needs the sudo password,
      can't be done for him). **Also**: Giel asked for `rss_summary` (D-1
      above) to be restricted to ONLY `impact_level=HIGH` -- contract
      §22.1 D3 originally wrote this restriction for D-2/LLM Digest (for
      cost reasons), but Giel explicitly asked for the same principle to
      apply to D-1 too (`scrapers/news.py::fetch_all_news` now skips
      parsing the summary entirely for MED/LOW, not just hiding it in the
      UI). 188 MED/LOW rows that had already gotten rss_summary filled in
      from the manual run above (before this scoping existed) were
      cleaned up directly in the production DB (`UPDATE ... SET
      rss_summary = NULL WHERE impact_level != 'HIGH'`) to stay consistent
      with the new rule -- confirmed 24/24 remaining rss_summary rows are
      all HIGH. 1 new test
      (`test_rss_summary_only_populated_for_high_impact`, monkeypatching
      the entry+feed-health spy since it needs deterministic control over
      HIGH vs LOW within a single fetch -- a rare exception from the
      live-test philosophy, same pattern as `test_notify_telegram.py`).
      397 tests green total.
      — initial research had BRIEFLY concluded to skip this (see the first
      attempt: hit an HTTP 429 that didn't recover after ~5-6 rapid
      requests, and the AJAX endpoint for "Yesterday" date navigation
      couldn't be found). But that problem was purely a RESEARCH issue
      (burst requests), not a production issue (1x/day) — once realized,
      the scope was changed entirely: **no date navigation needed at
      all**. Investing.com's default ("today") view is enough IF scraped
      in the EVENING/NIGHT (not morning alongside `run_daily`) -- that
      day's HIGH events already have their actual released by then. So
      it's 1 GET/day, not research bursts -- a completely different risk
      profile from what got blocked.
      **Built**: `scrapers/investing_calendar.py` (curl_cffi
      impersonate=chrome, same pattern as `idx_foreign_flow.py`; parses
      investing.com's Next.js SSR HTML; ONLY HIGH/3-star importance is
      taken, per the original request; skips events whose actual is still
      empty) + `pipeline/run_investing_actual.py` (a SEPARATE entrypoint
      from `run_daily.py`, its own evening cron -- see the "grab
      everything twice via cron" rationale below for why it's NOT merged
      into run_daily). Matching to existing `econ_calendar` rows uses
      `country` + `event_date` (+-1 day, accounting for the timezone
      difference between investing.com and WIB) + fuzzy-matching
      `event_name` (`difflib.SequenceMatcher`, threshold 0.5, SKIP if
      ambiguous/tied -- **an important finding during live verification**:
      normalization had BRIEFLY been discarding investing.com's
      "(MoM)"/"(YoY)" markers along with the release month "(Jun)",
      making "CPI (MoM)" and "CPI (YoY)" both become "cpi" -> a tie -> all
      skipped; fixed by normalizing "m/m"/"(MoM)" into a `mom` token
      (likewise for yoy/qoq) BEFORE stripping parentheses, with the rest
      (month/quarter names) stripped afterward). Written via the existing
      `set_econ_actual()` (no new write path created). **Verified live**
      against the real DB: 3 HIGH events (CPI m/m, Core CPI m/m, CPI y/y,
      14 Jul 2026) matched and got their actual filled in CORRECTLY (not
      mixed up between MoM/YoY). 19 new tests
      (`test_investing_calendar.py`, `test_run_investing_actual.py`), 312
      tests green total.
      **Not yet scheduled to cron** — needs 1 separate evening crontab
      line apart from the existing 00:00 `run_daily` line, Giel will set
      it up (see instructions in the README/conversation).
- [ ] Periodic DB size indexing/monitoring as volume grows (a sanity check,
      not necessarily meaning a migration is needed — see the SQLite
      rationale in ARCHITECTURE.md).
- [x] ~~Re-evaluate the RSS feed list~~ — the registry was moved to
      `scrapers/feeds_config.py` (the single place to manage feeds, change
      URL/enabled there, not in `news.py`) + `check_feed_health()` per
      feed on every run (ok/dead status goes into `source_flags` with the
      `rss_` prefix, same pattern as other APIs — a dead feed is visible
      immediately in the log, not a hidden backlog). All URLs were
      VERIFIED DIRECTLY (not assumed): **Reuters** & **Kontan**
      (`kontan.co.id/feed` AND `/rss`) confirmed genuinely dead (Kontan
      returns a normal HTML homepage, not XML, even with a browser UA —
      not a bot-block, it's really been shut down) → set to
      `enabled: False` + a note. **Bisnis.com** TURNED OUT to still be
      alive but on a different subdomain (`rss.bisnis.com`, not
      `bisnis.com/rss/market` which 404s) — found through re-research.
      Final result: **7 active feeds** (Fed FOMC, CNBC Finance, CNBC
      Economy, Investing ID, CNBC Indonesia, ANTARA Economy, Bisnis.com),
      tested live via `run_daily`: **7 ok, 0 dead**.
      `pipeline/run_daily.py` prints a summary `RSS: X ok, Y dead → [...]`
      every run. 9 new tests in `tests/test_news.py` (moved from
      `test_macro.py`), 127 tests green total. `IMPACT_KEYWORDS["HIGH"]`
      had briefly missed `"bi rate"` (only had the full `"bank indonesia"`)
      — found while porting the old test, added back so headlines
      abbreviated as "BI Rate ..." still register as HIGH.
- [ ] Backfill/fill in `econ_calendar` for past events if calendar history
      is ever needed (this scraper only gives a rolling "this week" window,
      not a historical source — would need a different source if history
      is really needed).
- [x] ~~`manual_articles` CLI~~ — `pipeline/add_article.py` complete (add +
      list/search by tag/date-range/keyword), 5 tests green. Used for
      historical research (e.g. from 2010) that RSS can't reach.
- [x] ~~Panel 1 Snapshot: Day/Week/Month/Year compare~~ — filter buttons
      above the snapshot cards (same pattern as the Panel 5 range filter),
      each card shows a delta + arrow (▲ green up / ▼ red down) vs D-1/
      W-1/M-1/Y-1. `web/app.py::_compare_from_series()` finds the nearest
      historical point <= the target date (not an exact match, since gaps
      in the calendar are expected given `run_daily` is manual). Columns
      whose instrument exists in `asset_ohlcv` (BTC/SP500/IHSG/USDIDR/
      USDJPY/Gold) use history from THERE (can go back >10 years), not
      `daily_market` (only ~4-5 rows for those columns since they only
      recently started being populated for real) — without this, week/
      month/year compare for instrument prices would always be n/a. Other
      columns (DXY/US10Y/VIX/etc., backfilled from FRED since 2010) & any
      columns genuinely without long history yet (BTC Vol MA20, Funding
      Rate, Fear & Greed, Net Liquidity) still show `n/a` for periods
      where there isn't enough data — not a bug, being honest about data
      limits. A single `/api/latest` fetch is enough (all periods computed
      at once server-side), toggling in the frontend is purely a display
      change with no refetch. 5 new tests (`tests/test_web_app.py`, the
      first test for `web/app.py`), 132 tests green total.
- [x] ~~Panel 1: card categories, collapse source_flags, data gap
      detection~~ — 3 UX complaints at once:
      1. **Snapshot cards grouped** into 3 categories (Crypto (BTC), Global
         Macro, Equity & FX) — `SNAPSHOT_FIELDS` in `web/app.py` changed
         from a flat dict to a list-of-dicts with a `category`, rendered
         per group on the frontend (instead of one flat 14-card grid).
      2. **"Data Source Status (source_flags)" made collapsible** — native
         `<details>`/`<summary>` (not custom JS), closed by default, a
         ▸/▾ triangle showing state.
      3. **Data gap detection in Manual Backfill** — a new endpoint `GET
         /api/data_gaps?instrument=X`, runs automatically whenever the
         instrument dropdown changes (`web/app.py::_detect_gaps()`). Each
         instrument is mapped to an expected calendar
         (`INSTRUMENT_SOURCE`): `DAILY` (BTC, RRP — RRP confirmed to
         release daily per FRED metadata), `WEEKDAY` (equities/forex/DXY/
         US10Y/VIX/HY), `WEEKLY_WED` (WALCL/TGA — confirmed to release
         weekly, the gap between Wednesdays is DELIBERATELY not treated as
         a gap). A 1-day gap (a normal holiday) isn't reported, only
         >=2 expected-days in a row. Found a real gap while testing: IHSG
         had 58 gaps (mostly during Lebaran holiday week — clearly visible
         from the date range), Giel decides whether that's normal or needs
         backfilling, the tool just provides visibility. 9 new tests
         (`tests/test_web_app.py`), 141 tests green total.
- [x] ~~News "key trigger" visibility + Synthesis rework + History tab~~ —
      complaint: the "key" button on Panel 2 didn't show whether something
      was already flagged or not, and the flag result only ever showed up
      in Telegram, so its purpose was unclear.
      1. **Panel 2 News**: date filter (defaults to today) + impact filter +
         a "🚩 Key only" button; flagged rows are a different color
         (`.news-key`); the flag button is now a TOGGLE (★ Key / 🚩 key,
         click again to unflag). `/api/news` already returned
         `is_key_trigger` & accepted `date` from the start — just added
         the `key_only` param.
      2. **Panel 4 Reading**: a "Today's Key News" section (read-only)
         above the 4 lenses — flagged news to use as material for writing
         analysis. This is what gives the key button "purpose" inside the
         dashboard, not just Telegram.
      3. **Panel 6 Synthesis**: a date-picker + auto-load (synthesis &
         outlook for the chosen day), and **fixed Outlook, which previously
         wasn't being saved anywhere** — now persisted (reuses
         `reading_workspace` lens=`OUTLOOK:<INSTRUMENT>`, upsert 1
         stance/instrument/day, no schema change).
      4. **Panel 7 "History" (NEW)**: an archive for manual input that
         didn't have a history view yet (chart/news/snapshot already had
         one). A tab with sub-tabs: Synthesis / Predictions (full track
         record) / Trading Journal / 4 Lenses. New read-only list helpers
         in `web/writes.py` + a GET route in `web/app.py`.
      7 new write tests, 148 tests green total; every panel verified live
      in the browser (toggling key, Key-only filter, key news in Panel 4,
      outlook persist + reload, synthesis save/load, the History sub-tabs),
      test data cleaned up.
- [x] ~~UI: single-select filters turned into `<select>` + search/sort/
      pagination across all tables~~ — 2 UX complaints at once:
      1. **3 filter button-groups that were only ever single-select** (never
         multi-select) turned into `<select>`s to save space: Snapshot
         Day/Week/Month/Year (`#snapshotPeriodSelect`), News Impact/Key-
         only (`#newsImpactSelect`), Chart range 1M/3M/6M/1Y/All
         (`#chartRangeSelect`). The old `.news-filters` button-group CSS
         removed, no longer used.
      2. **Generic search + sort + pagination** added to EVERY data table
         (News, Signals, Econ Calendar, Positioning, Policy Notes, and all
         4 sub-tables of Panel 7 History — 9 tables total). 1 reusable JS
         utility (`applyTableControls()`/`renderTableBar()`, reused rather
         than reimplemented per table): search (250ms debounce), per-
         column sort (click a `<th data-sort="field">` header, delegated
         click listener), pagination (10/20/50/100 rows per page). Search/
         sort/paging operate on `tableCache[key]` (data already fetched) —
         changing page or order does NOT refetch from the server, only
         server-side filters (date range, impact, etc.) trigger a new
         fetch. `renderSignalsTable()`'s hardcoded `.slice(0, 30)` was
         removed, so the Panel 5 Signal table can now access all ~200
         signals via pagination, not just the first 30.
      **Architecture decision**: staying with vanilla JS/HTML, NOT moving
      to a frontend framework (React/Vue/etc.) — single-user, local-only,
      no build pipeline; search/sort/pagination is only ~80 lines of
      utility, doesn't need a framework. A framework migration would be
      relevant later if this becomes multi-user/commercial (Master Plan
      Phase 2/3), not for UX polish. Verified live across all 9 tables
      (search filter correct, sort asc/desc correct, pagination page-count
      & Prev/Next correct).

- [x] ~~`index.html` split into partials/static assets~~ — a single 1,700-
      line file (HTML+CSS+JS mixed together) was split, WITHOUT changing
      any behavior and WITHOUT moving away from Jinja2/vanilla JS
      (consistent with the architecture decision above):
      1. **CSS** → `web/static/css/dashboard.css` (linked via
         `url_for('static', ...)`).
      2. **Per-panel HTML** → `web/templates/partials/panelN_*.html` (7
         files, 1 per tab), `{% include %}`-ed from `index.html`.
      3. **Per-panel JS** → `web/static/js/{core,panel1..7,main}.js` (9
         files: shared helpers/table utility in `core.js`, each panel
         split out for easy lookup, `main.js` holds `refreshAll()` +
         init), loaded via `<script src>` in order (dependency order: core
         first, then panel1-7, then main — because all functions are still
         global, not modules, so load order matters).
      `index.html` is now ~57 lines (just a shell: head+nav+includes+script
      tags). Flask's default `static_folder`/`template_folder` (relative to
      `web/`) used as-is, no new config needed. Verified: 148 tests stayed
      green (purely a frontend restructure, backend untouched), a live
      browser check of each panel (1/2/5/7 checked explicitly — snapshot
      cards, news table+pagination, 335-element SVG chart, History sub-
      tab) with no console errors, all assets loading 200/304.
- [x] ~~Panel 4: descriptive 4-lens labels + remove "Today's Entries"~~ — 2
      UX complaints:
      1. The 4-lens card labels were just codes (GEMA/LEON/AKELA/RIVAN)
         with no context on their function. Now they read "GEMA · Global
         Macro" / "LEON · Local Macro" / "AKELA · On-chain/Fundamental" /
         "RIVAN · Market Sentiment & Psychology" (a new `LENS_LABELS` map
         in `core.js`, also used in the Panel 7 4-Lens history for
         consistency). **The `lens` code in the DB is UNCHANGED** (still
         GEMA/LEON/AKELA/RIVAN) — just a display label, so old history
         stays compatible.
      2. The "Today's Entries" section (a small table under the 4 lenses,
         showing only today's entries) was removed from Panel 4 — already
         redundant since Panel 7 "History > 4 Lenses" exists (shows ALL
         history including today, at the top row).
         `loadReadingEntries()` in `panel4.js` removed, `main.js::
         refreshAll()` adjusted accordingly.
      Verified live: new labels appear on the Panel 4 cards & the Lens
      column in Panel 7, "Today's Entries" is gone, saving the 4 lenses
      still works (checked the saved row via direct DB query, then
      cleaned up).
- [x] ~~Panel 4: the 4 Analyses become AI-generated (OpenRouter)~~ — an
      **explicit, deliberate deviation** from the Phase C principle
      (`web/writes.py` §0 / Master Plan: "the 4 lenses are filled in
      manually, not by an AI agent"). At Giel's direct request, the 4
      analyses (GEMA/LEON/AKELA/RIVAN) are now generated via OpenRouter,
      triggered manually per card (a "Run Analysis" button), shown read-
      only in a popup modal (not an editable textarea). Codenames are
      anonymized in the UI (only the function labels show: Global Macro /
      Local Macro / On-chain-Fundamental / Market Sentiment & Psychology)
      — the `lens` code in the DB is UNCHANGED, old history stays
      compatible.
      1. **`llm/persona_analysis.py`** (a new package, same pattern as
         `notify/telegram.py`) — calls an OpenRouter chat completion via
         `requests` (already a dependency, no new SDK). The model comes
         from the `OPENROUTER_MODEL` env var (default
         `anthropic/claude-3.7-sonnet`). Each persona's system prompt is
         written manually by Giel in `prompts/persona_<lens>.txt` — **NOT
         auto-generated, NOT committed** (gitignored, treated as Giel's
         personal analysis IP, only `prompts/README.md` is tracked). If
         the file is empty/missing, `run_persona_analysis()` raises
         `PersonaPromptMissing` — the endpoint returns a clear error to the
         UI, NOT a silent skip or running with an empty prompt (per the
         explicit request: "if the persona prompt isn't there yet, tell
         me").
      2. **`pipeline/compose_persona_context.py`** — a pure function (same
         pattern as `compose_briefing.py`), assembles ONE context blob
         (market snapshot + today's key news) sent IDENTICALLY to all 4
         personas; each one's system prompt determines the point of view
         (not different context per persona — simplified because we don't
         have real separate on-chain data).
      3. **`web/writes.py::save_persona_analysis()`** — upsert (DELETE
         then INSERT, same pattern as `save_outlook`) so re-running the
         same persona on the same day OVERWRITES instead of piling up
         duplicates in the Panel 7 history.
      4. **`web/app.py`**: `POST /api/persona/run` (body `{lens}`, runs 1
         persona) + `GET /api/persona/status` (checks whether the prompt
         has been filled in yet, used to render the card). Reuses the
         existing `GET /api/reading?date=X` to load saved results (no new
         route needed).
      5. Other manual notes (External AI Check, Conflict Notes, Synthesis,
         Outlook, Trading Journal, Prediction Log) **UNCHANGED** — still
         100% manual, this deviation's scope is DELIBERATELY limited to
         just the 4 analyses.
      Verified: 14 new tests (`test_persona_analysis.py`,
      `test_compose_persona_context.py`, + 2 upsert tests in
      `test_web_writes.py`, all mocked — no real OpenRouter hits), 162
      tests green total. Live browser: the "prompt not filled in yet"
      path (all statuses `false`, button shows a toast, no API call) was
      verified before the real prompts were filled in by Giel.
- [x] ~~Panel 1: Aggregate OI + Long/Short Ratio + Long/Short Liquidation
      24h (Coinalyze)~~ — a new scraper `scrapers/coinalyze.py` (same
      pattern as `scrapers/crypto.py`), 3 Coinalyze endpoints tested LIVE
      before being written (`/open-interest`, `/liquidation-history`,
      `/long-short-ratio-history`, auth `Authorization: Bearer <key>`, no
      key = skipped rather than erroring). **Aggregate OI = sum of 3 major
      exchanges** (Binance/OKX/Bybit — the Coinalyze API has no ready-made
      combined symbol, it has to be summed manually; per-exchange symbol
      formats differ, e.g. Binance `BTCUSDT_PERP.A` vs Bybit `BTCUSDT.6`
      with no `_PERP` suffix — checked one by one, not guessed).
      **Liquidation split into long vs short** (2 new columns
      `btc_liq_long_24h`/`btc_liq_short_24h`), NOT 1 combined number — the
      old column `btc_liquidation_24h` (since Phase A, intended for
      CoinGlass) is left empty/unused, not deleted (avoiding a risky
      migration). The `btc_long_short_ratio` column (also since Phase A,
      also previously empty) is finally populated too. `btc_oi_aggregate`
      is a new column, DIFFERENT from the existing `btc_oi` (that one is
      Binance-only, single-exchange) — both still exist, neither replaces
      the other. **Migrating columns into the old DB**: `CREATE TABLE IF
      NOT EXISTS` in `schema.sql` doesn't add columns to a table that
      already has data — added `db/connection.py::_migrate_columns()`
      (checks `PRAGMA table_info` then idempotent `ALTER TABLE ADD
      COLUMN`), called from `init_db()`, tested against the real DB (not
      just the test DB) before proceeding. 5 new tests
      (`test_coinalyze.py`, live network, same pattern as
      `test_crypto.py`), 167 tests green total. Verified live: a full
      `python -m pipeline.run_daily` (not just the isolated scraper), 4
      new cards appear on Panel 1 in the "Crypto (BTC)" category with real
      numbers (aggregate OI ≈$12.35B, L/S ratio 1.46, long/short
      liquidation separated).
- [x] ~~Panel 3: IHSG Foreign Net Buy/Sell (IDX)~~ — a new scraper
      `scrapers/idx_foreign_flow.py`, source: idx.co.id's internal
      "Digital Statistic" JSON API (not a public official API, found via
      the open-source project `NeaByteLab/IDX-API`'s source code and
      confirmed LIVE before use — endpoint
      `primary/DigitalStatistic/GetApiData`, NO API key, just a session
      cookie). **Stores 3 raw components SEPARATELY**
      (`ihsg_ff_foreign_foreign`, `ihsg_ff_foreign_domestic`,
      `ihsg_ff_domestic_foreign`) + 1 computed net
      (`foreign_net_buy_value`), not just the net — the GEMA/LEON persona
      (Track D) needs to read F2F vs F2D vs D2F separately per their own
      interpretation rules. **An important correction** to the reference
      library `NeaByteLab/IDX-API`: the `foreignForeign*`/
      `foreignDomestic*` fields are NOT directly "buy"/"sell" as that
      library maps them — the ACTUAL column labels from IDX (from
      `columns[].Title` in the response): `foreignForeign` = "Foreign
      Investor Sell − Foreign Investor Buy" (F2F, foreign-to-foreign, NOT
      a directional signal), `foreignDomestic` = "Foreign Investor Sell −
      Domestic Investor Buy" (F2D, the distribution side). The correct
      formula: **Foreign Net Buy = domesticForeignValue (D2F, from the
      sibling endpoint) − foreignDomesticValue (F2D)** — tested & validated
      against a real figure (2026-06-02: −Rp 1.39 trillion, a sensible
      magnitude). **An important technical finding**: idx.co.id is behind
      Cloudflare bot-management — browser-realistic headers ALONE AREN'T
      ENOUGH (different from farside.co.uk, also Cloudflare, but headers
      are enough there, see `scrapers/positioning.py`). Confirmed via
      direct testing: the curl CLI got through consistently (3/3), but
      Python `requests`/urllib3 CONSISTENTLY hit a JS-challenge page ("Just
      a moment...", 403) with identical headers — it's about TLS
      fingerprint (JA3), not headers. Fix: a new dependency **`curl_cffi`**
      (requirements.txt) which mimics a real browser's TLS handshake — the
      ONLY scraper in this project that needs this. The `positioning`
      table is used as-is (generic per-instrument-per-day metric, NO new
      column needed on `daily_market`), reusing the existing
      `upsert_positioning` (natural key `date+instrument+metric`
      auto-dedupes) — just adding a list item, same pattern as the
      existing COT/ETF flow. The pull-a-range-not-1-day pattern (mirroring
      `fetch_btc_etf_flow`) was chosen because "today's" data is often not
      yet published when `run_daily` runs (confirmed: the current month
      always returns an empty array) — so the scraper pulls the WHOLE
      month every run, so any days missed by a prior failed/skipped run
      get backfilled automatically. 5 new tests
      (`test_idx_foreign_flow.py`, live network, same pattern as other
      scrapers), 172 tests green total. Verified fully live:
      `pipeline.run_daily` for June 2026 (a full month) — 80 rows went
      into `positioning` (20 trading days × 4 metrics), the 2026-06-02
      figure matched EXACTLY the manual calculation done during plan
      research, Panel 3 in the browser correctly showed all 4 rows.
- [x] ~~Panel 4: rewrite the 4-Persona context into Shared Core + Per-
      Persona Slice (system prompt v4)~~ — an **explicit architecture
      pivot from Giel**, reversing an earlier decision ("Same for all 4
      (Recommended)" when Panel 4 was first built). Reason: 4 analysts
      reading DIFFERENT data produce independent, debatable viewpoints
      (productive conflict), rather than 4 analysts reading identical data
      who just differ in speaking style.
      1. **`indicators/calc.py`**: `COMPARE_PERIODS`/`compare_from_series`
         (Day/Week/Month/Year delta) moved here from `web/app.py` — used
         by BOTH Panel 1 (`web/app.py`) and the persona context
         (`pipeline/compose_persona_context.py`), avoiding `pipeline`
         importing from `web` (which would be layering in the wrong
         direction if it stayed in app.py).
      2. **`pipeline/compose_persona_context.py`** — a full rewrite,
         signature now `compose_persona_context(conn, date, lens)`.
         **SHARED CORE** (all personas): date, key news, BTC close+H/M
         delta. **PER-LENS SLICE**: GEMA (DXY/US10Y/VIX/Net Liquidity/HY+
         delta, USD/JPY/Gold/SP500/BTCDom without delta, USD/IDR+delta,
         IHSG foreign flow F2F/F2D/D2F from Track C, COT DXY+ETF flow,
         Policy Tracker FOREIGN speakers), LEON (IHSG/USD-IDR+delta, IHSG
         foreign flow — framed DIFFERENTLY from GEMA: "policy-credibility
         report card" rather than "capital flow direction," econ_calendar
         country=ID, Policy Tracker DOMESTIC speakers), AKELA (full
         econ_calendar, Dissonance Flag, Fear&Greed+delta, VIX, BTC Vol
         MA20, funding rate, D/W/M/Y delta for key instruments), RIVAN
         (funding rate, aggregate OI+delta from Track B, 24h long/short
         liquidation, L/S ratio, ETF flow, BTC Dominance, volume vs Vol
         MA20). IHSG foreign flow is DELIBERATELY not given to
         AKELA/RIVAN (slice discipline). Policy Tracker foreign/domestic
         speakers are classified via an institution-name keyword match
         (`DOMESTIC_INSTITUTION_KEYWORDS`) — the `policy_tracker` table
         has no structured column for this.
      3. **`web/app.py::persona_run()`** — passes `lens` through to
         `compose_persona_context`.
      4. **`prompts/persona_{gema,leon,akela,rivan}.txt`** — replaced
         ENTIRELY (verbatim) with Giel's v4 system prompt, including
         explicit F2F/F2D/D2F interpretation guidance in the GEMA & LEON
         prompts.
      5. The Orchestrator prompt (an all-4-at-once debate panel + conflict
         synthesis, also in the v4 document) is **RECORDED as backlog**,
         NOT built — Panel 4 currently runs 1 persona per click, not a
         simultaneous debate panel; would need a separate UI design.
      **Finding during implementation**: `econ_calendar country='ID'` is
      ALWAYS empty right now — the ForexFactory source doesn't cover the
      Indonesian calendar at all (checked: `SELECT DISTINCT country` only
      has NZ/AU/CA/GB/US/EU/CH/JP/CN, no ID). Not a Track D bug — an
      existing data-source limitation, noted as-is in LEON's context text
      ("the ForexFactory source currently doesn't cover the ID calendar")
      rather than hidden.
      **Execution order**: Track B → Track C → Track D (strict, not a
      preference) — the GEMA/LEON slice needs Track C fields, the RIVAN
      slice needs Track B fields; wiring up the v4 prompt before its data
      exists would make a persona claim data that's actually empty.
      9 new tests (`test_compose_persona_context.py` fully rewritten,
      focused on verifying slice ISOLATION — GEMA fields don't leak into
      RIVAN etc.), 178 tests green total. Verified live: all 4 slices
      called with the same date against the real DB, confirmed the
      content is 100% different (not identical anymore), 1 real RIVAN run
      through OpenRouter — the result quoted REAL long/short liquidation
      numbers and correctly applied the "short-covering" interpretation
      rule from the v4 prompt, test rows cleaned up after verification.

## 🔶 Phase J+ — Equity Expansion (Build Contract v1.3 LOCKED 11 Jul 2026 + Addendum A 12 Jul 2026)

> **Single source of truth for the spec**: [phase_j_build_contract_v1_3_LOCKED.md](phase_j_build_contract_v1_3_LOCKED.md)
> (the complete contract file, verbatim from Giel). The summary below is for
> changelog context — if it differs from the contract file, the CONTRACT is correct.

The complete contract document (15 build steps J-0→J-13 + J-14/J-15 from
Addendum A, 3 gates G1-G3, the Emiten Grader module, the sizing/lot engine,
the manual-only execution layer, per-market calibration, the intake workflow,
the new Tab 8 dashboard panel) has been fully accepted from Giel — see the
locked decision summary in contract §18. Some steps could ALREADY be worked
on without waiting for the gates (schema + research + J-14), others are
explicitly BLOCKED until Giel fills in the inputs himself.

### Summary of locked principles — Sections 13-18 of the contract (NEWLY recorded, not all built yet)

- **§13 Per-Market Calibration**: one S&R/breakout engine, but parameters
  are tuned per market before an instrument may be promoted to the `TRADE`
  lane — 5 points: volume proxy (ATR/range) for assets with
  `has_real_volume=false`, stock R:R as an optimistic estimate (gap risk,
  different from BTC), ARA/ARB sizing buffer for IDX, S&R zone tolerance
  scaled per price fraction (not an absolute number), and mandatory
  bar-replay validation per instrument before `lane_validated_at` is filled
  in (**"An engine tested on BTC ≠ tested on BBRI"**). The IDX-vs-US
  characteristics table (ARA/ARB vs LULD, small gaps vs earnings gaps,
  loose vs tight retest, GTC limit orders placed on IBKR during the WIB
  afternoon without staying up late) — serves as a reference for J-3/K-2,
  not yet executed.
- **§14 Sizing & Lot Quantization**: risk budget ÷ entry-SL distance →
  **round DOWN** to a multiple of `lot_size` (actual risk ≤ planned,
  never the other way around); capacity insufficient for 1 lot → signal
  **SKIP** (`skip_reason=RISK_CAPACITY_EXCEEDED`), equivalent status to a
  R:R<1.5 skip; **strictly forbidden to move the SL just so the lot
  "fits"** — the SL stays structural, derived from the zone, sizing is what
  adjusts. Intentional side effect: this rule naturally filters the
  universe (an issuer that doesn't yet fit the risk capacity automatically
  only qualifies for the `INVEST` lane). Not yet built in
  `analysis/signals.py` — still J-3b in the build order.
- **§15 Execution Layer**: the system stops at signal+size, execution is
  100% manual by Giel's own hand (Stockbit for IDX, IBKR GTC limit orders
  for US, existing exchange for crypto) — **NO broker API integration for
  phase J-K**, this is a locked decision (§18 point 6). An explicit guard is
  written into the contract for the future: if broker API integration is
  ever reconsidered, it MUST go through a separate written review that
  answers "how does the human gate stay alive if execution is automated" —
  and that review MUST be done while NOT currently in a position/drawdown
  (a decision made out of frustration with manual execution = the most
  suspect kind of decision). Recorded here so this guard isn't lost if the
  idea ever resurfaces.
- **§16 Intake Workflow**: the feasibility-testing flow for candidate
  issuers outside the universe (metadata input → fundamental input, 8
  quarters target / 4 minimum with `LOW_CONFIDENCE` flag → scraper checks
  UMA/special monitoring board/suspension → grader runs → Giel's decision:
  universe/watchlist/reject, **recorded + mandatory reason**) — uses the
  SAME rubric as the existing universe, NO special path (an issuer that
  comes in because of hype/recommendation is precisely the one that most
  needs the integrity flag — the grader is a brake, not a rubber stamp).
  Implemented as Tab 8 Component C (see Addendum A below), not as a
  separate module.
- **§18 Locked decisions (7 points, Giel's review 11 Jul 2026)**: the
  official hierarchy persona→machine→Giel; the per-instrument `lane`
  model; **FULL VERSION of no-hold-through-earnings** for US stocks (close
  the position before earnings, WITHOUT the half-size option — different
  from the earlier draft which still offered that option); ARA/ARB sizing
  buffer = **1.5× SL distance** as default (revision only via journal
  evidence, not case-by-case); final skip rule + ban on moving the SL; the
  broker-API ban applies to phase J-K (not permanent); build order
  J-0→J-13 approved without changes.

### Addendum A (12 Jul 2026) — Universe & Grader Panel, new Tab 8

Closes the explicit backlog item "manual `instrument_metadata` input UI form"
(previously recorded in the "kickoff continuation" section below) — not a
separate module, it's part of Tab 8 of the dashboard. Position in the spine:
**box ⑤ READ** (context & universe management), NOT execution — no
approve/reject button for `trade_signals`, doesn't display entry/SL/TP
(that stays with Panel 5). Weekly/quarterly cadence, deliberately separate
from the daily ritual of Panels 1-6.

4 components (code pattern: writes go through `web/writes.py` pure
testable functions, reads new in `web/app.py`, partial `partials/panel8_*.html`
+ `static/js/panel8.js`, following the Phase C pattern):
- **Component A — Universe Table**: `instrument_metadata` LEFT JOIN with the
  latest grade (`emiten_grade` per `MAX(as_of)`). Columns: ticker/sector/market,
  `lane` badge (TRADE green/BOTH blue/INVEST gray/NONE dashed), quadrant badge
  (INVESTABLE/WATCH/SPECULATIVE/AVOID, "—" if not yet graded), `fund_score`,
  count of active flags. `GET /api/universe`.
- **Component B — Issuer Detail** (wave 2, prerequisite J-4+J-11):
  `GET /api/emiten/<ticker>` combines metadata+8 quarters of fundamentals
  (or fewer + `LOW_CONFIDENCE`)+sector benchmark+grade+active flags. Bank
  playbook: `is_financial=1` → display CAR/NPL/NIM/LDR, **HIDE**
  DER/net-debt-EBITDA (replace, not add). The only write in this
  component: `POST /api/emiten/<ticker>/override` (`{quadrant, reason}`,
  `reason` mandatory non-empty) → `save_grade_override()` — the original
  machine value remains visible, the override displays with a separate
  marker.
- **Component C — Candidate Intake**: **wave 1** (J-14, can start now) —
  metadata form (`POST /api/intake` → `save_intake_metadata()`), **guard at
  the write-function level** (not just the UI): `lane` from the intake path
  may ONLY be `INVEST`/`NONE`, `TRADE`/`BOTH` explicitly rejected (mirrors
  the assert in `test_seed_universe.py`), `lane_validated_at` always NULL.
  **Wave 2** (J-15) — manual fundamentals + integrity-check button (scraper
  J-11a) + run-grade button + Giel's recorded decision into a new table
  **`intake_log`** (`id, instrument, decided_at, decision, reason TEXT NOT
  NULL, grade_snapshot JSON, created_at` — the intake counterpart of
  `prediction_log`, `CREATE TABLE IF NOT EXISTS`).
- **Component D — Grader Log & Calibration** (wave 2): `GET
  /api/grader_log` (per-instrument history) + an "Outcome Score" widget
  (identical pattern to the Panel 6 "Prediction Score" widget) → `POST
  /api/grader_log/<id>/outcome` → `save_grader_outcome()`. UI reminder:
  revising rubric weights ONLY through this log, not case-by-case.

**Deliberately NOT included in Tab 8**: earnings calendar (home is Panel 3),
chart/signal/approve-reject (home is Panel 5), per-issuer persona analysis
(home is Panel 4, the RIVAN slice reads `fundamentals_quarterly` via prompt
v5 later).

**2-wave build order:**
```
J-14 (CAN START NOW, no need to wait for gate/grader):
  Tab 8 shell (partial+JS+nav) · Component A (GET /api/universe + table +
  lane badge) · Component C v1 (intake form + lane guard) · Panel 5: LANE
  badge in the per-instrument chart header
J-15 (prerequisite: J-4 fundamentals + J-11 grader engine complete):
  Full Component B (+override) · Full Component C (manual fundamentals+
  integrity check+grade run+intake_log) · Component D (grader_log+outcome) ·
  Panel 5 QUADRANT badge · Panel 3 earnings_calendar on the timeline + warning
  for ONGOING positions approaching earnings
```

**Already done (doesn't need Giel's input first):**
- [x] **Schema `instrument_metadata`** (contract §3, complete) — 1 row per
      equity/index/fx/commodity instrument outside core BTC/macro. Key
      fields: `lane` (TRADE/INVEST/BOTH/NONE, Gate G1), `lane_validated_at`
      (audit trail of bar-replay validation before promotion to TRADE),
      `lot_size`, `has_daily_limit` (ARA/ARB for IDX), `has_real_volume`
      (false for FX/Gold spot — range/ATR proxy).
- [x] **`trading_journal` extension**: `planned_size`/`actual_size` (lot
      quantization audit), `skip_reason` (RISK_CAPACITY_EXCEEDED etc.),
      `return_asset_ccy`/`return_idr` (dual P&L for USD assets).
- [x] **`policy_tracker` extension**: `+sector_tags` (JSON, filters the LEON
      slice per issuer sector).
- Column migration via `db/connection.py::_migrate_columns()` (same pattern
  as Track B) — tested against the real DB, 178 tests still green (2 table
  count tests in `test_db.py` adjusted from 14→15).
- **NOT built yet** (referenced in the contract as "unchanged from v1.1" —
  the v1.1 document containing the full DDL was NOT given to me, so its
  structure was NOT guessed): `fundamentals_quarterly`, `earnings_calendar`,
  `sector_benchmark`, `emiten_grade`, `grader_log`, and the concrete
  extension of `asset_context_weight` (the contract only narratively says
  "inheritance index → sector → instrument", not yet turned into columns).
  Need the v1.1 document or a re-description before it can be built.
- [x] **G3 Prototype (yfinance `.JK` fundamentals)** — tested live against 3
      candidates (BBCA.JK, BBRI.JK, TLKM.JK, chosen as a data-source test
      sample, NOT a universe decision). Findings:
      - `quarterly_financials`/`quarterly_balance_sheet`/`quarterly_cashflow`
        are available via yfinance, data looks reasonable (e.g. BBCA Net
        Income Q1 2026 ≈ Rp14.68 trillion, BBRI ≈ Rp15.49 trillion, TLKM ≈
        Rp4.34 trillion) — BUT **only ~4-5 quarters back are available,
        not 8** as targeted for J4 — matches EXACTLY the scenario the
        contract itself already anticipated ("if only 4 → grade runs with
        LOW_CONFIDENCE flag").
      - `info["sector"]`/`info["industry"]` use GICS/English terms
        (e.g. "Financial Services"/"Banks - Regional"), NOT the IDX-IC
        classification — needs a manual mapping if IDX-IC becomes the
        standard.
      - Bank ratios CAR/NPL/NIM/LDR are **NOT PRESENT** in any yfinance
        line item (checked the full balance sheet) — confirming that
        contract J7 was already correct in flagging that this needs a
        separate source (OJK/bank reports), not yfinance.
      Giel can use these findings directly for manual validation of the 3
      issuers against official reports (Gate G3 requirement) — no final
      decision has been made here, just supporting research.

**Update — Gates G1/G2/G3 ANSWERED by Giel (13 Jul 2026):**
- **G1 (lane + SOP v4.1 amendment)**: ✅ **approved** ("amendment OK") —
  the per-instrument `lane` model officially replaces the old binary
  trade-vs-invest question. There isn't a separately written SOP v4.1
  amendment text yet, but the decision in principle is already locked —
  enough to proceed substantively with J-0b (the `lane` field has been
  used as-is since the Phase J+ kickoff).
- **G2 (initial universe)**: ✅ **NOT 15-30 tickers as in the original
  contract draft** — Giel decided the initial universe is JUST **BBCA
  (IDX) + TSLA (US)**, the rest added manually one at a time via
  scrape/intake (Panel 8) later, not a big batch at once.
  `pipeline/seed_universe.py` updated (TSLA added, market_cap/free_float
  data from yfinance checked live: mcap ≈$1.53T, free float ≈69.91%,
  sector "Consumer Cyclical/Auto Manufacturers"). `lot_size=1` (US, not
  100 like IDX), `has_daily_limit=0` (LULD minute-based circuit-breaker,
  NOT daily ARA/ARB), `fx_exposure="global"`, `accounting_std="US_GAAP"` —
  explicitly different from BBCA in every market-relevant field.
- **G3 (fundamentals source)**: ✅ **yfinance OR direct IDX, both
  accepted** — there's no single decision forcing one source; Giel
  accepts yfinance as the default (already prototyped for G3 earlier for
  BBCA/BBRI/TLKM) with the option to switch to a direct IDX source if
  needed. This opens up J-4 (fundamentals_quarterly backfill) — NOT done
  in this update, next turn's task.

**Impact on build order**: J-0/J-1 (seed universe) is NOW **complete** for
the decided scope (BBCA+TSLA, not "can't run yet without G2" as before) —
J-2 (OHLCV) automatically runs for TSLA too without code changes
(`scrapers/equity_universe.py` reads `instrument_metadata` dynamically, see
the J-2 entry above), verified live: `equity_TSLA = ok` in
`pipeline.run_daily`, 508 rows of history (2024-07-01..2026-07-12) via
`pipeline.backfill`, TSLA appears in Panel 8 Universe & (once selected) the
Panel 5 chart. **J-3 (per-market calibration + bar-replay validation)** is
still NOT automated work — contract §13.1 point 5 still requires manual
validation per instrument before `lane_validated_at` is filled in, that's
Giel's own decision via historical chart review, not something I can decide
unilaterally.

**Update — J-4 complete (fundamentals_quarterly backfill, BBCA + TSLA):**
- [x] **`scrapers/fundamentals_yf.py`** (NEW) — yfinance `quarterly_
      financials`/`quarterly_balance_sheet`/`quarterly_cashflow`, real
      fields checked live first (not guessed) before mapping: `Total
      Revenue`→revenue, `Net Income`→net_income, `Diluted EPS` (fallback
      `Basic EPS`)→eps, `Stockholders Equity`→total_equity, `Total
      Assets`→total_assets, `Operating Cash Flow`→operating_cash_flow,
      `Free Cash Flow`→free_cash_flow (a direct row, not computed manually
      from capex). **Important finding**: yfinance has a `Net Interest
      Income` row even for TSLA (non-bank) — this is NOT genuine bank
      NIM, so the `net_interest_income` column is deliberately gated by
      `instrument_metadata.is_financial` (only filled if `is_financial=1`),
      not taken raw from yfinance as-is. Quarters where both revenue AND
      net_income are NaN are skipped (not stored as 0).
- [x] **`pipeline/backfill_fundamentals.py`** (NEW) — `upsert_
      fundamentals_quarterly()` by natural key (instrument, quarter_end,
      UNIQUE constraint already in the schema), `backfill_fundamentals()`
      processes 1 instrument or ALL in `instrument_metadata`. Run
      manually/periodically (fundamentals change per-quarter, NOT part of
      the daily `run_daily`) — same pattern as `seed_universe.py`.
      `python -m pipeline.backfill_fundamentals` (all) or
      `--instrument BBCA` (one).
- 9 new tests (`test_fundamentals_yf.py` + `test_backfill_fundamentals.py`,
  live network, same pattern as other scrapers — including an explicit
  assert that `net_interest_income is None` for all TSLA rows, and filled
  for at least 1 BBCA quarter), 201 tests green total. **Fully verified
  live against the real DB**: `python -m pipeline.backfill_fundamentals` ->
  BBCA 5 quarters, TSLA 5 quarters, BOTH `LOW_CONFIDENCE` (as expected per
  contract §16 point 2 and the earlier G3 prototype finding — yfinance
  really only gives ~5 quarters, not 8). BBCA's Q1 2026 Net Income
  (≈Rp14.68 trillion) **matches exactly** the earlier G3 prototype finding
  before the Phase J+ kickoff — a data consistency cross-check.
- **Not done yet** (outside the pure "data backfill" scope of J-4):
  `sector_benchmark` computed from this data (J-5), using this data in
  Panel 8 Component B (J-15, prerequisite Grader module J-11 doesn't exist
  yet), the RIVAN prompt v5 slice reading fundamentals (J-9).

**Update — J-3 groundwork (uncalibrated first pass, NOT final validation):**
Giel answered "just do it, I'll review later when I try BBCA and TSLA" — so
it was run without waiting for per-market calibration (§13) to finish
first, BUT `lane_validated_at` DELIBERATELY STAYS NULL (that validation is
Giel's own manual decision via chart review, not something decided
automatically here).
- **Important finding**: `pipeline/run_analysis.py::run_analysis(instrument)`
  **has ALREADY been generic since Phase B** — no code change was needed
  AT ALL. `INSTRUMENTS` (the default list when no `--instrument` given) is
  only used by `main()`, the core function accepts ANY instrument present
  in `asset_ohlcv`. Ran directly: `python -m pipeline.run_analysis
  --instrument BBCA` and `--instrument TSLA`.
- **Live results**: BBCA — 488 rows of history, 12 new zones (10 active), 16
  new signals. TSLA — 508 rows of history, 13 new zones (11 active), 12
  new signals. All `approved=0` (hardcoded in `insert_signal_dedup`, no
  other path writes to `trade_signals` — confirmed with a direct query: 0
  rows `approved=1` for BBCA/TSLA). `instrument_metadata.lane` remains
  `INVEST`, `lane_validated_at` remains NULL for both — confirmed
  unchanged.
- **Important discipline note**: the schema.sql comment for `instrument_
  metadata.lane` says "only lanes TRADE/BOTH have trade_signals generated
  for them" — that is a FUTURE rule NOT YET enforced anywhere in the code
  today (there's no `lane` check before generating a signal). Running the
  engine for lane=INVEST instruments here is actually INTENTIONAL —
  that's the whole point of J-3 (give Giel material for bar-replay review
  before `lane_validated_at` can be filled in). Once J-3b/official lane
  gating is enforced in code later, this rule needs revisiting so it
  doesn't conflict with this kind of review flow.
- Verified live in the browser: Panel 5's BBCA dropdown shows 16 rows in
  the Signals table (status "pending" for all, Approve/Reject buttons
  work the same as BTC), S&R zones drawn on the chart (9/10 zones relevant
  to the current price).
- **Not done yet** (the actual §13 calibration): per-price-fraction S&R
  zone tolerance for IDX, ARA/ARB buffer, loose-vs-tight retest parameters
  per market — the signals/zones above use the SAME GENERIC parameters as
  BTC, NOT the result of specific calibration. Giel's bar-replay review of
  this data will determine whether these generic parameters are enough or
  need adjusting before the lane can be promoted to TRADE.

**Update — J-3b complete (sizing & lot quantization engine, §14):**
- **Giel's decision (13 Jul 2026)**: max risk per trade = **2.5%**.
- [x] **`analysis/sizing.py`** (NEW) — `suggest_position_size(entry_price,
      sl_price, capital, lot_size, max_risk_pct=2.5)`: risk budget
      (capital × 2.5%) ÷ entry-SL distance = ideal units → **round DOWN**
      to a multiple of `lot_size` (`lot_size<=0` = full fractional, IBKR
      US — not rounded at all). If the budget < 1 lot →
      `skip=True, skip_reason='RISK_CAPACITY_EXCEEDED'` (contract §14
      point 2). **No parameter or path whatsoever to move the SL** — this
      module only accepts `sl_price` as a fixed input, never proposes
      changing it (contract §14 point 3, "strictly forbidden").
      `MAX_RISK_PCT = 2.5` module constant (same pattern as `MIN_RR = 1.5`
      in `analysis/signals.py`) — regression-guarded via an explicit test
      so it doesn't silently change.
- **`capital` is DELIBERATELY not stored/guessed in code** — Giel's real
  capital is private & can change, so it's filled in manually via `.env`
  (`RISK_CAPITAL_IDR`/`RISK_CAPITAL_USD`, empty placeholder added to
  `.env.example`, segmented per contract §13.2 "funded from the USD Jago
  segment") — the caller (journal/route, not yet built) reads that env
  value and passes it as an explicit argument to the function.
- 8 new tests (`test_sizing.py`) — including a regression guard for
  `MAX_RISK_PCT == 2.5`, IDX round-down (exact and inexact multiples),
  `RISK_CAPACITY_EXCEEDED` skip when budget < 1 lot, US fractional rarely
  skips (contract §14 point 5), and the `actual_risk <= risk_budget`
  invariant across various number combinations (contract §14 point 1,
  "never the other way around"). 209 tests green total.
- **Not done yet** (outside the "pure engine" scope): wiring into the
  UI/route (e.g. Panel 5's "Approve" button showing the suggested size),
  populating `trading_journal.planned_size`/`actual_size`/`skip_reason` —
  that's J-13 (final SOP amendment), needs an additional decision from
  Giel about the confirmation flow in the dashboard, not just the
  calculation.

**Update — J-10 complete (seed asset_context_weight for BBCA/TSLA):**
- [x] `pipeline/seed_context_weight.py` — `BBCA_WEIGHTS` (ihsg_foreign_flow
      HIGH, bi_rate HIGH, usd_idr MED, sector_fundamentals MED) & `TSLA_
      WEIGHTS` (fed_path HIGH, earnings HIGH, net_liquidity MED, dxy MED) —
      drivers different from the generic BTC/FOREX weights, reflecting the
      character of an IDX bank vs a US growth stock. `level` still
      defaults to `'INSTRUMENT'` (NOT YET built: the full
      index→sector→instrument inheritance from contract §3 — that needs a
      separate fallback-lookup design, outside the scope of the manual
      J-10 seed). 4 new tests, run live: 4 new rows for BBCA/TSLA
      respectively in the real DB.

**Update — J-7 complete (earnings_calendar, BBCA + TSLA):**
- [x] **`scrapers/earnings_yf.py`** (NEW) — yfinance's `Ticker.earnings_dates`
      (needs a new dependency `lxml`, added to `requirements.txt` —
      without it yfinance silently raises `ImportError` behind a
      try/except in pandas, discovered live on the first try). Fields
      more complete than `Ticker.calendar` (which only gives 1 upcoming
      date with no surprise history): `EPS Estimate`/`Reported EPS`/
      `Surprise(%)` per date, history + 1 row for earnings NOT YET
      released (`Reported EPS=NaN` → mapped to `eps_actual=None`).
- [x] **`db/schema.sql`**: `idx_earnings_calendar_dedup` UNIQUE(instrument,
      earnings_date, event_type) — NEW (the table previously had no index
      at all), `CREATE UNIQUE INDEX IF NOT EXISTS` idempotent for
      old/new DBs, doesn't need `_migrate_columns()` (that's only for
      `ALTER TABLE ADD COLUMN`, not indexes).
- [x] **`pipeline/backfill_earnings.py`** (NEW) — `upsert_earnings_
      calendar()` UPSERT by natural key (forecast/actual updated on
      re-run, NOT a duplicate row — important since `eps_actual` goes
      NULL→filled once earnings are officially released). `backfill_earnings()`
      for 1 instrument or all in `instrument_metadata`. Run
      manually/periodically (not part of `run_daily`), same pattern as
      `backfill_fundamentals.py`.
- 9 new tests (`test_earnings_yf.py` + `test_backfill_earnings.py`, live
  network — including an explicit assert there's a row with
  `eps_actual=None` AND a row with `eps_actual` filled, and an upsert
  re-run test that fills in actual without duplication), 219 tests green
  total. **Fully verified live against the real DB**: BBCA 25 rows, TSLA
  25 rows of earnings history — **BOTH instruments have earnings NOT YET
  released on the SAME date: 2026-07-22** (9 days from today, 13 Jul
  2026) — directly relevant to the locked SOP rule "no hold through
  earnings" (contract §18 decision #3, full version for US stocks).
- **Not done yet** (outside the "data backfill" scope of J-7): display in
  Panel 3's timeline (combined visually with `econ_calendar`), a WARNING
  for `trading_journal.outcome='ONGOING'` positions approaching earnings —
  that's J-15 (prerequisite J-4 already done, just need the J-11 grader +
  its UI left).

**Update — J-11 complete (Emiten Grader Module, DRAFT v1):**
> ⚠️ **DRAFT rubric, not Giel's final spec** — the source document "v1.1"
> containing the official rubric (fund_score weights, complete flag list)
> was NOT available when this module was built. Composed from the
> contract's general concepts (two axes: fund_score × integrity flags →
> quadrant), the same pattern as the 5 Phase J+ tables previously also
> marked draft. **Correct anytime it diverges from Giel's actual rubric.**
- [x] **`analysis/grader.py`** (NEW, pure function) —
      **Axis 1 fund_score (0-100)**: 4 components @25 points each from the
      LATEST quarter of `fundamentals_quarterly`, different criteria for
      banks (`is_financial=1`: net_income>0, net_interest_income>0,
      net_margin>0, equity>0) vs non-banks (revenue>0, net_margin>0,
      operating_cash_flow>0, free_cash_flow>0). **Bug found & fixed while
      writing the test**: net_margin = net_income/revenue could
      incorrectly come out "positive" if BOTH are negative (e.g.
      -500M/-1 = a large positive number) — guarded to only be valid when
      `revenue > 0` (not just `!= 0`).
      **Axis 2 integrity_flags**: `UMA_ACTIVE` (RED, from the new
      scraper), `NEGATIVE_NET_INCOME`/`NEGATIVE_EQUITY` (RED, directly
      from fundamentals), `LOW_CONFIDENCE_FUNDAMENTALS` (ORANGE, quarters
      <8). **Quadrant**: any RED flag → **AVOID** (absolute veto, "the
      grader is a BRAKE not a rubber stamp" — contract §16), then
      INVESTABLE (score≥70, no flag) / WATCH (40-69, or ≥70 with ORANGE) /
      SPECULATIVE (<40). Empty fundamental data (not yet graded) →
      SPECULATIVE, NOT AVOID (empty ≠ an active red flag, must not be
      equated).
- [x] **`scrapers/idx_uma.py`** (NEW, J-11a) — the idx.co.id UMA news page
      as the source: **SSR (server-rendered)**, DIFFERENT from the
      "Financial Data and Ratio" page that failed to be researched in a
      previous session (client-side) — 1 GET request directly gets the
      full `__NUXT__` payload containing 1115+ PDF announcement
      references, WITHOUT needing to interact with filters/JS. File
      naming pattern confirmed live: `YYYYMMDD-UMA_<TICKER>.pdf` /
      `YYYYMMDD-WAS_UMA_<TICKER>.pdf`. `is_recently_flagged()` — a
      CONSERVATIVE heuristic (90-day window, WAS_ entries STILL counted
      since the official semantics of "UMA resolved" isn't confirmed) —
      an explicit assumption, revisit if Giel has official clarity on the
      semantics.
- [x] **`pipeline/run_grader.py`** (NEW, J-11b/c/d/e orchestrator) — reads
      the LATEST fundamentals + live UMA per instrument → `grade_emiten()`
      → **APPEND** to `emiten_grade` (grade history, not overwrite) +
      **`grader_log` is ONLY added to if the quadrant CHANGES** from the
      previous grade (anti-overtuning, explicitly tested: running twice
      on the same data → `grader_log` doesn't grow a row, `emiten_grade`
      still appends).
- 26 new tests (`test_idx_uma.py`, `test_grader.py`, `test_run_grader.py`)
  — including a regression test for the net_margin bug above, RED-flag
  veto vs high score, and anti-overtuning of grader_log. 245 tests green
  total. **Fully verified live against the real DB**: BBCA & TSLA both
  come out `fund_score=100, quadrant=WATCH` (held back from INVESTABLE by
  the `LOW_CONFIDENCE_FUNDAMENTALS` flag — 5 quarters of data, not 8), no
  `UMA_ACTIVE` for either (makes sense, blue-chip). Panel 8 browser: the
  Quadrant/Score/Flags columns are NOW filled with real data (previously
  "not graded yet"/`-`), no console errors.
- **NOT yet automated (J-11a follow-up, more research needed)**: the
  special monitoring board (the `daftar-efek-pemantauan-khusus` page turned
  out to be JS-client-side like financial-ratio, not SSR like UMA — failed
  to be researched the same way) and 12-month suspension history (J8-J10
  of the contract) — scraper NOT built yet, a flag for this, if there is
  one, can be entered manually via the `extra_flags` parameter in
  `grade_emiten()`.
- **Not done yet** (outside the "pure engine" scope of J-11): the
  `emiten_grade.giel_override` column (mentioned in Addendum A §19.2
  Component B but not yet in schema.sql — gap found during research, needs
  to be added when J-15 is built), Panel 8 Component B/D UI (issuer
  detail + grader log view, J-15), the "Outcome Score" widget for
  grader_log at 3/6 months.

**Update — J-12/J-15 Component C Wave 2 complete (full intake workflow):**
- [x] **Table `intake_log`** (schema.sql, NEW) — the intake counterpart of
      `prediction_log`: `instrument, decided_at, decision
      (UNIVERSE/WATCHLIST/REJECT), reason TEXT NOT NULL, grade_snapshot
      JSON, created_at`. Total tables 20→21, `EXPECTED_TABLES` +
      `test_db.py` adjusted.
- [x] **`web/writes.py::save_intake_decision()`** — guard at the function
      level (not just the UI): `decision` must be one of
      UNIVERSE/WATCHLIST/REJECT, **`reason` MUST be non-empty** (raises
      `ValueError` if not) — contract §16: "an issuer that comes in
      because of hype/recommendation is precisely the one that most needs
      the integrity flag, the grader is a BRAKE not a rubber stamp."
      `list_intake_log()` for history.
- [x] **3 new routes in `web/app.py`** — `GET /api/intake/integrity_check`
      (reuses `scrapers.idx_uma`, READ-ONLY, writes nothing), `POST
      /api/intake/grade` (reuses `run_grader()` EXACTLY from J-11, not
      separate logic — writes to `emiten_grade`/`grader_log` the same as a
      regular run_grader call), `POST /api/intake/decision` +
      `GET /api/intake/log`.
- [x] **Panel 8 UI**: new section "Candidate Feasibility Test (Wave 2)" —
      ticker input + 3 sequential buttons (Check Integrity → Run Grade →
      Record Decision with a dropdown + mandatory reason textarea), + an
      "Intake Decision History" table.
- 3 new tests (`test_web_writes.py`: empty reason rejected, unknown
  decision rejected, normal insert+list), 248 tests green total.
  **Fully verified live via browser**: the 3-step flow tried end-to-end
  for BBCA — Check Integrity → "clean (no recent UMA)", Run Grade →
  "score=100, quadrant=WATCH, flags=[LOW_CONFIDENCE_FUNDAMENTALS]" (matches
  the J-11 result), Record Decision → appears in the Intake Decision
  History table with the grade snapshot attached. Test data cleaned from
  `intake_log` after verification (the `emiten_grade` row from the
  re-grade was left in place — that's genuine history, not test junk,
  `grader_log` confirmed to NOT gain a row since the quadrant didn't
  change).
- **Not done yet**: a manual fundamentals form (n quarters, `source=
  'manual'`) mentioned in contract §19.3 wave 2 — currently a candidate's
  fundamentals must already exist via `backfill_fundamentals` (yfinance)
  before "Run Grade" is useful; if a candidate isn't listed/isn't
  available in yfinance, a separate manual input path is needed (not yet
  built).

**Update — J-13 complete (sizing engine wired into the Trading Journal, §14):**
- [x] **`web/writes.py::insert_trading_journal()` extended** — 5 new
      OPTIONAL parameters (backward-compatible): `planned_size`,
      `actual_size`, `skip_reason`, `return_asset_ccy`, `return_idr`
      (columns already existed in the schema since contract §3, just
      needed to be wired up).
- [x] **`GET /api/sizing/suggest?instrument=X&entry=&sl=`** (NEW) — reuses
      `analysis.sizing.suggest_position_size()` (J-3b) EXACTLY, no
      separate logic. **2-layer guard** (not just calculate and go):
      (1) the instrument MUST exist in `instrument_metadata` (lot_size
      known) — if not, 404 with a clear message ("the sizing engine only
      applies to the Phase J+ universe"); (2) capital is read from `.env`
      (`RISK_CAPITAL_IDR`/`RISK_CAPITAL_USD`, chosen automatically from
      `instrument_metadata.market`) — if empty, 400 with a clear message,
      **NO fabricating numbers**.
- [x] **Panel 6 Trading Journal form**: a "Calculate Size" button (calls the
      endpoint above, fills in `planned_size` automatically or shows the
      SKIP reason) + 3 new fields (Planned Size/Actual Size/Skip Reason,
      all can also be filled in manually to override the engine's
      suggestion).
- [x] **Panel 7 History > Trading Journal**: a new "Size (Plan/Actual)"
      column — shows a SKIP badge if there's a `skip_reason`, not just two
      empty numbers.
- 2 new tests (`test_web_writes.py`: sizing fields saved correctly, skip
  without size), 250 tests green total. **Fully verified live end-to-end
  in the browser**: (1) `/api/sizing/suggest` for BBCA (in the universe)
  BUT `RISK_CAPITAL_IDR` not yet filled -> a clear error message, no
  made-up number; (2) `/api/sizing/suggest` for BTC (not Phase J+) -> 404
  with a clear message; (3) fill in `planned_size`/`actual_size` manually
  -> saves to `trading_journal` -> shows up correctly in Panel 7 as
  "2500 / 2500". Test data cleaned up after verification.
- **Not done yet**: `return_asset_ccy`/`return_idr` (dual P&L for USD
  assets, contract §13.2) has no UI input yet — the field already exists
  in the DB/write function, just needs to be added to the form
  if/when Giel actually starts trading TSLA and needs to record P&L;
  auto-computing from the sizing engine (auto-filling `planned_size` when
  approving a signal in Panel 5, not just manually in Panel 6) also isn't
  built yet — currently the flow is still 2 separate steps (approve in
  Panel 5, calculate+record size manually in Panel 6).

**Update — RISK_CAPITAL_IDR/USD default placeholder (Giel's decision:
"create the field but you set up a default value"):** `.env`/`.env.example`
filled in with `RISK_CAPITAL_IDR=100000000` (Rp100 million) &
`RISK_CAPITAL_USD=10000` ($10k) — **PLACEHOLDER VALUES, NOT anyone's real
capital**, clearly marked in comments so Giel can replace them once he
knows the exact numbers. The sizing engine now works out-of-the-box
(checked live: `suggest_position_size` with the placeholder capital for
BBCA produces a reasonable number), without Giel needing to open .env
first.

**Update — J-6 complete (bank prudential ratios CAR/NPL/NIM/LDR, MANUAL):**
- [x] **4 new columns in `fundamentals_quarterly`** (`car`, `npl_gross`,
      `nim`, `ldr`) — NOT a separate table, still "1 row per instrument per
      quarter" (consistent with the existing table), migrated via
      `_COLUMN_MIGRATIONS`.
- [x] **`web/writes.py::save_bank_ratios_manual()`** — UPSERT by
      (instrument, quarter_end) that **ONLY touches the 4 ratio columns**,
      NEVER overwrites revenue/net_income/etc. OR the `source` column of
      an existing row from the yfinance backfill — explicitly tested (test
      + live verification: BBCA 2026-03-31 row from yfinance, manually
      fill CAR/NPL/NIM/LDR, `source` stays "yfinance" not overwritten to
      "manual"). This function is SEPARATE from
      `upsert_fundamentals_quarterly` (J-4) by design — the automated
      scraper never touches these 4 columns at all.
- [x] **2 new routes** `POST`/`GET /api/fundamentals/bank_ratios`.
- [x] **Panel 8 UI**: input form (ticker+quarter+4 ratios) + a per-ticker
      history table.
- 3 new tests (`test_web_writes.py`: new insert, no clobbering a yfinance
  row, list only quarters that have ratios filled), 253 tests green
  total. Verified live: saved dummy ratios for BBCA 2026-03-31 (row
  already existed from yfinance) -> `source` stays "yfinance", the 4
  ratio columns filled correctly in the table. Test data (dummy numbers,
  NOT real BBCA ratios) cleaned up (nulled out again) after verification —
  the original row (revenue etc.) untouched.
- **Note**: the form does NOT validate `is_financial=1` at the backend
  level (could be filled in for a non-bank instrument if Giel mistypes
  the ticker) — if this becomes a real problem, add a guard similar to
  `save_intake_metadata()` in a future session.

**Update — J-15 Component B/D complete (issuer detail, override, grader log):**
- [x] **Schema**: `emiten_grade.giel_override` (TEXT JSON, the column that
      was flagged as a "gap" in the J-11 update — now added),
      `grader_log.outcome_3m`/`outcome_6m`/`outcome_notes` (NEW, for the
      Outcome Score widget). Migrated via `_COLUMN_MIGRATIONS`.
- [x] **`web/writes.py::get_emiten_detail()`** — a combination of
      instrument_metadata + last 8 quarters of fundamentals + latest grade
      (integrity_flags & giel_override parsed from JSON).
- [x] **`save_grade_override()`** — guard: `quadrant` must be one of the
      4 official quadrants, `reason` MUST be non-empty. **The machine's
      ORIGINAL quadrant (`quadrant`) is NEVER overwritten** — the override
      is stored separately in `giel_override`, both shown together in the
      UI (explicitly tested + verified live: BBCA override becomes
      INVESTABLE, the `quadrant` column in the DB stays WATCH).
- [x] **`list_grader_log()` + `save_grader_outcome()`** — the 3-month/6-month
      outcomes are independent (COALESCE, filling one doesn't clear the
      other — explicitly tested).
- [x] **4 new routes**: `GET /api/emiten/<ticker>`, `POST /api/emiten/
      <ticker>/override`, `GET /api/grader_log`, `POST /api/grader_log/
      <id>/outcome`.
- [x] **Panel 8 UI**: "Issuer Detail" section (metadata+grade+override
      form, **bank playbook from contract §12.1 applied** — `is_financial=1`
      shows CAR/NPL/NIM/LDR, HIDES the generic revenue/OCF/FCF that's less
      relevant for banks) + "Grader Log & Calibration" section (a table
      with an inline outcome dropdown per row).
- 9 new tests (`test_web_writes.py`), 262 tests green total. **Fully
  verified live via browser**: BBCA's detail displays correctly with bank
  columns (not the generic revenue), the override to INVESTABLE saves
  with the machine quadrant (WATCH) still visible side by side, the
  outcome dropdown widget works (select PARTIAL -> saves, appears in the
  table). Test data (dummy override + outcome) cleaned up after
  verification.
- **With this, J-15 (Addendum A §19) is ENTIRELY COMPLETE** — Component
  A (J-14), C Wave 1 (J-14) & 2 (J-12), B & D (this turn) all now exist.

**Update — J-8 complete (foreign flow, turned out to be PER-STOCK not just
per-sector — more detailed than what the contract asked for):**
- **Research**: the first attempt (guessing the urlName of the "Digital
  Statistic" API that worked for Track C) FAILED — consistent with the
  earlier "special monitoring board"/"financial ratio" dead-ends. **The
  correct endpoint was found by observing a REAL BROWSER's network
  requests** (navigate to the official IDX "Stock Summary" page, read the
  network request that actually fires) — not guessing again. Endpoint:
  `https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=9999&start=0`
  — a DIFFERENT family from "Digital Statistic" (`primary/DigitalStatistic/...`)
  used by Track C. **No session-cookie warmup needed** (different from
  `idx_foreign_flow.py`) — 1 GET directly returns 200. Confirmed live: 965
  stocks, including BBCA (`ForeignBuy`=105,752,900, `ForeignSell`=120,664,900
  shares, 2026-07-10) — a VOLUME field (shares), NOT a Rupiah value like
  Track C.
- [x] **`scrapers/idx_stock_foreign_flow.py`** (NEW) —
      `fetch_idx_stock_foreign_flow(tickers)`, generic (accepts a list of
      tickers, doesn't read its own DB — different from
      `equity_universe.py`, consistent with the more generic scraper
      pattern in this project). 3 metrics per ticker output:
      `stock_ff_foreign_buy_vol`/`sell_vol`/`net_vol`.
- [x] **Wired into `pipeline/run_daily.py`** — reads tickers with
      `market='IDX'` from `instrument_metadata` (dynamic, automatically
      picks up new IDX stocks added to the universe), calls the scraper,
      merges into the existing `upsert_
      positioning` (natural key dedupe automatic, NO new write path).
- **NO new UI code** — the `positioning` table is ALREADY generic, Panel 3
  automatically displays these new rows once they exist (the exact same
  pattern as Track C).
- 5 new tests (`test_idx_stock_foreign_flow.py`, live network + guard for
  empty ticker list = skip the network call), 267 tests green total.
  **Fully verified live**: `pipeline.run_daily` -> `idx_stock_summary = ok`,
  3 BBCA rows go into `positioning` with numbers EXACTLY matching the
  manual research finding (net = -14,912,000, net = buy - sell validated),
  automatically shows up in `/api/positioning` without changing the
  endpoint or Panel 3 at all.
- **Coverage note**: this is PER-INSTRUMENT, not a per-sector aggregate as
  literally requested by contract J-8 — considered BETTER (can be
  aggregated to sector any time if needed, granularity can't go the other
  way). The endpoint has no date parameter (always the LATEST trading
  day) — history/backfill for past dates NOT built yet (outside this
  turn's scope, if needed a J-2-style backfill would need fresh research
  into whether this endpoint has a way to pull history).

**Update — kickoff continuation (Giel said "okay go ahead", fill in BBCA
only for now):**
- [x] **5 Phase J+ tables built as DRAFT** (`fundamentals_quarterly`,
      `earnings_calendar`, `sector_benchmark`, `emiten_grade`, `grader_log`)
      — because the original v1.1 document wasn't available, the columns
      were composed from the gap analysis §1 + data requirements §2 +
      yfinance G3 research, NOT Giel's final spec. Clearly marked in the
      `schema.sql` comments so it's easy to correct if it diverges from
      the real v1.1. `asset_context_
      weight` extended with `+level` (INDEX/SECTOR/INSTRUMENT, weight
      inheritance) — old rows auto-backfilled to `INSTRUMENT` (the only
      level that existed before this concept, not left NULL). Total
      tables 14→20. 3 table-count tests in `test_db.py` adjusted.
- [x] **`pipeline/seed_universe.py`** (new, same pattern as
      `seed_context_weight.py`) — manual seed of `instrument_metadata`,
      idempotent (`INSERT OR REPLACE` by `instrument` PK). First **BBCA**
      entry: `lane='INVEST'` (NOT `TRADE` — contract §13.1 point 5, a new
      instrument must be INVEST/NONE first until the J-3 bar-replay
      validation is done, `lane_validated_at` deliberately NULL),
      `is_financial=1`, `lot_size=100`, `has_daily_limit=1` (ARA/ARB),
      market_cap/free_float data from yfinance `.JK` (checked live, will
      go stale over time — metadata fields change slowly, unlike
      daily_market which is refreshed on every run). `avg_volume_20d`
      deliberately NULL — this field should be computed from real
      `asset_ohlcv` history (J-2, not yet running for BBCA), not a
      one-time snapshot approach from yfinance's `info`.
- 3 new tests (`test_seed_universe.py`, including an explicit assert
  "a new instrument must not default to TRADE"), 181 tests green total.
- **Backlog recorded (Giel's explicit request)**: a manual input system in
  the dashboard for `instrument_metadata` (a UI form, not editing
  `seed_universe.py` directly each time an issuer is added) — NOT built
  yet, this seed script is the temporary substitute until the UI exists.

**Update — J-14 complete (Tab 8 Wave 1, Addendum A §19.5):**
- [x] **Panel 8 "Universe" (NEW)** — `web/templates/partials/panel8_universe.html`
      + `web/static/js/panel8.js`, nav tab 8 in `index.html`.
      **Component A** (universe table): `GET /api/universe` ->
      `web/writes.py::list_universe()` — `instrument_metadata` + the
      LATEST grade per instrument from `emiten_grade` (a correlated
      subquery by `MAX(graded_at)`, not a window function — consistent
      with this project's SQL style). Quadrant/score show "not graded
      yet"/`-` until the Grader module (J-11) runs — not a bug, just no
      data yet.
      **Component C v1** (intake metadata): `POST /api/intake` ->
      `save_intake_metadata()` — **guard at the function level** (not just
      the UI): lane may ONLY be `INVEST`/`NONE`, `TRADE`/`BOTH` raises
      `ValueError` (endpoint returns 400) — mirrors the
      `test_seed_universe.py` assert pattern. `INSERT OR REPLACE` by
      `instrument` PK (idempotent, same pattern as `seed_universe.py`).
- [x] **Panel 5: LANE badge** in the chart header (`#instrumentLaneBadge`) —
      `GET /api/instrument_meta?instrument=X` -> `get_instrument_meta()`.
      The badge is **hidden** (not empty-error) if the instrument has no
      `instrument_metadata` row — applies to all existing macro/index
      assets (BTC/GOLD/IHSG/SP500/USDIDR/USDJPY, not yet in the Phase J+
      universe), lane is only relevant for individual stocks.
- [x] **CSS**: 4 new badge modifiers (`lane-trade` green/`lane-both`
      blue/`lane-invest` gray/`lane-none` dashed-border) in
      `static/css/dashboard.css`, `LANE_CLASS` map alongside `LENS_LABELS`
      in `core.js` (used by Panel 5 & Panel 8, not duplicated).
- 6 new tests in `test_web_writes.py` (lane guard reject, insert+upsert
  idempotent, join latest grade, no-grade-yet, get_instrument_meta
  found/missing), 187 tests green total. Verified live via browser: BBCA
  shows up in the Universe table with real data, the intake form saves a
  new instrument (`ZZZTEST`, lane INVEST, cleaned up after verification),
  the Panel 5 badge is empty for BTC (no row) and correctly renders `LANE
  INVEST` when called manually for BBCA (BBCA isn't in the Panel 5
  instrument dropdown yet since the J-2 OHLCV backfill hasn't run for
  individual stocks yet).
- **Component B/D + the Panel 5 QUADRANT badge + Panel 3 earnings** remain
  J-15, prerequisite J-4 (fundamentals) & J-11 (grader engine) — NOT
  worked on in J-14 (outside Wave 1 scope per contract §19.5).

**Update — J-2 complete (universe OHLCV -> asset_ohlcv, dynamic yfinance):**
- [x] **`scrapers/equity_universe.py`** (NEW) — different from
      `scrapers/macro_yf.py`: the universe is read DYNAMICALLY from
      `instrument_metadata` on every run (not a hardcoded dict), so
      adding a new issuer via Panel 8 intake does NOT need a scraper code
      change. `yf_ticker_for(instrument, market)`: IDX -> `.JK` suffix,
      US (and others) -> ticker as-is. Writes ONLY to `asset_ohlcv` (not
      `daily_market` — an individual stock isn't global macro context,
      Master Plan §4). Every instrument in `instrument_metadata` is
      fetched (including lane INVEST/NONE, not just TRADE) — price
      history is still needed for the upcoming J-3 bar-replay validation.
- [x] **Wired into `pipeline/run_daily.py`** — `fetch_equity_universe(date,
      db_path)` called alongside the other scrapers, `asset_rows` merged
      into the existing pipeline upsert (no new write path, reuses
      `upsert_asset_ohlcv`).
- [x] **`pipeline/backfill.py` extended** — an instrument not known in
      `YF_TICKERS`/`FRED_INSTRUMENTS` (hardcoded macro) now falls back to
      checking `instrument_metadata`: if present, the ticker is derived
      dynamically via `yf_ticker_for()` then reuses the existing
      `_yf_history_range()`.
      `python -m pipeline.backfill --instrument BBCA --from .. --to ..`
      works directly with no new entry needed anywhere in the code.
- 4 new tests (`test_equity_universe.py`, live network same pattern as
  other scrapers — `yf_ticker_for()` unit test + a live
  `fetch_equity_universe()` test for BBCA), 191 tests green total.
  **Fully verified live**:
  `pipeline.run_daily` -> `equity_BBCA = ok` in source_flags, a real row
  goes into `asset_ohlcv` (2026-07-10, close 6175); a 2-year CLI backfill
  (2024-07-01..2026-07-12) -> 486 new rows; Panel 5 browser -> BBCA
  APPEARS in the instrument dropdown (automatic, `/api/assets` generic
  since Phase C), the candlestick chart renders 299 SVG elements with real
  data, the LANE INVEST badge shows correctly in the chart header.
- **Coverage note**: the Panel 1 "Manual Backfill" HTML dropdown is still
  hardcoded to macro instruments (BTC/DXY/SP500/IHSG/Gold/USD-IDR) —
  backfill for Phase J+ instruments (BBCA etc.) runs via the
  `pipeline.backfill` CLI, NOT via the Panel 1 UI. Adding Phase J+
  instruments to the dropdown isn't part of J-2 (outside contract scope),
  recorded as a potential UX follow-up.
- **`volume_ma20`** remains NULL for the BBCA backfill rows
  (`backfill.py` doesn't recompute that column, unlike `run_daily` which
  explicitly calls `volume_ma20_for_instrument` on every run) — this
  does NOT block anything right now (Panel 5's chart computes the MA
  itself client-side from raw OHLCV; `analysis/*` doesn't yet include
  BBCA in the `INSTRUMENTS` list, that's part of J-3).

**Evaluated, deliberately not done:**
- **J-6: Bank ratios CAR/NPL/NIM/LDR via IDX** — Giel asked "how about
  IDX" as an alternative to OJK. Research was done (not assumed): (1)
  WebSearch confirmed IDX has a "Financial Report and Ratio of Listed
  Companies" page on the same Digital Statistic system already used for
  the foreign-flow API (Track C); (2) researching the open-source
  NeaByteLab/IDX-API project's source code found a `syncFinancialRatio()`
  module — BUT the fields it mentions are only **PER/PBV/ROE/DER**
  (general market valuation ratios), NOT bank prudential ratios
  (CAR/NPL/NIM/LDR); (3) directly trying several `urlName` API guesses
  (`LINK_TABLE_FINANCIAL_RATIO` etc., same pattern as the foreign-flow
  endpoint) — all returned 503 (not 404, the correct endpoint really
  hasn't been found yet); (4) trying via a real browser (filling in the
  month/year filter + clicking "Apply" on the official page) also failed
  to trigger the API's network request (likely server-side Nuxt
  resolution, not a client-side fetch that can be intercepted).
  **Conclusion**: specific bank prudential ratios are MOST LIKELY not
  data published at the exchange's (IDX's) "general ratio" level —
  that's usually a regulatory disclosure owned by OJK (`ojk.go.id`,
  Indonesian Banking Surveillance Report, found in the same research).
  **Still Backlog** — OJK is the most likely candidate source, not
  researched further yet (outside this turn's scope). Recorded here so
  the "IDX urlName for financial ratio" research isn't repeated from
  scratch without a new reason.
- **NewsData.io** — checked directly: sentiment analysis is **only
  available on the Professional/Corporate (paid) tier**, not the free
  tier as originally thought. The historical archive (10 years) is also a
  paid feature. The free tier (200 credits/day) is just an extra RSS
  aggregator with no real sentiment. Judged not worth the integration
  effort vs. the added value. Decided to **skip**.
- **NewsAPI.org** — free tier is "non-commercial only" (conflicts with the
  Phase 2/3 monetization plans in the Master Plan), and historical depth
  is only ~1 month. Skip.
- **Net exchange flow (BTC)** — checked: Glassnode/CryptoQuant really are
  **paid** for this metric (as noted earlier), and there's no free
  substitute of comparable quality. This metric needs a database of
  labeled, continuously maintained exchange addresses (who owns which
  address) — that's exactly the paid value proposition of
  Glassnode/CryptoQuant, not just access to blockchain data (which is
  public/free). Available options, all less than ideal:
  - **Dune Analytics** (free) — some community dashboards replicate
    CryptoQuant-style netflow via SQL queries over indexed on-chain data,
    but this is "using/adapting someone else's query" not a stable REST
    endpoint — a different integration shape from every other scraper in
    this project.
  - **DIY** (maintain your own list of exchange addresses + query a chain
    indexer) — high effort, data quality below paid vendors, not worth it
    for a personal dashboard. **Still Backlog** — no free path currently
    worth the effort.
  - **Update (tried Giel's paid CryptoQuant API key, verified LIVE)**: the
    key is valid (other endpoints like `market-data/price-ohlcv`
    succeeded with 200 + real data), BUT the entire `exchange-flows`
    category (`netflow`, `inflow`, `outflow`, `reserve`, etc. — 6
    endpoints all tried) returns 403 "no authority for this request". Not
    a free-vs-paid issue anymore — the CryptoQuant plan Giel currently has
    doesn't cover this category at all, likely needing a higher
    tier/separate add-on (entitlement granularity is per-endpoint, not
    neatly per-tier — `open-interest` is also 403 even though it's
    equally "market-data" like the `price-ohlcv` that works). No
    workaround (trying to compute manually from inflow−outflow also hits
    a wall, both are 403). **Giel decided to drop it** — not worth
    pursuing further. Still Backlog.
- **Whale / long-term holder (LTH) accumulation (BTC)** — same story, Coin
  Metrics has a free "Community" tier, BUT the specific age-band/LTH-split
  metric (`SOPRLth`, realized cap by coin age, etc.) turns out to be
  gated behind the "Network Data Pro" (paid) tier — the free tier doesn't
  cover it. The only genuinely free proxy that could be used:
  - **Whale Alert API** (free tier) — a real-time feed of individual large
    transactions (e.g. "$X moved from wallet A to exchange B"). This is a
    proxy for **whale movement**, NOT the actual "LTH supply accumulating"
    metric (a different concept: individual transfer vs. UTXO age
    analysis), but the direction is related (a whale moving funds
    to/from an exchange). The free tier's exact rate limit hasn't been
    confirmed — needs checking the official docs if it's ever used.
    **Still Backlog** — if a rough proxy is wanted later, Whale Alert is
    the most realistic choice, not a genuine LTH metric.
  - **Update**: also tried via Giel's CryptoQuant API key (the
    `network-indicator/utxo-age-distribution` endpoint, an LTH/STH proxy
    via UTXO age) — 403 same as `exchange-flows` above, not included in
    the plan owned. **Giel decided to drop** this along with the item
    above — not worth pursuing further. Still Backlog.

**Update — J-3: ARA/ARB sizing buffer (§18 decision #4, LOCKED) + price
fraction zone tolerance (§13.1 point 4, DRAFT) complete (13 Jul 2026):**
- **ARA/ARB 1.5× buffer** (`analysis/sizing.py`) — `suggest_position_size()`
  takes a new parameter `has_daily_limit: bool`. If `True` (read
  automatically from `instrument_metadata.has_daily_limit`, not manual user
  input), the SL distance is multiplied by `ARA_ARB_BUFFER_MULT = 1.5`
  before being used to calculate position size — shrinking
  `suggested_units` so real risk doesn't exceed budget if the price gaps
  past the SL when hit by ARA/ARB (an auto-rejected order on IDX, unlike
  the US's LULD circuit-breaker which can still be closed out). This is a
  **§18 locked** decision, not a draft — no further Giel revision needed.
  The `/api/sizing/suggest` API response now includes
  `nominal_risk_per_unit` (the original SL distance, unbuffered) alongside
  `risk_per_unit` (already buffered) — Panel 6 (`panel6.js`) explicitly
  shows both when the buffer is applied ("ARA/ARB 1.5x buffer applied:
  nominal distance X → Y") so Giel can see the calculation transparently,
  not just the final number. 3 new tests (`test_sizing.py`), verified
  live: BBCA (`has_daily_limit=1`) correctly shows nominal 100 →
  buffered 150 in the Panel 6 browser.
- **Price fraction (tick size) zone tolerance** (`analysis/calibration.py`,
  new file) — the official table from BEI Regulation No. II-A (confirmed
  via WebSearch, not guessed): price <Rp200 → Rp1 fraction; Rp200-500 →
  Rp2; Rp500-2k → Rp5; Rp2k-5k → Rp10; ≥Rp5k → Rp25.
  `idx_zone_tolerance_pct()` computes the S&R clustering tolerance as a
  relative percentage (`fraction × 2 ticks ÷ reference price`) — **DRAFT**,
  `IDX_ZONE_TOLERANCE_TICKS = 2` still needs Giel's confirmation/revision
  after bar-replay validation per §13.1 point 5 ("an engine tested on BTC
  ≠ tested on BBRI"), DIFFERENT from the ARA/ARB buffer above which is
  already final. `pipeline/run_analysis.py::run_analysis()` checks
  `instrument_metadata.market` — if `'IDX'`, tolerance is computed from
  the LATEST close via this function; other instruments (all existing
  macro/index: BTC/GOLD/IHSG/SP500/USDIDR/
  USDJPY, no `instrument_metadata` row) still use the default
  `CLUSTER_TOLERANCE` of 0.5% exactly as before — **guaranteed zero
  regression** (verified both via code inspection and re-running the
  existing test suite before adding new tests). `upsert_sr_zone()` takes
  the `tolerance` that is the SAME one used by `detect_zones()` so
  `zone_bucket_key()` stays consistent across re-runs (no drift). The
  summary dict + `_print_summary()` show the actual tolerance percentage
  with a note "(IDX calibration, DRAFT)" vs "(default)". 4 new tests
  (`test_calibration.py`) + 2 new tests (`test_run_analysis.py`,
  regression guard for non-IDX + assert IDX tolerance correctly used),
  276 tests green total. **Verified live**: `python -m pipeline.run_analysis
  --instrument BBCA` -> tolerance 0.816% (25×2÷6175, matching BBCA's real
  price ~Rp6175), 0 new zones (existing buckets still match, no drift);
  `--instrument TSLA` -> stays at the 0.500% default (not IDX, unaffected
  entirely).

**Update — Lane validation / bar-replay sign-off mechanism complete (13 Jul
2026, contract §13.1 point 5):** Giel's review was "No need, I'll review
directly from Panel 5" for bar-replay prep material (no special tool
needed) — BUT he still needs **a path to record the result** of that review
once done, because `instrument_metadata.lane`/`lane_validated_at`
previously had NO UI/API at all to write it (only fillable manually via
direct `sqlite3`, not scalable & no audit trail). Built:
- **New table `lane_validation_log`** (`db/schema.sql`, append-only, same
  pattern as `intake_log`/`grader_log`) — `evidence TEXT NOT NULL`, a
  trail of instrument/old_lane/new_lane/validated_at per decision.
  `db/connection.py`'s `EXPECTED_TABLES` + `tests/test_db.py` updated
  (21 → 22 tables).
- **`web/writes.py::validate_lane()`** — the ONLY path allowed to change
  `instrument_metadata.lane` / fill `lane_validated_at`. Guarded at the
  function level (not just the UI, same pattern as
  `save_intake_metadata`/`save_grade_override`): `evidence` mandatory
  non-empty, `new_lane` must be one of TRADE/INVEST/BOTH/NONE, returns
  `None` if the instrument doesn't yet exist in `instrument_metadata`
  (must be intaken first). NEVER called automatically by any
  `run_analysis`/`seed_universe`/backfill — purely a manual action via the
  form. `list_lane_validation_log()` for history, with optional
  per-instrument filter.
- **New routes** `POST /api/emiten/<ticker>/validate_lane` +
  `GET /api/lane_validation_log` (`web/app.py`).
- **New Panel 8 UI** (`panel8_universe.html`/`panel8.js`): a "Lane
  Validation (Bar-Replay Sign-off)" section (ticker + new-lane dropdown +
  mandatory evidence textarea) + a "Lane Validation History" table
  (columns for old→new lane + evidence), wired into `refreshAll()` in
  `main.js`.
- 7 new tests (`test_web_writes.py`: reject unknown lane, reject empty
  evidence, return None if not yet intaken, correctly updates metadata +
  logs evidence, filter log per instrument), 281 tests green total.
  **Verified live** via browser (a direct fetch, not clicking the form, so
  as not to touch the real BBCA/TSLA judgment): intake a disposable
  `ZZTEST` ticker → validate to TRADE with evidence → check the log
  recorded correctly → **cleaned back out of the production DB** (0 rows
  left, confirmed by query). BBCA & TSLA REMAIN `lane=INVEST`,
  `lane_validated_at=NULL` as before — the mechanism is ready, but the
  actual bar-replay decision remains entirely Giel's, not fabricated here.

**Update — J-9 data plumbing + draft equity slice prompt (13 Jul 2026):**
Giel asked to "go ahead" on 3 things at once (bar-replay validation, §13
calibration, the J-9 prompt) — for J-9, this was again split into
"mechanism" (can be built) vs. "voice/prompt wording" (must be Giel
himself, same as the earlier decision in Track D that the persona prompt is
Giel's own way of thinking).
- **Data plumbing** (`pipeline/compose_persona_context.py`) —
  `_equity_fundamentals_lines()` (fundamentals_quarterly + emiten_grade +
  the J-8 per-stock foreign-flow, per instrument in `instrument_metadata`)
  and `_earnings_calendar_lines()` (earnings_calendar J-7, its intended use
  for AKELA was already explicitly written in the schema comment since
  J-7 was built) — added to `_slice_rivan()` and `_slice_akela()`. Bank
  instruments (`is_financial=1`) show NII/CAR/NPL/NIM/LDR, non-banks show
  Revenue/NetIncome/FCF + a `confidence` flag (FULL/LOW_CONFIDENCE). Grade
  shows quadrant+score+Giel's override (if any, the ORIGINAL still
  visible alongside). GEMA/LEON are UNTOUCHED (slice discipline,
  consistent with the existing IHSG foreign flow pattern). 9 new tests
  (`test_compose_persona_context.py`), 287 tests green total. **Verified
  live** against the production DB: the RIVAN slice shows BBCA (bank,
  CAR/NPL/NIM/LDR still `n/a` since not yet manually filled by Giel, NII
  filled from yfinance, grade WATCH score=100, foreign flow -14,912,000
  shares) + TSLA (Revenue/NetIncome/FCF filled, confidence=LOW_CONFIDENCE,
  grade WATCH score=100); the AKELA slice shows BBCA & TSLA earnings
  2026-07-22 with forecast EPS.
- **The prompt text itself has NOT been changed** — drafted separately in
  `docs/j9_equity_slice_prompt_draft.md` (a proposal, NOT written into
  `prompts/persona_rivan.txt`/`persona_akela.txt` which are gitignored/
  Giel's personal IP). The draft proposes giving RIVAN an explanation of
  the equity data + guidance that "a grade isn't a final verdict", and
  giving AKELA an explanation of the earnings date as a scheduled event
  risk. GEMA/LEON are deliberately not proposed to change at all. It's
  Giel's call whether to use it, edit it, or discard it.

**Update — Panel 1 "Check & Backfill All Gaps" (14 Jul 2026):** Giel pointed out
that the existing gap-detection system (`/api/data_gaps`, per-instrument dropdown)
is already informative — the question was why you still have to pick instruments
one by one when the system already knows everything that's missing. Built:
- **`web/app.py::_all_instruments_with_gaps(conn)`** — a pure function (DB-only,
  no network) that detects gaps for ALL instruments at once: macro
  (`INSTRUMENT_SOURCE`, 13 instruments) + the Phase J+ equity universe
  (`instrument_metadata`, WEEKDAY calendar). Instruments with no history at all
  (`total_rows=0`) are SKIPPED on purpose — that's an initial backfill that needs
  a conscious decision (which instrument, from what date), not an automatic
  "fill the gap". The `WEEKLY_WED` calendar is also skipped (same pattern as
  `/api/data_gaps`).
- **`POST /api/backfill/all/preview`** — uses the function above to find
  candidates, then calls `backfill_mod.backfill(..., preview_only=True)` (real
  network fetch) per instrument for its own gap range. Instruments that fail to
  fetch have their error recorded, WITHOUT stopping the other instruments (same
  pattern as the scraper's `safe_call`).
- **`POST /api/backfill/all/commit`** — commits ONLY the items that were already
  previewed (body `{"items": [...]}`, not a re-detection) — avoids drift if the
  gap changes between the 2 requests, request/response symmetric with the
  existing single-instrument flow.
- **Panel 1 UI** (`panel1_snapshot.html`/`panel1.js`) — new "Check & Preview All
  Gaps" button below the existing Manual Backfill form, renders a table of
  instrument/gap-range/new/duplicate + a "Commit All (N instruments)" button.
  After commit, `loadDataGaps()` is called again so the gap info for the
  currently selected dropdown also gets refreshed.
- 5 new tests (`test_web_app.py`, DB-seeded, no network — mirrors the existing
  `_detect_gaps` pattern): macro gap, skip instrument with no history, skip the
  WEEKLY_WED calendar, include the equity universe (WEEKDAY), no-gap → empty
  result. 292 tests total green. **Verified live against the production DB**:
  preview found a real BTC gap (2026-07-11 through 2026-07-12, 2 rows), commit
  wrote 2 new rows (4,316→4,318), the BTC gap-info dropdown auto-refreshed to
  "no gap detected" — the data written is REAL (not dummy, no need to clean up).

**Update — FE migration to Vue 3 + Vite, Phases 0-2 complete (14 Jul 2026):**
Giel asked to "run all FE build phases" following the plan in
`docs/migrationFE.md` (parallel app + strangler cutover, prior decision: Vue 3 +
Vite + PrimeVue, chart wrapped as-is, backend untouched). Node/npm turned out to
already be installed by Giel himself via nvm before this session (`v24.16.0`);
the Vite+Vue scaffold had also already been run by Giel but nested in the wrong
location (`web/frontend/web/frontend/`, likely run from inside `web/frontend/`)
— moved to the correct location (`web/frontend/`), the already-installed
node_modules were kept.
- **Phase 0** (scaffold): Vue Router (8 routes 1:1 with the old tabs) + Pinia +
  PrimeVue (Aura preset) + dev proxy `/api` → Flask. Verified live: real
  `/api/latest` data loaded through the proxy, SPA routing works.
- **Phase 1** (shared foundation): `src/lib/api.js`, `src/lib/format.js`,
  `src/components/DataTable.vue` (wraps PrimeVue DataTable, used by ~11
  tables), `src/composables/useAppToast.js`.
- **Phase 2** (migration of 8 panels): ALL 8 views done & verified live against
  the production DB (not dummy data) — Snapshot (cards+backfill+backfill-all-
  gaps), News, Forward (the form-heaviest one: inline-edit econ calendar,
  expectations, positioning, policy tracker, dissonance), Reading (persona
  cards + PrimeVue Dialog), Chart (SVG candlestick WRAPPED AS-IS,
  `rollingMA`/`drawCandleChart`/`drawMiniLine` moved to `src/lib/chartMath.js`
  nearly verbatim, migrated LAST per the plan), Synthesis, History (4
  sub-tabs), Universe (the biggest, 8 sub-sections including lane validation &
  grader log). **Bug found & fixed BEFORE production**: `ForwardView` initially
  used 1 shared `ref` for all empty "Actual" econ-calendar inputs — wrong if
  >1 row needs to be filled at the same time (a real case, econ calendars
  commonly have many future events without an actual) — fixed to per-row
  state.
- Live verification covered: switching instrument BTC↔BBCA in Chart (price +
  lane badge change correctly), Issuer Detail for BBCA in Universe
  (bank-specific fundamentals table + LOW_CONFIDENCE flag display correctly),
  DataTable search/sort/paginate, Economic Calendar with actuals already
  filled in vs empty. `npm run build` succeeds (~200KB gzip total, code-split
  per view).
- **Phase 3 (cutover + login) COMPLETE (14 Jul 2026)**. Paused first for
  explicit confirmation from Giel before deleting the old code (see the
  update below) — after being confirmed, fully executed:
  - **Auth**: `@app.before_request` in `web/app.py` rejects (401) all
    `/api/*` except `/api/auth/{login,status}` until `session["authed"]`.
    `DASHBOARD_PASSWORD` must be filled in manually in `.env` — NEVER
    generated/defaulted by code (different from `RISK_CAPITAL_*`, which
    really is a placeholder number; this is a credential, I never
    typed/tested its actual value myself). Empty → login endpoint rejects
    with a clear message. `FLASK_SECRET_KEY` optional. Password is compared
    using `secrets.compare_digest` (constant-time).
  - **Serving**: an SPA catch-all route (registered last) serves
    `web/frontend/dist/` — Flask `/` is now ONE process/port for both API +
    frontend, no separate Vite dev server needed for everyday use.
  - **Vue**: `src/stores/auth.js` (Pinia) + `src/views/LoginView.vue` + a
    router guard (`src/router/index.js`) + automatic redirect to `/login` if
    the session expires (`src/lib/api.js`).
  - The old vanilla code (`web/templates/`, `web/static/` — 8 partial HTML
    files + 10 JS files + 1 CSS) was **deleted**, Giel himself committed it
    (`f7168f2 "Migrate to Vue JS"`), not an auto-commit from me — still
    recoverable via `git show bcfa625:web/templates/index.html` etc. if
    needed.
  - **Verified**: redirect to `/login` when not authenticated, 401 on
    `/api/*` without a cookie, all assets served correctly (network tab:
    200/304, zero 404s), and AFTER Giel filled in the password & logged in
    himself — the sidebar + Logout button + real data displayed correctly
    from the authenticated session. The backend/API + 292 Python tests
    remained completely unchanged throughout this entire process.

**Update — Snapshot: 2 triggers (News + Backfill) + tidy up Manual Backfill
(28 Jul 2026):** Giel asked for "2 triggers" that run now: News (can't be
backfilled for past dates, RSS only serves what's live) and Backfill (market
data, fills gaps for past dates) — kept separate because their purposes
differ, not a duplicate.
- **`POST /api/run_daily_now`** (new) — calls `pipeline.run_daily.
  run_daily()` directly from the "Trigger News (Now)" button in
  `SnapshotView.vue`. Previously Giel had to ask for a manual run via
  terminal every time the WSL cron didn't run (a recurring occurrence, see
  the entry above) — now it can be triggered from the UI itself.
- **Checkbox in "Check & Preview All Gaps"** — the results table now has a
  check column per instrument (all checked by default), the button becomes
  "Commit Selected (N instruments)" — you can uncheck an instrument you
  don't want to commit, no longer all-or-nothing.
- **Manual Backfill per-instrument form REMOVED** (Instrument dropdown +
  From/To date + Preview/Commit) — Giel said it was redundant with "Check &
  Preview All Gaps", which already checks all instruments at once. The
  backend endpoints that became unused were removed too: `GET
  /api/data_gaps`, `POST /api/backfill/preview`, `POST /api/backfill/commit`
  (the `_detect_gaps`/`INSTRUMENT_SOURCE` functions STILL exist, still used
  by `_all_instruments_with_gaps` for the "all gaps" path).
- Verified: 404 Python tests green, `npm run build` clean, the new endpoints
  verified via the Flask test client (temp DB, `run_daily` monkeypatched so
  it doesn't actually hit the network).

**Update — News Threads: the 7-ACTIVE cap lifted (28 Jul 2026):** Giel tried
to activate/create a thread, hit the cap of 7 (decision #5, §20.1 of the
contract) — explicitly asked for the limit to be removed, he wants to decide
himself how many threads there are and which ones are ACTIVE/DORMANT via the
existing status field.
- `MAX_ACTIVE_THREADS` + the COUNT-check guard in `save_thread()`
  (`web/writes.py`) were removed entirely. `patch_thread()` (DORMANT→ACTIVE
  reactivation) never had a similar guard, so nothing changed there.
- Frontend: the text "Maximum 7 ACTIVE threads" + "{{activeCount}}/7 ACTIVE
  threads" in `ThreadsView.vue` was changed to just show the count, no longer
  mentioning a limit. `active_count`/`list_threads_with_stats` are unchanged
  (still useful as info, just no longer a count against a hard limit).
- The old test `test_save_thread_enforces_max_active` was replaced with
  `test_save_thread_no_longer_caps_active_count` (creates 8 ACTIVE threads at
  once, all must succeed).
- `docs/phase_j_build_contract_v1_3_LOCKED.md` §20.1: decision #5's text is
  struck through + annotated (not deleted, its history stays visible).
- Verified: full pytest suite green, `npm run build` clean.

**Update — Mode Ringkas (Quick Mode) & Mobile PWA v1.0 design saved + Step 1
executed (28 Jul 2026):** Giel wrote a full design document
(`docs/mode_ringkas_pwa_mobile_v1.md`) — a 5-minute habit session for busy
days (PART A) + its mobile PWA container (PART B), with a cheap-first build
order (PART C, 5 steps, starting from ZERO code). Guiding principle: this app
is a habit engine, success metric = daily streak, not feature completeness.
- Step 1 (ZERO code) executed: a new section "Mode Ringkas — 5-minute session
  (busy day)" added to `docs/SOP.md` §1 (version bumped 1.1→1.2) — the
  MANDATORY action (log/score 1 prediction), CORE, BONUS, and the list of
  what's NOT in Mode Ringkas, with exactly the same structure as the source
  document.
- Steps 2-5 (the `/m` view, PWA manifest+service worker, light capture,
  native APK) were DELIBERATELY not built yet — each waits for evidence of
  usage from the previous step (the "use-then-build" pattern Giel wrote
  himself), rather than being built all at once up front.

**Update — PWA + `/m` Mode Ringkas built all at once (31 Jul 2026):** Giel
explicitly asked to skip Step 2 (use plain `/m` for 1-2 weeks first) and go
straight to Step 3 (full PWA) — overriding the "use-then-build" order he
wrote himself in `docs/mode_ringkas_pwa_mobile_v1.md`.
- **`web/frontend/src/views/MobileView.vue`** (new, route `/m`) — a single
  vertically-scrolling screen per wireframe §B.2: data-status header
  (source_flags 🟢/🔴), MANDATORY (log/score prediction), CORE (HIGH news +
  for_reading + inline SUGGESTED tag/thread confirmation), BONUS (ACTIVE
  thread summary, click → timeline), ONGOING Positions (crossed with
  earnings warnings). **100% reuse of existing endpoints** (§B.4) —
  `/api/latest`, `/api/prediction/{due,add,score}`, `/api/news`,
  `/api/content_tags/*`, `/api/threads/*`, `/api/journal`,
  `/api/earnings/warnings` — zero new endpoints. Decision endpoints
  (approve, sizing, backfill, settings, run persona) are deliberately never
  called from this view.
- **`App.vue`/`router/index.js`** — `/m` renders standalone without the
  sidebar shell (same as `/login`), not part of the 7 desktop nav groups.
- **PWA** (`vite.config.js`, `vite-plugin-pwa` plugin) — manifest
  (`start_url: /m`, `display: standalone`, dark color matching the theme),
  service worker `registerType: autoUpdate`, `navigateFallbackDenylist` for
  `/api/*` (the SW never caches/serves API responses — data is always fresh
  from the network, this app is installable, not offline-first). Icons
  generated from 1 source SVG (`@vite-pwa/assets-generator`, dev-only tool)
  — the letter "K" over the dark `--bg` color, a full set of 64/192/512 +
  maskable + apple-touch-icon.
- Verified: `npm run build` clean (manifest.webmanifest + sw.js + workbox
  chunk generated), pytest 404 still green (backend untouched at all this
  session), checked directly in the browser (production build via
  `kastara-web`): the manifest served correctly, all four icons 200 OK, the
  service worker script installed, zero console errors up to the login
  page. Could NOT verify the content of `/m` behind it (credential rule) or
  a real home-screen install (needs real HTTPS from a phone, not yet tested
  via Tailscale) — both await Giel trying it himself.

**Update — Track A: Railway deploy scaffolding, staying on SQLite (31 Jul
2026):** Giel decided to deploy to Railway WITHOUT a Postgres migration
(ARCHITECTURE §6.1's "cloud managed" trigger fired, but the app is still
single-user/single-writer, so it's solved with a Railway Volume, not a
database swap) — see `docs/deploy.md` §7 for the full rationale & Railway
checklist.
- **`Dockerfile`** (new, multi-stage) + **`.dockerignore`** (new) —
  `node:22-alpine` builds the frontend, `python:3.12-slim` runtime,
  `gunicorn web.app:app --workers 2 --timeout 300` (the timeout was made
  generous for `/api/run_daily_now`, see the Snapshot 28 Jul entry above).
- **`requirements.txt`** — added `gunicorn`.
- **`web/app.py`** — `init_db()` moved to module level (out of `main()`) —
  MANDATORY because gunicorn imports the module directly and never executes
  `if __name__ == "__main__"`. Without this, an empty Volume on first
  deploy makes the very first API call fail (table doesn't exist yet).
- **`tests/test_web_app.py`** — set `KASTARA_DB_PATH` to a temp file BEFORE
  `from web.app import ...`, because the change above means merely
  IMPORTING this module now triggers `init_db()` — without this guard,
  tests would silently touch the real production DB via Giel's local
  `.env` (found during this session's verification; the real production DB
  did NOT end up changing, since the schema was already fully migrated so
  `init_db()` happened to be an idempotent no-op — but still a latent bug
  that had to be closed, not left alone).
- **`.env.example`** — a note that `FLASK_SECRET_KEY` is now REQUIRED to be
  set explicitly for Railway deploys (optional only for local dev) —
  without this, every redeploy invalidates all login sessions.
- Verified: `docker build` succeeds, `docker run` + an end-to-end smoke test
  (`/` 200, `/api/auth/login` + `/api/auth/status` + `/api/latest` all
  working correctly, authenticated, inside the container), the test image
  deleted after verification. `pytest` full suite still 404 green.
- **Not yet executed** (needs Giel's own Railway account): create project,
  attach Volume, set env vars, first deploy, upload the real DB via
  `railway ssh`, add a second cron service — full checklist in
  `docs/deploy.md` §7.3.

Per `plan.txt`: **don't skip phases without new instructions.** If there's an
urgent need outside the order (like Phase 1 the other day), that's allowed —
but it must be recorded here clearly, explaining why it went out of order, so
the roadmap keeps reflecting reality rather than a stale ideal plan.

**Update — /universe: Step 1, restructuring into 4 tabs (31 Jul 2026):** Giel
wrote a full design document (`docs/universe_portfolio_restructure_v1.md`) —
a diagnosis of why the /universe page is dizzying to read (8 sections mixing
daily/quarterly frequency, 5 standalone ticker-scoped forms, no reading
hierarchy), plus a plan for a Portfolio/Holdings tracker (new component,
Steps 4-6, not yet built). Agreed to execute only Step 1 this session (cheap,
quick relief) — Steps 2-6 (per-ticker drawer, holdings table, allocation vs
SOP, guards) await further instruction.
- **`UniverseView.vue`** restructured into 4 tabs (custom tab-bar, not
  PrimeVue TabView — consistent with the hand-rolled `App.vue` sidebar
  style): Universe (table + Issuer Detail/Override + Lane Validation + Bank
  Ratios — these 4 ticker-scoped sections TEMPORARILY stay here, not yet
  moved to the drawer), Portfolio (placeholder, content to follow in Step
  4), Intake (Intake Candidates + Feasibility Test + Intake Decision
  History), Log & Audit (Lane Validation History + Grader Log). **The
  content of each section was NOT changed at all** — purely regroup +
  reorder, per the explicit constraint of Step 1 in the document.
- Verified: `npm run build` clean, pytest 403 green (1 pre-existing
  unrelated skip). No backend changes this session.
- (Operational note, unrelated to content): found that the `nvm default`
  alias in WSL pointed to a Node version that wasn't installed (`lts/*` ->
  v24.18.1, when only v24.16.0/v20.20.2 were actually present) — that's why
  `npm run build` briefly failed with "command not found" mid-session.
  Fixed with `nvm alias default v24.16.0`. Not a code bug, purely a local
  environment issue.

**Update — /universe: Step 2, Issuer Detail becomes a drawer (3 August
2026):** Continuation of the restructuring
(`docs/universe_portfolio_restructure_v1.md`).
- **`DataTable.vue`** (shared component, used by ~10 other views) — added
  `v-bind="$attrs"` to the internal `PDataTable`, so listeners/attributes
  passed to the wrapper (e.g. `@row-click`, `class`) are forwarded to the
  actual PrimeVue table. This component is multi-root (a fragment), so
  without this, Vue 3's automatic fallthrough attrs get dropped. Fully
  backward-compatible — other views that don't pass extra attrs have
  unchanged behavior (confirmed: props already declared never end up in
  $attrs).
- **`UniverseView.vue`** — the Universe table's `@row-click` now opens a
  `<Drawer>` (PrimeVue, right-side position) containing exactly the content
  of the old "Issuer Detail (Component B)" section (including the Override
  form that had already been attached there since before) — the ticker
  comes automatically from the clicked row, the manual ticker-input field +
  "View Detail" button were removed entirely. Lane Validation & Bank Ratios
  have NOT been moved yet (still standalone sections) — that's Step 3.
  Table rows get `cursor:pointer` (`.clickable-rows :deep(tbody tr)`).
- Verified DIRECTLY in the browser (Giel logged in himself, I only read the
  page afterward — credential rule maintained): clicking the BBCA row opens
  a drawer containing BBCA's metadata/lane/grade/fundamentals/override
  correctly, confirmed by screenshot. Ran into a page cached by the PWA
  service worker (Step 3 Aug, previous session) that served an old bundle
  even after `npm run build` was rerun — fixed by unregistering the SW +
  clearing the workbox cache via the console, not a code bug.
- `npm run build` clean, pytest 403 green (1 pre-existing skip).

**Update — /universe: Step 3, Lane Validation + Bank Ratios move to the
drawer (3 August 2026):** Direct continuation of Step 2 above, same session.
- **`UniverseView.vue`** — the standalone "Lane Validation" and "Bank
  Ratios" sections were removed entirely; their content moved into the same
  drawer as Issuer Detail/Override (below the Save Override button,
  separated by `<hr>` + `<h4>`). Their individual ticker fields were
  removed — `validateLane()`, `saveBankRatios()`, `loadBankRatios()` now
  use `detailTicker` (the drawer's state) as the single source of ticker.
  `openDetailDrawer()` resets `bankRatios`/`lane.evidence` each time a new
  ticker is opened, so leftover data from the previous ticker doesn't
  linger.
  Bank Ratios now **only shows if `detail.metadata.is_financial`** (per §3
  of the docs: "Bank Ratios -> form + history (if bank)") — a new guard
  that didn't exist in the old standalone section.
  The drawer is now the single place for all ticker-scoped actions
  (Summary, Fundamentals, Override, Lane, Bank Ratios) — exactly matching
  the §3 document structure, Steps 2+3 fully complete.
- Verified DIRECTLY in the browser (not just build): clicking BBCA ->
  drawer shows Override + Lane Validation + Bank Ratios (BBCA is a bank,
  all sections appear); clicking TSLA -> drawer switches content to TSLA,
  the Bank Ratios section correctly disappears (checked via
  `document.querySelector` directly, not just the accessibility tree,
  which was briefly stale due to a stuttering CSS transition — most likely
  a browser-pane rendering artifact that wasn't actively rendered at that
  moment, not an app bug).
- `npm run build` clean, pytest 403 green (1 pre-existing skip) — no
  backend changes.
- **Remaining work** (`docs/universe_portfolio_restructure_v1.md` §5): Step
  4 (`holdings` table + form + Per Provider), Step 5 (Allocation vs SOP +
  Per Currency), Step 6 (book/conversion/staleness/journal guards) — the
  Portfolio/Holdings tracker, not yet built, awaiting instructions.

**Update — /universe: Step 4, `holdings` table + form + Per Provider (3
August 2026):** New component, the Portfolio/Holdings tracker (not a
continuation of the tab structure, this is the content of TAB 2 that was
previously a placeholder).
- **`db/schema.sql`** — table #28, `holdings` (universal for all asset
  types: stocks/gold/crypto/mutual funds/forex, same pattern as
  `asset_ohlcv`). `book` (TRADE/INVEST) NOT NULL at the schema level AND
  validated in the write function (a clear error message, not a raw
  IntegrityError). `linked_journal_id` MAY be NULL even if book=TRADE — the
  "TRADE without a journal" flag is Step 6, not a blocker in Step 4.
  `EXPECTED_TABLES` (db/connection.py) + `tests/test_db.py` (27→28)
  updated.
- **`web/writes.py`**: `create_holding()` (guards non-empty
  instrument/provider/unit, book ∈ {TRADE,INVEST}, currency ∈
  {IDR,USD,SGD}, quantity>0) + `list_holdings()` (filter by book/provider,
  hides is_closed=1 by default).
- **`web/app.py`**: `POST /api/holdings`, `GET /api/holdings`.
- **`UniverseView.vue`** Portfolio tab: minimal input form (instrument,
  provider, book, quantity, unit, optional avg_price, currency, optional
  opened_at, optional notes) + a "Per Provider" view (grouped, book badge
  reusing `LANE_CLASS` since the TRADE/INVEST values match
  `instrument_metadata.lane` exactly). A "Not yet built (Steps 5-6)" panel
  was left as an explicit note in the UI itself, not just in the document.
- **Bug found+fixed BEFORE it could reach production**: 4 new tests written
  briefly used `get_connection()` without a path (instead of
  `get_connection(db)`) — meaning they connected to the actual production
  DB, not tmp_path. Caught from a "no such table: holdings" error (the
  test db hadn't been init'd), not from a silent execution against prod —
  but still a correctness bug that had to be closed. Fixed, production DB
  mtime checked before & after (unchanged, confirmed safe).
- Verified DIRECTLY in the browser (Giel restarted his server himself —
  this session also happened to hit the same gunicorn/dev-reload pattern
  — `python -m web.app` doesn't hot-reload, must be restarted manually
  every backend change): submitted a real holding (BTC/Cold Wallet/INVEST/
  0.083 coin/USD, Giel explicitly agreed since this is a dev environment)
  via the form, appeared correctly in "Per Provider" immediately. `npm run
  build` clean, pytest 407 green (1 pre-existing skip).
- **Remaining**: Step 5 (Allocation vs SOP + Per Currency — needs more
  holding data first to be meaningful) & Step 6 (mandatory book guard in
  the UI/locked conversion+reason, staleness indicator >30 days,
  TRADE-without-linked_journal_id flag) — awaiting further instructions.

**Update — /universe: Step 6, book conversion guard + indicators (3 August
2026):** Full completion of the /universe restructuring + Portfolio Tracker
(`docs/universe_portfolio_restructure_v1.md`, Steps 1-6 all complete).
- **`holding_book_conversion_log`** (table #29) — same pattern as
  `lane_validation_log`: the single path to change `book`, a reason is
  required, append-only, `pnl_check` records the outcome of the P&L
  verification during conversion (surfaced, not hidden).
- **`convert_holding_book()`** — blocked if the position is CURRENTLY AT A
  LOSS (avg_price vs the latest close in `asset_ohlcv`, §4.4 "converting a
  book while in the red always carries a motive of avoiding admitting a
  mistake"). If the instrument is NOT tracked in `asset_ohlcv` (physical
  gold, cash, etc.) — P&L can't be verified, the conversion is STILL
  ALLOWED (not blocked by default) but is honestly recorded in `pnl_check`,
  rather than silently assumed profitable.
- **Staleness indicator (🟡, >30 days) + TRADE-without-journal flag (🔴)**
  — purely computed on the frontend from fields already returned by
  `list_holdings()` (`last_updated`, `book`, `linked_journal_id`), zero
  backend changes needed for this.
- **"Mandatory book"** (point 1, §4.4) has been enforced since Step 4 — no
  additional change needed, re-confirmed during the Step 6 audit.
- **`POST /api/holdings/<id>/convert_book`**, **`GET
  /api/holdings/conversions`** + a new "Book Conversion History" section in
  the Log & Audit tab.
- Verified DIRECTLY in the browser (not just tests): the Book Conversion
  drawer opened from the BTC/Cold Wallet row, a reason filled in,
  submitted — book changed INVEST→TRADE, the 🔴 flag appeared immediately
  (since there's no linked_journal_id yet), and the conversion log row
  appeared correctly in the Log & Audit tab with pnl_check "not verified
  (instrument not in asset_ohlcv)" — as expected since BTC genuinely
  doesn't match any instrument in the asset_ohlcv test data at the time.
- 5 new tests (block-while-losing, allow-while-profiting,
  allow-while-unverifiable, 4 guard errors, log ordering+join) + 1
  additional scenario in test_db.py (28→29 tables).
- The backend needed restarting 2 more times during this session (new
  endpoint each time) — the same recurring pattern, noted again so it
  isn't forgotten: `python -m web.app` does NOT hot-reload.

**Update — Addendum F, F-1: Secondary Opinions foundation (4 August 2026):**
`docs/phase_j_build_contract_v1_3_LOCKED.md` §24 (Addendum F) — a
secondary-opinion layer (video/book/paper/podcast) that is SEPARATE from
thread evidence, per the locked decisions F1-F5 in the contract.
- **`secondary_opinions`** (table #30) — `source_type`, `source_ref`,
  `author`, `my_summary` (Giel's distillation, F2 — not a raw transcript),
  `core_claim`, `testable` (TESTABLE/SPECULATIVE, F3), `my_stance`,
  `conflict_of_interest` (F4), optional `thread_id`. `EXPECTED_TABLES` +
  `tests/test_db.py` (29→30 tables) updated.
- **`create_secondary_opinion()`/`list_secondary_opinions()`** in
  `web/writes.py` + `POST`/`GET /api/secondary_opinions` in `web/app.py`.
- **Guard F1 (non-negotiable)**: secondary opinions NEVER count toward a
  thread's stance-composition tally (`thread_stats`) — guaranteed BY
  CONSTRUCTION (separate table, never JOINed by `thread_stats`) AND by an
  explicit regression test
  (`test_secondary_opinion_never_leaks_into_thread_stats`, deliberately
  fills `my_stance` with the text "MENDUKUNG" ["SUPPORTS"] to make sure no
  path mis-reads this column as a stance link).
- **`ThreadDetailView.vue`**: a new "Secondary Opinions" shelf, deliberately
  placed SEPARATE from the "Timeline (CONFIRMED links)" section (§24.3,
  "must not be mixed into the timeline") — a full 8-field form + a list of
  existing opinions per thread.
- Verified DIRECTLY in the browser (Giel logged in manually, credentials
  never handled myself): submitted 1 real video opinion to the "Warsh
  Dovish Regime" thread (thread_id=4) via the UI — appeared correctly on
  the shelf, then `GET /api/threads/stats` was checked AGAIN afterward:
  `composition.MENDUKUNG` ("SUPPORTS") stayed at 4 (the count before the
  opinion was added, unchanged) even though the newly saved opinion's
  `my_stance` deliberately contained the word "MENDUKUNG" ("SUPPORTS") —
  the F1 guard proven to work on real production data, not just in tests.
- 5 new tests (`pytest -q`: 419 passed, 1 pre-existing skip). `npm run
  build` clean.

**Update — Addendum F, F-2: Thread Readability (4 August 2026, same
session):** `docs/phase_j_build_contract_v1_3_LOCKED.md` §24.4 — a thread
readability layer (hierarchy, NOT categories — the contract's explicit
principle: categories fragment the list & break the timeline arc).
- **New field beyond the original F-1 schema**: `secondary_opinions.
  relation_to_view` (ALIGNED/CHALLENGES, optional). The contract's example
  text §24.3/24.4 needs a breakdown like "2 aligned · 1 challenging" per
  thread — this data does NOT exist in the F-1 schema (only free-text
  `my_stance`). Explicitly asked to Giel via AskUserQuestion (rather than
  guessed from `my_stance` via keyword matching — this kind of editorial
  classification needs Giel's decision, not a rule-based guess) — Giel
  chose "add a new field" (not "just a total count"). Nullable migration,
  old F-1 opinions (including the 1 live-test opinion) are automatically
  "not yet classified", not guessed into either side.
- **`news_thread_links`**: 2 new columns, `is_milestone` (manual toggle by
  Giel, Layer 2 §24.4 — NEVER automatic) + `is_backfill` (1 if the link
  originated from `tools/backfill_tag.py`, used for filtering).
  `EXPECTED_TABLES` UNCHANGED (new columns on an old table, not a new
  table) — went into `_COLUMN_MIGRATIONS` in `db/connection.py`.
- **`web/writes.py`**: `thread_opinion_summary()` (total/aligned/
  challenging/unclassified per thread, reuses the F1 guard — reads
  `secondary_opinions` only, never `news_thread_links`),
  `set_link_milestone()`, `suggest_thread_links(..., is_backfill=False)`
  (new param, default False = the daily pipeline path,
  `tools/backfill_tag.py` passes `True`), `thread_stats()` extended:
  `trend_30d` (CONFIRMED composition over the last 30 days, from
  `linked_at`), `shift_warning` (True if the 30-day majority differs from
  the overall majority), `milestone_count`, `opinions` (via
  `thread_opinion_summary`). `list_thread_links()` extended:
  `is_milestone`/`is_backfill` + `tags` (the source news article's tag
  facet — ONLY daily_news/manual_articles, policy_tracker honestly returns
  an empty array since it genuinely isn't taggable, not an error).
- **`web/app.py`**: `POST /api/threads/link/<id>/milestone`; `GET
  /api/threads/<id>` now includes `thread_stats()` directly (the header
  block needs all these fields in 1 request, rather than calling
  `/api/threads/stats`, whose content is for ALL threads).
- **`pipeline/compose_persona_context.py`**: `_thread_opinion_digest_lines()`
  — 1 line per ACTIVE thread whose `persona_tags` match the lens AND that
  has an opinion (threads without an opinion are skipped, not shown as "0
  opinions"). §24.3's hard prohibition is enforced: NEVER send the full
  `my_summary` (only the manual §21.4 path does that), NEVER touch
  `news_thread_links` (F1 preserved).
- **`ThreadDetailView.vue`**: a thread-header summary block (Layer 1,
  exactly matching the contract's format: Evidence/30-day trend + ⚠/
  secondary opinions/age), collapsible monthly `<details>` groups (Layer 3
  — the most recent month open, older ones folded) with a ★ milestone
  toggle per link (Layer 2), stance/tag/milestone-only/backfill-only
  filters (client-side, purely temporary — doesn't change data).
- **DELIBERATELY not built yet**: a narrative title per month group (per
  the contract's example, "Nomination & initial price shock") — needs
  Giel's manual writing per period, there's no field/mechanism for that
  input; monthly groups currently only have counts+composition, not
  narrative. `thread_relations` (§20.1 WAVE 2) remains schema-only.
- Verified DIRECTLY in the browser (restarted the server myself via the
  preview tool since Giel's old process wasn't running anymore; Giel
  logged in manually): the header block displayed correctly ("Evidence: 4
  SUPPORTS...", "Secondary opinions: 1 (0 aligned · 0 challenging) · 1
  unclassified"), toggled the ★ milestone on a real link (thread_id=4) —
  the head block's `milestone_count` immediately rose to 1, the
  "Milestones only" filter immediately trimmed the timeline from 4 links
  -> 1, the tag dropdown filled with real tags (`geo:us`/`org:fed`/
  `theme:inflation`/`who:warsh`) from production data.
- 9 new writes.py tests (is_backfill flag, milestone toggle, tags attach,
  trend_30d/shift_warning/milestone_count, opinion summary,
  relation_to_view validation) + 1 backfill_tag.py test (is_backfill=1
  from the backfill path) + 2 compose_persona_context.py tests (digest
  appears for matching, non-empty-thread lenses, skips empty threads) + 2
  test_db.py tests (new columns). The old F1 guard test
  (`test_secondary_opinion_never_leaks_into_thread_stats`) was updated —
  `opinions` DOES change (that's the point of F-2), but `composition`/
  `trend_30d`/`shift_warning` are still proven frozen. `pytest -q`: 430
  passed, 1 pre-existing skip. `npm run build` clean.

**Update — ThreadDetailView.vue: moved to tabs (4 August 2026, same
session):** Giel asked for the thread page to not require so much
scrolling — 5 sections (Summary, Suggestions, Timeline, Secondary Opinions,
Manual Link) previously stacked vertically on 1 page, the worst being the
"Suggestions" section which could have 86 items with no tabs. Changed to a
tab bar (same pattern as `UniverseView.vue`, an `activeTab` ref + buttons),
tab labels use live counts ("Suggestions (86)", "Timeline (4)", "Secondary
Opinions (1)") so tab content is visible without opening it. Purely
frontend, zero backend/API changes — the `.tab-bar`/`.tab-btn` CSS was
copied into `ThreadDetailView.vue`'s own `<style scoped>` (it was
previously only scoped to `UniverseView.vue`, not automatically shared).
Verified live: build clean, `pytest -q` still 430 passed (no backend logic
changed), clicked between tabs in the browser (a real thread_id=4) — data &
state (filters, previously-set milestone toggles) stayed correct per tab.

**Update — First Railway deploy + correction to the cron plan (4 August
2026):** Giel finished the first Railway deploy. 2 field findings that
corrected the old `docs/deploy.md` §7 plan:
- **Volume wasn't attached** — a first-boot error
  (`sqlite3.OperationalError: unable to open database file`) because a
  Railway Volume turns out to be created via right-clicking the project
  canvas or the Command Palette (Ctrl+K), NOT "Settings -> Volumes" as
  originally assumed — the earlier guidance was wrong, corrected after
  checking the Railway docs directly.
- **The plan for cron via a second service CANNOT BE USED** — checked
  against the Railway docs (`docs.railway.com/reference/volumes`): **one
  Volume can only attach to one service**. A second service for
  `pipeline.run_daily` (the old §7.3 step 7 plan) would automatically need
  its own Volume = a separate, empty SQLite DB, violating the §3.2 "ONE
  DATABASE" rule.
- **Replacement solution**: a 2-way Telegram bot, 1 command (`/run_daily`)
  that triggers `run_daily_mod.run_daily()` on the SAME SERVICE (the one
  that already has the real Volume) — not a separate process/service. New
  endpoint `POST /api/telegram/webhook` (`web/app.py`), exempt from
  session auth (Telegram calls it, not a browser) but gated by chat_id
  (must match `TELEGRAM_CHAT_ID`, silently ignored if different) + an
  optional secret token header (`TELEGRAM_WEBHOOK_SECRET`). The command
  runs on a background thread (Telegram retries if the webhook responds
  slowly, `run_daily()` can take a while) — acks quickly first, the
  summary/error is sent afterward via the existing
  `notify/telegram.py::send_message()` (reused, not a new module).
- **Fresh start** (Giel's decision) — the old local DB was NOT uploaded to
  Railway, it stays as dev data; production starts from an empty
  `init_db()`.
- 4 new tests (`tests/test_web_app.py`): ignore foreign chat_id, ignore
  unknown command, successful trigger (the thread mocked synchronous +
  `run_daily_mod`/`send_message` monkeypatched, not a real network call),
  guard requiring the secret token when configured. `pytest -q`: 434
  passed, 1 pre-existing skip.
- `docs/deploy.md` §7.3 corrected (the upload-DB & second-service steps
  struck through, the reason written explicitly rather than silently
  deleted) + a new §8 (Daily Cron via Telegram) added in full with manual
  setup steps (`setWebhook` once via curl, needs Giel's real token/domain
  — not executed by me, that's a credential/public action).
- **Not yet executed** (needs Giel to run himself): registering the
  webhook with Telegram (the `setWebhook` API call), verifying a real
  `/run_daily` send from his phone once the Railway service is properly
  up.

**Update — Backfilling historical news via on-site search (4 August
2026):** After the Railway deploy, 29 of the local `daily_news`'s 43 days
were empty (the WSL cron didn't run consistently). RSS can't refill past
dates (a rolling "now" window only) — 3 approaches checked DIRECTLY (not
assumed from docs) before building anything, see the plan saved in this
session:
- **Wayback Machine CDX API** — `curl`'d directly against 7 of this
  project's actual feed URLs: nearly zero coverage (1 snapshot from Fed
  FOMC, and even that outside the gap window). Rejected.
- **Paid news API** (NewsAPI.org $449/mo, NewsData.io/Currents/GNews
  cheaper) — none guarantees indexing this project's specific sources
  without paying first to test, and a monthly subscription for a one-time
  gap isn't worth it. Rejected.
- **On-site search per source** — ACCEPTED, live-tested against 2 of 7
  sources (CNBC Indonesia, ANTARA) with real positive results before
  building anything.

**What was built** (`scrapers/news_archive.py`,
`tools/backfill_news_archive.py`):
- **CNBC Indonesia**: a public JSON API `api/v2/search-result` found via
  the Network tab (NOT documented) — the `dtnewsdate` field (real publish
  date) allows accurate range filtering, no headless browser needed.
- **ANTARA Ekonomi**: a server-rendered search page, plain
  `requests`+`BeautifulSoup` is enough (verified live — headlines appear
  in the raw HTML without executing JS). The date in the listing is
  relative text ("3 hours ago"/"5 days ago"/"yesterday"/an absolute
  Indonesian-format date) — parsed to an absolute date via
  `_parse_antara_relative_date()`, day-level accuracy (same precision as
  `daily_news.date`).
- **5 other sources** (Investing ID, Bisnis.com, CNBC Finance/Economy, Fed
  FOMC) DELIBERATELY not added yet — each needs the same live verification
  before assuming it works similarly (CNBC's Market section, for example,
  turned out to be JS-rendered/infinite-scroll when checked).
- Queries use the ALREADY-EXISTING `IMPACT_KEYWORDS` dictionary
  (`scrapers/feeds_config.py`), not a new word list — a targeted subset
  (what this pipeline considers important), NOT a replication of "every
  article that day" (that would need a per-date listing that turned out to
  be JS-rendered, out of scope for this session).
- `tools/backfill_news_archive.py` — a preview→confirm→commit pattern same
  as `pipeline/backfill.py`, `--yes` to skip the prompt, results go in
  through the existing `insert_news_dedup()` (no new insert path).
- 16 new tests (`tests/test_news_archive.py` +
  `tests/test_backfill_news_archive.py`) — including LIVE NETWORK tests
  (same pattern as the existing `test_news.py`, not mocked) for both
  search functions, mocking only for the CLI orchestration tests (dedup,
  one-source-failing-doesn't-stop-others, preview/commit flow) to avoid
  spamming external requests on every test run. `pytest -q`: 450 passed,
  1 pre-existing skip.
- **Verified live, not simulated**: run for real (temp DB, not production)
  against the real gap 2026-06-16..2026-06-24 — **33 real articles found
  across 8 of 9 gap days**. Concrete evidence, not a theoretical claim.
- **EXECUTED against the real local DB** (4 August 2026, `--since
  2026-06-16 --until 2026-07-26`, one call covering all 6 separate gap
  windows — `INSERT OR IGNORE` safely handles days already filled in
  between, 5 of 189 candidates got deduped): **184 new rows into
  `daily_news` (3311 -> 3495)**. Result: 39 of 43 days now have news (up
  from 14 before), the remaining 4 empty days (2026-06-21, 06-27, 07-11,
  07-12) — likely genuinely quiet days for the 26 HIGH/MED keywords used,
  hasn't been tried with broader keywords yet.
- **Not yet executed**: replicating to the Railway DB (fresh-start
  production) — needs an export+re-apply of the same pattern as the
  earlier news/chart migration, whenever Giel is ready. Giel explicitly
  asked for broader scope than just filling the gap ("data is power, maybe
  we can learn from the past") but chose to prioritize the 29-day gap
  first (not pull as far back as possible) — the option to pull further
  back (~6-12 months realistic, NOT all the way to 2010 — the depth of
  CNBC's search API was tested directly: capped at 10,000 results, for
  common keywords that only reaches back ~11 months; ANTARA's pagination
  is also unreliable past ~page 100) remains open if requested later.

**Update — Extend the backfill to January 1, 2026 (4 August 2026, same
session):** Giel asked to go further back. `search_cnbcindonesia` was
upgraded from single-page relevance-sort (`isrelevance=1`, top-20 only) to
tiered date-sort pagination (`isrelevance=0`, verified live to sort cleanly
newest-first) — `page_size`/`max_pages` (default 15, up from 10) replace
the old `limit` param, stopping once a full page is already older than
`date_from`.
- **Real limits tested first before running broadly**: a common keyword
  ("bank indonesia") needs ~7,200 items (360 pages) to reach January — NOT
  REALISTIC. But medium-frequency keywords ("cpi", "earnings") reach
  January with just 300 items (15 pages) — so full coverage per-keyword is
  impossible, but PARTIAL-BUT-REAL coverage via a combination of 21
  keywords is still worthwhile.
- **Run against the real local DB**: `--since 2026-01-01 --until
  2026-06-14` — **516 new rows** (0 duplicates, all candidates new since
  the range had never been touched). `daily_news` is now **2026-01-01
  through 2026-07-27, 4011 total rows** (up from 3495).
- **Final result, 208 days of coverage (Jan 1 - Jul 27)**: 186 days HAVE
  news, 22 days still empty (many likely weekends/genuinely quiet days for
  the 21 HIGH/MED keywords used, not necessarily a scraper failure — not
  yet verified day-by-day which are weekends vs. actually missed).
- Data that's AVAILABLE but NOT YET used (see the response to Giel about
  "what data can be scraped"): the CNBC Indonesia JSON API returns the
  FULL article body (`strisi`, full HTML), author name+profile,
  category/channel, topic tags (`strkeyword_name`), images — this project
  only takes headline+URL+date+summary (the same fields used by the
  original RSS, §22.1 D3 "HIGH only"), deliberately not storing the full
  body (the contract's F2/D2 principle: distillation/extractive, not a raw
  transcript/excessively stored full article).

**Update -- Deep sweep back to 2010 (5 August 2026, same session):** Giel
asked to pull even further back ("pull year by year all the way to 2010
but take it easy. pauses are fine"). Before running, live-probed the
`total` for each of the 21 HIGH/MED keywords directly via the CNBC API —
**8 high-volume keywords hit a hard cap of 10,000 results** (`bank
indonesia`, `fed`, `ihsg`, `inflasi`, `obligasi`, `rupiah`, `suku bunga`,
`the fed`) — 2010 is **provably unreachable** for these no matter how much
`max_pages`/patience is given (a platform limit, not slowness). **The
remaining 13 keywords** (`bi rate`, `cpi`, `earnings`, `etf`, `fomc`,
`gdp`, `inflation`, `nasdaq`, `powell`, `rate cut`, `rate hike`,
`unemployment`, `yield`) have totals well below the cap (123-9530) — a
real chance of reaching 2010, so only these 13 were run (the 8 impossible
ones skipped rather than wasting hours of requests for nothing).
- **Not literally year-by-year**: `search_cnbcindonesia`/
  `search_antaranews` sort newest-first with no absolute per-date offset
  — calling separately per year would mean each year has to re-page
  through all the more-recent years first before reaching the target (e.g.
  reaching 2010 means paging through 2011..2026 first), then repeating
  again from scratch for 2011, etc. — drastically wasteful. Instead ONE
  sweep per keyword was used, from now back to 2010-01-01 (paging stops
  once a full page is already older than `date_from`) — each page is only
  ever requested once, the result still covers all years down to 2010,
  just executed differently from the literal request, not differently in
  coverage.
- **`tools/deep_backfill_2010.py`** (new, one-off) — per-keyword
  checkpointing (commits to the DB after each keyword finishes, rather
  than waiting for all 13x2 sources to finish) so that if the job stops
  partway (network/timeout), progress already saved isn't lost.
  `delay=1.5` seconds between requests ("take it easy", per Giel's
  request), `max_pages` made generous (CNBC 400, ANTARA 100) so paging can
  genuinely reach 2010 for keywords with a large total that aren't yet
  capped (e.g. `nasdaq` total 9530). `tools/backfill_news_archive.py` was
  also upgraded (`--keywords`/`--max-pages`/`--delay`, all optional &
  backward-compatible) so this capability can be reused later via the
  regular CLI, not just a one-off script.
- **Run against the real local DB** (5 August 2026, `python -m
  tools.deep_backfill_2010`, ~13 keywords x 2 sources, 1.5s delay/request):
  **40,016 new rows** (0 failures per-source/keyword, all 13 keywords
  completed). `daily_news` is now **44,027 total rows** (up from 4,011),
  range **2010-01-19 through 2026-08-05**, **3,583 distinct days with
  news**. Sources: CNBC Indonesia + ANTARA Ekonomi (the 2 sources verified
  live on 4 August 2026 — 5 other sources in `feeds_config.py` still
  unverified for this search path). Breakdown per year (rows /
  days-with-news): 2010: 80/69 · 2011: 111/95 · 2012: 19/17 · 2013:
  108/88 · 2014: 69/59 · 2015: 64/58 · 2016: 61/57 · 2017: 149/106 ·
  2018: 3007/331 · 2019: 4300/350 · 2020: 4235/356 · 2021: 4762/351 ·
  2022: 5716/355 · 2023: 5764/359 · 2024: 4908/363 · 2025: 4695/358 ·
  2026: 5979/211. Coverage for 2010-2017 is sparse (low because only 13 of
  21 keywords were used, and older sources likely have fewer articles
  indexed in their own search API to begin with), 2018 and up is much
  denser (>300 days/year, close to full daily coverage).
- **Not yet executed**: replicating to the Railway DB (still fresh-start
  production, see the earlier note) — only the local DB has been enriched
  so far.

**Update -- Migrate Threads/Tags/News to Railway + 2 new Telegram bot
commands (5-6 August 2026):** Giel reported Threads & Tags "missing" on
Railway — after checking, `/api/threads` returns a clean `[]` (not an
error), turns out they'd genuinely never been populated (the initial
Railway fresh-start decision deliberately skipped threads/tags, only
news/chart). Giel asked for them to be migrated.
- **`kastara_migration.json` + `apply_migration.py`** (one-off, not going
  into the permanent repo): a JSON payload (44,027 rows of `daily_news`
  through 2026-08-05, 11 threads, 72 tags, 718 thread_links, 253
  content_tags) uploaded to the Railway container's `/tmp` via `railway
  ssh -- "cat > /tmp/kastara_migration.json"` < file`, then applied via
  `railway ssh -- python3 - < apply_migration.py` (the stdin-pipe pattern
  already proven safe from the earlier `KASTARA_DB_PATH`/"ambiguous
  redirect" incident). `ref_id` in thread_links/content_tags was
  re-resolved via a natural key (date+headline for daily_news, title for
  threads) — NOT copied raw, since local vs Railway ids differ in
  order/value. Idempotent (INSERT OR IGNORE via the existing UNIQUE index)
  — tested run twice against a simulated DB, the second run produced 0 new
  rows in every table. `tag_dictionary`'s `usage_count` was recomputed at
  the end (not just copied) since the migrated content_tags rows didn't go
  through `apply_tag()`.
- **The Telegram bot expanded from 1 command to 3** — Giel had sent
  `/start` and `/status`, which were previously silently ignored
  (`web/app.py:488-492` only matched `/run_daily` exactly, other commands
  fell through to `return jsonify({"ok": True})` with no action). Added:
  - `/start` -- replies with a static help text listing commands (no DB
    query).
  - `/status` -- a new `web/writes.py::telegram_status_summary()`: reads
    the LATEST `daily_market` row (the source for "when did run_daily last
    run", different from `daily_news` which can have zero rows on a quiet
    day) + decodes the `source_flags` JSON into ok/fail counts + the count
    of `daily_news` for that date + the count of `news_thread_links` with
    SUGGESTED status awaiting Giel's review — all from data that ALREADY
    exists, no new table/column.
  - A webhook incident (recorded because it's recurring — a failure
    pattern for this Railway project): `getWebhookInfo` initially returned
    `last_error_message: "Wrong response from webhook: 403 Forbidden"` —
    the root cause was in `web/app.py:479-481`, the
    `X-Telegram-Bot-Api-Secret-Token` header from Telegram didn't match
    Railway's `TELEGRAM_WEBHOOK_SECRET` (likely that var was set but not
    yet deployed, Railway's staged changes don't auto-apply — same as the
    earlier `KASTARA_DB_PATH` incident). Giel chose the simple route:
    re-run `setWebhook` WITHOUT `secret_token` (still gated by the chat_id
    check) rather than debug two values across systems — worked after
    that.
- 7 new tests (`tests/test_web_app.py` 3 new for `/start`/`/status`/
  no-pipeline-data-yet, `tests/test_web_writes.py` 2 new for
  `telegram_status_summary`) — full suite still green.

**Update -- Rebuild the Telegram bot per the "Telegram Bot Commands v1.0"
spec (6 August 2026):** Giel gave a full spec document (version 1.0,
written independently of this session) asking the bot to be rebuilt as
long-polling + a systemd service on a separate VPS (assuming there wasn't
yet an "always-on host"). **A real conflict with the actual state of
things**: the bot was ALREADY running via webhook on Railway (verified
live just now — `/start`/`/run_daily` succeed), and Railway ITSELF is
already an always-on host (that was the point of deploying to Railway in
the first place). Long-polling+systemd needs a 2nd always-running process
— on Railway that means a 2nd service, hitting the EXACT SAME
Volume-only-1-service blocker that killed the separate cron-service plan
on 4 August (§8.0 of deploy.md). Asked Giel via AskUserQuestion before
executing (rather than silently overriding his spec) — **Giel chose: stay
on webhook on Railway, take the relevant parts of the spec** (not build a
new VPS).
- **`web/writes.py::telegram_status_summary()` rewritten** — from 1
  combined date to EACH table checking its OWN latest date (`daily_market`,
  `daily_news`, `asset_ohlcv` can each have a different date, no longer
  assumed to always be in sync — if news is behind but market is ok,
  that's now visible instead of hidden). New fields: `sources_fail_names`
  (names of failed sources, not just a count), `sources_skip`,
  `daily_news_date`/`asset_ohlcv_date` (+ counts for each), `econ_upcoming`
  (`econ_calendar` events >= today), `pending_signals` (`trade_signals`
  WHERE approved=0).
- **`web/app.py` -- multi chat_id allowlist**: new `TELEGRAM_CHAT_IDS`
  (plural, comma-separated), falling back to `TELEGRAM_CHAT_ID` (singular)
  if unset — backward-compatible, does NOT require redeploying the Railway
  env var again (there's already been enough env-var drama this week).
- **Anti-double-run lock + rate limit for `/run_daily`** (§3.2/3.3 of the
  spec) — `RUN_DAILY_LOCK_PATH` (a temp dir, holding PID+timestamp, stale
  after >30 minutes gets taken over, MUST be released via try/finally in
  `_run_daily_via_telegram` so a crashed run doesn't lock forever) +
  `RUN_DAILY_LAST_TRIGGER_PATH` (a minimum 5-minute gap between triggers,
  a different purpose from the lock — prevents SEQUENTIAL spam after a
  previous run finishes, not just overlapping runs).
- **The `/run_daily`-complete message now uses the SAME FORMAT as
  `/status`** (§2 of the spec explicitly asked for this) — rather than a
  separate ad-hoc summary, `_format_status_message()` is used in 2 places
  (DRY, not 2 texts that can drift apart).
- **Other commands (`approve/reject signal`, `backfill`, `settings/grader
  override`) DELIBERATELY still NOT built** — exactly matching §1 of the
  spec ("operations need a gate/conscious ritual, not an idempotent pipe
  operation") — the 3 commands (`start`/`status`/`run_daily`) were the
  only ones implemented from the start, this decision hasn't changed, it's
  just now explicitly documented as matching the spec's risk framework,
  not just "hadn't gotten to it".
- 6 new tests (`tests/test_web_app.py`: multi chat_id allowlist, lock
  blocks double-run, stale lock gets taken over, rate limit blocks) + 2
  existing tests updated (`telegram_status_summary` new fields, new
  /status message format) — full suite still green.
- Docs: `docs/deploy.md` §8.1/§8.2 updated (3 commands, the reason for
  staying on webhook over long-polling, `TELEGRAM_CHAT_IDS` optional).

**Update -- Mobile (`/m`) catches up on 2 features it had missed since
being built (6 August 2026):** Giel asked for `/m` to be compared against
desktop — turned out `MobileView.vue` hadn't been touched since its first
commit (31 July 2026, checked directly via `git log`, not assumed) while 2
waves of desktop features had shipped since: Secondary Opinions F-1/F-2
(`ThreadDetailView.vue`, +292 lines, 3-4 August) & the Portfolio/Holdings
restructuring (`UniverseView.vue`, +608/-141 lines,
`docs/universe_portfolio_restructure_v1.md`, 3 August). Both were added to
`/m` now — NO new endpoints, all reusing existing APIs.
- **The "Active Threads" card**: now shows trend_30d, a ⚠ shift badge if
  `shift_warning` is true, milestone count, opinion summary
  (total/aligned/challenging) — all already available in
  `/api/threads/stats` (`thread_stats()`), just not yet rendered on
  mobile. A "+ Secondary Opinion" button per thread opens a Dialog form (8
  fields, same as desktop: source_type, source_ref, author, summary, core
  claim, testable, stance, conflict_of_interest, relation_to_view) ->
  `POST /api/secondary_opinions`.
- **New "Portfolio" card**: allocation summary (total IDR-equivalent +
  count of unaccounted holdings) from `/api/portfolio/allocation`, a
  holdings list, a "+ Add Holding" form
  (instrument/provider/book/quantity/unit/avg price/currency/SOP
  category/date/notes) -> `POST /api/holdings`. **Decision**: logging a
  new holding is treated the same as logging a prediction (record-keeping,
  not a trading decision) — NOT a violation of the "decision endpoints
  aren't rendered on /m" principle (that's for approving signals, sizing,
  backfill, settings, running the persona — that principle itself remains
  untouched).
- Verification: `npm run build` clean (364 modules, no errors), the dev
  server checked via browser — `/m` correctly redirects to `/login` (auth
  guard works), 0 console errors. **Same as previous sessions: can't
  visually verify the card contents behind login** (credential rule) —
  proven via compile-clean + reading the code directly, not a behind-auth
  screenshot.

**Update -- Bug fix login-redirect + sidebar collapse + 4 follow-up mobile
fixes (6 August 2026, same session):** Giel actually used `/m` from Chrome
on Android, reported back 2 bugs + 2 feature requests.
- **Bug: login ALWAYS lands on `/snapshot`, not back to the original
  destination.** Root cause: the `router/index.js` guard redirects to
  `/login` WITHOUT carrying `to.fullPath`, and `LoginView.vue` hardcodes
  `router.push('/snapshot')`. The effect: opening `/m` from a phone while
  not logged in (e.g. from the PWA icon) ALWAYS lands on the desktop
  dashboard after login — this is the answer to the complaint "why does it
  always redirect to the regular page". Fix: the guard now saves a
  `?redirect=<destination>` query, LoginView reads it & pushes there
  (falls back to `/snapshot` if empty). Verified live: `/m` ->
  `/login?redirect=/m`.
- **Feature: desktop sidebar can now be collapsed** (`App.vue`) — a «/»
  button toggles width between 200px <-> 44px, state persisted in
  `localStorage`.
- **Fix #1+#2 (Giel's report "doesn't work on inactive thread" + "only
  tags shown, need thread too")**: root cause was `MobileView.vue`'s
  `status==='ACTIVE'` filter, which made DORMANT/CLOSED threads NEVER
  appear on `/m` at all (not just dimmed, genuinely gone, no other way to
  reach them from a phone). The "Thread" card now shows ALL statuses —
  ACTIVE full detail (trend/opinions/+Opinion button), non-ACTIVE
  condensed (title+status badge) in an "Inactive" sub-list, still linking
  to `/threads/:id`.
  - **Fix #3 ("can the chart be shown on the dashboard")**: `drawCandleChart`
  extracted from `ChartView.vue` into `lib/candleChart.js` (a shared
  module, purely moved code, no new logic) so `/m` can reuse the EXACT
  SAME candlestick+MA+volume+zone chart without duplicating ~130 lines.
  New "Chart" card on `/m`: an instrument dropdown (default BTC, same as
  desktop) + an SVG that auto-scales to screen width (`viewBox` + CSS
  `aspect-ratio`). Purely read-only — NO approve/reject signal buttons (a
  decision endpoint, the same principle preserved).
  - **Fix #4 ("can all daily news be shown on /m")**: an "All news" toggle
  on the CORE card — still defaults to HIGH-only (the single-screen
  principle unchanged), but 1 tap opens all impact levels (limit raised to
  100).
- Verification: `npm run build` clean (365 modules -- `candleChart.js`
  split into its own 3.98kB chunk used by BOTH `ChartView` AND
  `MobileView`, proof of real reuse not copy-paste), browser-checked `/m`
  unauthenticated -> `/login?redirect=/m` (the redirect fix works), 0
  console errors. **The content of the Chart/Thread/Portfolio cards STILL
  can't be visually verified behind login** (credential rule) — Giel needs
  to check directly on his phone.

**Update -- Diagnosis correction: the real bug is in desktop
ThreadsView.vue, not mobile visibility (6 August 2026, same session):**
Giel used the new Chart/Thread/Portfolio features on `/m`, reported back 2
things.
- **The real bug, "can't save inactive status, can't click save"**: turned
  out to NOT be about `/m` at all (a wrong guess in the previous session)
  — the root cause is in the DESKTOP `ThreadsView.vue`, the inline
  quick-edit form (a Status column + Save button in the table). The
  backend's `patch_thread()` REQUIRES a non-empty `verdict` when
  `status='CLOSED'` (§20.1, "an auditable verdict", the guard already
  existed & was correct from the start) — but the quick-edit form NEVER
  had a verdict field at all (only the separate "Manage Thread" dialog has
  one). The effect: selecting CLOSED in quick-edit, clicking Save ->
  always fails with an error toast that's easy to miss, the form doesn't
  close, the row stays in edit mode — looking like "the button can't be
  clicked" when really the click works but the backend rejects the
  request. Fix: added an inline verdict field (only appears when
  status=CLOSED is selected, same pattern as the Manage dialog), plus
  client-side validation with a clear message BEFORE sending the request
  (not just relying on the backend's error toast).
- **Reverted the "Inactive" section in the `/m` Thread card**: Giel
  explicitly said "no need to show it" — reverted back to ACTIVE-only (the
  `activeThreads` filter; the now-unused `inactiveThreads` computed & the
  `THREAD_STATUS_CLASS` import were removed). To be clear: the earlier
  "inactive doesn't work" complaint was ALWAYS about the desktop Save
  button, not about what's shown on the phone — the initial diagnosis went
  the wrong direction, corrected once Giel gave a more specific detail
  ("can't click save").
- Verification: `npm run build` clean (0 errors). Browser-checking on the
  dev server was blocked by port 5000 being held by an old process
  (`wslrelay.exe`) this session — NOT forced through, since the change is
  purely in a behind-login area that's already been repeatedly verified
  via compile-clean throughout this session; Giel needs to try saving a
  CLOSED status directly on the dashboard to confirm.

**Update -- Real bug: the news date is the SCRAPE date, not the PUBLISH
date (6 August 2026, same session):** Giel reported that the News search
filter appeared to use a "create date" — "news from a few days ago is
treated as today when it gets seeded". Checked: the `/api/news` filter
(date_from/date_to) already correctly queries the `date` column, NOT
`created_at` — but `scrapers/news.py::fetch_all_news()` (used by
`run_daily()`, the DAILY CRON PATH — different from
`scrapers/news_archive.py`, used for historical backfill & which ALREADY
correctly reads the real date) turned out to ALWAYS stamp EVERY article
with `target_date` (the date the pipeline ran) — NEVER reading the actual
publish date from the RSS entry itself. If the cron runs late (a recurring
occurrence, the reason the Telegram bot was built) and then catches up
today, a headline that was actually published a few days ago (but still
within the RSS feed's rolling window) gets stamped as if it were published
TODAY — so the NewsView filter/search "looked" wrong even though the query
itself was correct; the data itself was wrong from the moment it entered
the DB.
- **Fix**: a new `_entry_date(entry, fallback)` -- reads feedparser's
  `published_parsed`/`updated_parsed` (a standard UTC struct_time) if the
  feed includes it, converts to an explicit WIB date (`tzinfo=timezone.utc`
  set first before `.astimezone(WIB)` -- without that, Python treats the
  struct_time as LOCAL SYSTEM time, giving a wrong result). Falls back to
  `target_date` (the old behavior) ONLY if the feed genuinely doesn't
  include a date — honestly using the scrape date rather than guessing,
  not a made-up new constraint.
- **Honest limitation**: this fix only applies going forward (new scrapes
  after the fix is deployed). `daily_news` rows already inserted with the
  wrong scrape date (from a previously-late cron) are NOT
  backfilled/corrected -- the old RSS entry's real publish date is no
  longer stored anywhere (RSS doesn't retain history), so there's no
  source to correct it retroactively, unlike `scrapers/news_archive.py`
  (historical backfill), which does have access to the real date from its
  source API.
- 4 new tests (`tests/test_news.py`): `_entry_date` using published_parsed
  (UTC->WIB conversion across a day boundary, not a coincidental match),
  fallback to updated_parsed, fallback to the scrape date when neither
  exists, + 1 regression test directly on `fetch_all_news()` with a
  past-dated entry confirming the resulting `date` DIFFERS from
  `target_date`. 18/18 test_news.py green.

**Update -- Separate "Get News" + "Get Price" buttons on `/m` (6 August
2026, same session):** Giel asked for a manual trigger from his phone, but
scoped (not 1 button that always runs EVERY scraper like the "Trigger
News" button on the desktop Snapshot) — sometimes he just wants to see the
latest news without waiting for all the market scrapers, or vice versa.
- **`pipeline/run_daily.py`**: 2 new orchestration functions,
  `run_news_only()` (fetch+save news/tags/thread-suggest/auto-dormant
  ONLY) and `run_price_only()` (crypto/coinalyze/yfinance/FRED/
  equity/IDX-flow/econ-calendar/positioning ONLY) -- **`run_daily()`
  itself untouched** (zero risk to the existing cron/Telegram/desktop
  path). Both reuse the EXACT SAME helpers as `run_daily()`
  (`insert_news_dedup`, `upsert_asset_ohlcv`, `upsert_daily_market`, etc.
  -- already factored out separately from the start) -- not a
  reimplementation, just a subset of the steps + their OWN transaction
  (deliberately separate from `run_daily()`'s transaction, so these 2
  scoped triggers are genuinely independent).
- **`web/app.py`**: `POST /api/news/fetch_now` and `POST
  /api/price/fetch_now`, exactly the same pattern as
  `/api/run_daily_now` (synchronous/blocking, try/except
  ValueError->error json) -- no lock/rate-limit (same as the original
  endpoint, protection is enough from session auth + the synchronous
  request/response nature).
- **`/m`**: 2 new buttons "📰 Get News"/"💹 Get Price" below the header,
  always visible (not inside a specific card) -- disabled+relabeled while
  running, a summary toast, refreshing related data
  (`loadHighNews()`/`loadLatest()`) once done.
- Verification: `npm run build` clean. The new endpoints were NOT given
  unit tests (matching the project convention -- `run_daily()`/
  `/api/run_daily_now` itself also has no tests, a live-network
  orchestrator, verified manually through real usage, not layered mocks).

**Update -- `/m` split into tabs instead of 1 long scrolling screen (6
August 2026, same session):** Giel reported that scrolling on the mobile
dashboard is "very tiring" -- makes sense, `/m` had grown from 4 cards
(the original design, 31 July) to 6 cards stacked on 1 screen (MANDATORY,
News, Chart, Thread, Portfolio, Positions -- the last 3 cards added today
as well). Split into 4 tabs, the EXACT SAME pattern as
`ThreadDetailView.vue`/`UniverseView.vue` (an `activeTab` ref + a `TABS`
computed + `.tab-bar`/`.tab-btn`, CSS adapted for mobile width --
`overflow-x:auto` just in case, rather than wrapping if a label is too
long on a narrow screen):
- **Main** -- MANDATORY (predictions) + CORE (news) STAY combined in 1 tab
  (not split further) -- both are a daily ritual that must be 1 step, not
  2 separate tabs adding friction.
- **Chart** -- the Chart card alone.
- **Thread (N)** -- the Active Threads card, label using the count of
  ACTIVE threads.
- **Position (N)** -- Portfolio + ONGOING Positions combined into 1 tab
  (both are "what do I currently hold"), label using the combined
  holdings+positions count.
- The tab bar appears AFTER loading finishes (inside `v-else`, before the
  first section) -- the Get News/Get Price buttons in the header STAY
  always visible across tabs (not part of any one tab), matching their
  role as a quick action rather than per-tab content.
- Verification: `npm run build` clean (`<template>` tags balanced -- Vue
  hard-fails compilation if not, so this is a strong structural signal).
  Browser-checking couldn't continue (port 5000 still held by an old
  process this session, same as the earlier check) -- Giel needs to check
  navigating between tabs directly on his phone.

**Update -- Clean up `daily_news` duplicates from the old scrape-date bug
(6 August 2026, same session):** Giel gave 1 concrete example -- the
article "World Cup gave bars..." (real date Jul 15) appeared with the date
2026-08-09 in production. Dug in: the `scrapers/news.py` bug fixed this
session (stamping `target_date` instead of the real publish date) had
been active for a long time -- 1 old article that lingered in the RSS
rolling window got RE-inserted every day the cron ran, each time getting a
new (wrong) SCRAPE date. The scraper fix only prevents this GOING FORWARD,
it doesn't fix rows that already got in -- so `tools/dedupe_news.py` was
built (a one-off cleanup, not part of the daily pipeline).
- **Strategy to determine the correct date per group (headline+source+
  raw_url, ALL identical = definitely the same article)**: (1) if raw_url
  is CNBC (a `/YYYY/MM/DD/` pattern embedded in its own URL path --
  verified to match 100% in the sample) -- use that date, straight from
  the source, not a guess. (2) if not (e.g. ANTARA, whose URL is just an
  article id) -- use MIN(date) among the duplicates, best-effort.
  **Deliberately grouped by raw_url TOO, not just headline+source** -- a
  generic headline that genuinely repeats across DIFFERENT articles (e.g.
  ANTARA's "IHSG weakens following Asian markets", used for many genuinely
  different days) does NOT get collapsed, since its raw_url differs
  (verified: 986 groups with just headline+source, 778 once raw_url is
  also checked -- that 208-group difference really isn't a bug, and MUST
  be left alone).
- **content_tags/news_thread_links attached to deleted rows MUST be
  repointed to the kept row first** (not orphaned) -- if the target
  already has the same pair (a UNIQUE collision), the duplicate row is
  deleted rather than UPDATEd (a collision guard, not a crash).
  `tag_dictionary.usage_count` recomputed at the end.
- **Tested on a COPY of the DB first** (not directly on the real file) --
  778 groups, 1993 excess rows, 0 orphaned references afterward, idempotent
  (a 2nd run = 0 changes), the "World Cup" example correctly became
  2026-07-15. **Only after that was it run against the real local DB**
  (Giel explicitly confirmed "ok") -- the result EXACTLY matched the
  copy's dry-run: 1993 rows deleted, 113 dates corrected, 38 tags + 67
  thread links repointed, 0 orphans, 0 duplicate groups remaining.
- **Not yet run on Railway** (production) -- needs a separate script +
  `railway ssh`, same pattern as previous data migrations (Giel runs it
  himself, I don't have direct access to the Railway DB).
- 6 new tests (`tests/test_dedupe_news.py`): preview counting, collapse +
  take the date from the URL, fallback to MIN(date), same headline but
  different raw_url NOT collapsed (a §21.9-style guard, preventing false
  positives), repointing tags/thread-links without orphans +
  usage_count recompute, idempotency. 469 tests total still green.

**Update -- Scroll position preserved after save/toggle/confirm on the FE
(6 August 2026, same session):** Giel reported an FE annoyance -- every
click of Save/toggle/confirm on a long list page, the page jumps back to
the top, requiring scrolling back down. Diagnosed via 2 subagents (Explore
then Plan) before executing, per the plan-mode flow: the root cause is THE
SAME across all views -- `save*`/`toggle*`/`confirm*` handlers call
`await post(...)` then `load*()`, which overwrites the ENTIRE reactive
array (`rows.value = await get(...)`), Vue re-renders the whole DataTable,
and the browser (scroll at the window/document level, not a sub-container
-- `html/body/#app` has no `overflow` rule) resets scroll to the top since
there's zero scroll-position handling anywhere in the codebase.
- **New `web/frontend/src/composables/useScrollPreserve.js`** (~15 lines,
  same pattern as `useAppToast.js`): `preserveScroll(fn)` -- wraps an
  async function, captures `window.scrollY` BEFORE the reload, restores it
  via `window.scrollTo` AFTER the DOM updates (`nextTick`, not
  `setTimeout`).
- **Definition-wrap vs. call-site-wrap, chosen per view**: `NewsView.vue`
  (8 spots) & `TagsView.vue` (4 spots) were wrapped at the CALL SITE of
  each save handler -- both also call `load*()` from filters/checkboxes
  (`watch`/`@change`), and resetting scroll to the top THERE is still
  reasonable (a new filter result) -- only the save-triggered ones need
  preserving. The other 4 views (`ThreadsView`, `UniverseView` 9
  functions, `ForwardView` 4 functions, `ThreadDetailView` 2 functions)
  were wrapped once at the `load*()` function's DEFINITION -- verified
  there's no filter/watch calling the load function in these views, so
  the behavior is equivalent but much cheaper (1 spot instead of up to
  ~15 call sites in UniverseView).
- **Deliberately NOT extended to**: `MobileView.vue` (a 1-column tab
  layout, smaller impact, `loadAll()`'s `Promise.all` fan-out needs
  different handling) and the 4 short-form views
  (`Synthesis`/`Snapshot`/`Chart`/`Reading` -- little content,
  scroll-reset there is barely noticeable). Revisit if Giel reports it's
  still bothersome there too.
- Verification: `npm run build` clean (365→366 modules,
  `useScrollPreserve.js` split into its own 0.17kB chunk used by 6 views
  -- proof of reuse, not copy-paste; compilation hard-fails on unbalanced
  braces/parens from a bad wrap, so this is a strong structural signal).
  **Can't verify visually behind login** (credential rule, consistent
  throughout this session) -- Giel needs to try directly: save/toggle in
  News/Threads/Universe/Forward/Tags, check that scroll doesn't jump.
