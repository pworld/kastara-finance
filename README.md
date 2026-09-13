# Kastara Finance — Data Layer + Analysis Engine + Dashboard + Equity Expansion

Personal finance/trading intelligence stack. **The engine suggests, Giel
decides** — there is no automatic execution/trading logic anywhere.

**Status as of July 2026 (full detail in [`docs/ROADMAP.md`](docs/ROADMAP.md)):**
- **Phase A** ✅ — collect raw macro/news data into a local SQLite DB (no paid API).
- **Phase B** ✅ — S&R + breakout/retest + R:R engine (BTC).
- **Phase C** ✅ — **write-enabled** dashboard, now **8 panels/tabs**.
- **Phase D** ✅ — forward layer (manual FedWatch/Dot Plot, automatic COT +
  BTC ETF flow, Policy Tracker, Dissonance Flag).
- **Phase E** ✅ — Daily Briefing → Telegram (one-way push, manual trigger).
- **Phase F+** ✅ — engine replicated to GOLD/IHSG/SP500/USDIDR/USDJPY, +
  4 Persona Analyses (Panel 4, OpenRouter, shared-core + slice v4).
- **Phase J+** 🔶 — **equity expansion (individual stocks)**, universe = **BBCA +
  TSLA**. Build Contract v1.3 is done on the code side (universe OHLCV,
  fundamentals, bank ratios, earnings, per-stock foreign flow, Emiten Grader,
  sizing engine 2.5% + ARA/ARB buffer, price-fraction zone calibration,
  lane-validation sign-off, Tab 8 Universe & Grader). What remains is Giel's own
  manual decisions (bar-replay, final §13 calibration, J-9 persona prompt) — not
  code work.

> **Next up:** migrate the frontend from vanilla HTML/CSS/JS → **Vue 3 + Vite**
> (plan in [`docs/migrationFE.md`](docs/migrationFE.md)) so login/sidebar/etc.
> can be added without the burden of the raw stack. Backend/API unchanged.

> Phase A scope is locked in `plan.txt`. The Phase B-E execution plans
> (`plan_b.txt`-`plan_e.txt`) were deleted once each was executed — their
> summarized results live in `docs/ROADMAP.md`.

Login uses `DASHBOARD_PASSWORD`, set by you in `.env` (see §Setup).

📄 **Full documentation lives in [`docs/`](docs/):**
[ARCHITECTURE.md](docs/ARCHITECTURE.md) (technical design & rationale),
[FLOW.md](docs/FLOW.md) (data flow, diagrams),
[ROADMAP.md](docs/ROADMAP.md) (status per phase),
[SOP.md](docs/SOP.md) (when to open which panel + **how to read each panel item**),
[Master Plan.md](docs/Master%20Plan.md) (strategy, v1.6),
[migrationFE.md](docs/migrationFE.md) (FE → Vue migration plan).

---

## 1. What this does

- **SQLite** `kastara-finance.db` with **27 tables** (`db/schema.sql`) — 11
  Phase A tables + 3 forward-layer (Phase D) + 7 equity Phase J+
  (`instrument_metadata`, `fundamentals_quarterly`, `earnings_calendar`,
  `sector_benchmark`, `emiten_grade`, `grader_log`, `intake_log`) + 1
  `lane_validation_log` (bar-replay sign-off) + 3 News Threads (Addendum B
  §20, N-1: `news_threads`, `news_thread_links`, `thread_relations`
  schema-only) + 2 Faceted Tagging (Addendum C §21, C-1: `tag_dictionary`,
  `content_tags`; `daily_news` also gets 2 new columns via a column
  migration — `display_subtitle`, `for_reading`). `db/connection.py::EXPECTED_TABLES`
  is the authoritative list.
- **Modular scrapers** (each source can run standalone):
  - `scrapers/crypto.py` — CoinGecko + Binance + Alternative.me (BTC OHLCV,
    dominance, funding, OI, Fear & Greed). *Binance blocked? automatic fallback
    to CoinGecko for OHLC.*
  - `scrapers/macro_yf.py` — yfinance (S&P 500, IHSG, Gold, USD/IDR, USD/JPY).
  - `scrapers/macro_fred.py` — FRED (DXY, US10Y, VIX, WALCL, RRP, TGA, HY spread).
    Needs `FRED_API_KEY`.
  - `scrapers/news.py` — RSS (7 active feeds: Fed FOMC, CNBC Finance/Economy/
    Indonesia, Investing ID, ANTARA, Bisnis.com — list in
    `scrapers/feeds_config.py`) + rule-based HIGH/MED/LOW scoring (not
    AI). `check_feed_health()` runs per feed every run — a dead feed shows up
    immediately in `source_flags`/logs, instead of becoming a hidden backlog.
  - `scrapers/econ_calendar.py` — ForexFactory (future economic events:
    FOMC/CPI/etc.), free unofficial JSON endpoint. Forecast/previous are
    stored; `actual` (release result) is never provided by this source —
    filled manually OR automatically via the second pass below.
  - `scrapers/investing_calendar.py` — SECOND pass, HIGH importance
    (3-star) ONLY, fills in `actual` values ForexFactory doesn't have. Uses
    `curl_cffi` against investing.com (Cloudflare, same pattern as
    `idx_foreign_flow.py`) — BUT rate-limits much more aggressively, so it's
    DELIBERATELY only 1 GET per run, scheduled separately from `run_daily`
    via `pipeline/run_investing_actual.py` (its own evening/night cron,
    not added to the morning cron — see [ROADMAP.md](docs/ROADMAP.md) for
    why "grab everything twice per cron" wasn't used). Matches against
    existing `econ_calendar` rows via fuzzy event-name matching (`difflib`)
    + a `country`/`event_date` window, SKIPPING on ambiguity — conservative,
    never guesses.
  - `scrapers/positioning.py` (Phase D) — COT report (CFTC Socrata API,
    free, no key needed: BTC/DXY/GOLD/SP500 speculator net-long) + BTC ETF net
    flow (farside.co.uk, unofficial HTML scrape, needs realistic browser
    headers since the site sits behind Cloudflare — see
    [ARCHITECTURE.md §6.11](docs/ARCHITECTURE.md#611-scraperspositioningpy--cloudflare-needs-browser-realistic-headers)).
  - `scrapers/coinalyze.py` (Track B) — cross-exchange aggregate OI +
    24h long/short liquidation + long/short ratio (Coinalyze REST, free key).
  - `scrapers/idx_foreign_flow.py` (Track C) — market-level IHSG foreign flow
    (F2F/F2D/D2F + net), via idx.co.id using `curl_cffi` (Cloudflare TLS fingerprint).
  - `scrapers/idx_stock_foreign_flow.py` (J-8) — **per-stock** foreign flow
    (buy/sell/net foreign volume) from `TradingSummary/GetStockSummary`.
  - `scrapers/idx_uma.py` (J-11) — checks UMA (Unusual Market
    Activity) integrity flags per ticker, feeds into the Emiten Grader.
  - `scrapers/equity_universe.py` (J-2) — daily OHLCV for universe stocks
    (yfinance `.JK`/US) for instruments in `instrument_metadata`.
- **Pipeline** `pipeline/run_daily.py` — daily orchestrator, idempotent (UPSERT).
  Since Addendum B N-1, it also calls `web.writes.suggest_thread_links()`
  right after ingesting news (rule-based News Threads auto-suggest, ALWAYS
  SUGGESTED-only — see [ROADMAP.md](docs/ROADMAP.md)).
- **Pipeline (evening/night, separate)** `pipeline/run_investing_actual.py` —
  SECOND cron, fills in HIGH-importance `actual` values from investing.com
  (see `scrapers/investing_calendar.py`). Not in crontab yet — run manually
  or add your own cron line (e.g. `0 21 * * *`, WIB).
- **Backfill** `pipeline/backfill.py` — pulls historical data (BTC/macro), preview-before-commit.
- **Manual article** `pipeline/add_article.py` — fills `manual_articles` for
  historical research (RSS can't backfill — see [Manual article](#manual-article-historical-research)).
- **Phase A indicators** `indicators/calc.py` — `net_liquidity`, `volume_ma20`.
- **Analysis engine** (`analysis/`, generic since Phase B), active for
  **BTC/GOLD/IHSG/SP500/USDIDR/USDJPY** (Phase F+ expansion):
  - `analysis/sr_zones.py` — support/resistance zone detection (swing
    high/low + clustering + touch count).
  - `analysis/signals.py` — breakout/retest detection + R:R calculator.
  - `pipeline/run_analysis.py` — orchestrator, writes to `sr_zones` +
    `trade_signals`. **Suggestion only** — `approved` is always 0 from the code.
    Without `--instrument`, processes all 6 instruments at once.
  - `tools/review_signal.py` — CLI to approve/reject a signal by explicit id.
  - `pipeline/seed_context_weight.py` — seeds per-asset driver weighting
    (exactly the Master Plan §4.3 example, e.g. GOLD: real_yield/dxy/geopolitics).
- **Telegram Daily Briefing Phase E** (`notify/`, `pipeline/`):
  - `notify/telegram.py` — `send_message()` (one-way push, not a two-way
    bot) + `get_latest_chat_id()` (one-time setup helper).
  - `pipeline/compose_briefing.py` — assembles the briefing text from data
    you've ALREADY filled in manually (4 lenses, approved signals) — it
    doesn't generate anything itself.
  - `pipeline/send_briefing.py` — CLI, manually triggered (see
    [Daily Briefing to Telegram](#daily-briefing-to-telegram-phase-e)).
- **Equity expansion Phase J+** (individual stocks, universe **BBCA + TSLA** —
  Build Contract v1.3, per-J-step detail in `docs/ROADMAP.md`):
  - `analysis/grader.py` — two-axis Emiten Grader (fund_score × integrity
    flags → INVESTABLE/WATCH/SPECULATIVE/AVOID quadrant), logs to `emiten_grade`/
    `grader_log`.
  - `analysis/sizing.py` — position sizing, MAX_RISK 2.5% (locked), round-down
    lot quantization, `RISK_CAPACITY_EXCEEDED` skip (without moving the SL), **1.5×
    ARA/ARB buffer** (§18, locked) via `has_daily_limit`.
  - `analysis/calibration.py` — per-market S&R zone tolerance derived from the
    official **IDX price fraction** (BEI Regulation No. II-A); used by
    `run_analysis` specifically for `market='IDX'` instruments (**DRAFT**
    pending Giel's bar-replay validation, §13.1).
  - `pipeline/backfill_fundamentals.py` — quarterly fundamentals (yfinance);
    bank ratios CAR/NPL/NIM/LDR are filled **manually** (Panel 8), never
    overwritten by the scraper.
  - `web/writes.py::validate_lane()` — the ONLY path that can set
    `lane_validated_at` / promote a lane to TRADE, purely manual (bar-replay
    sign-off), logged to `lane_validation_log`.
  - Tab 8 **Universe & Grader** (Panel 8) — candidate intake, eligibility
    check, ticker detail + quadrant override, bank ratios, lane validation,
    grader log.

Every scraper is **API-failure resistant**: if one source goes down, it's
flagged `fail` in `source_flags` and the pipeline keeps going (no crash, no
silent failure).

---

## 2. Setup

Needs Python 3.11+.

```bash
# 1. virtualenv
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. dependencies
pip install -r requirements.txt

# 3. configuration (optional, only needed for FRED & Telegram)
cp .env.example .env
# edit .env, fill in FRED_API_KEY (free: https://fred.stlouisfed.org/docs/api/api_key.html)
```

FRED is optional — without a key, FRED series are `skip`ped (not an error),
everything else keeps running.

**Telegram setup (optional, for Daily Briefing Phase E):**
1. Message `@BotFather` on Telegram, send `/newbot`, follow the prompts -> get a `TELEGRAM_BOT_TOKEN`.
2. Send any message (e.g. `/start`) to your new bot from your own Telegram account.
3. `python -m notify.telegram` -> prints the `chat_id` from the latest update.
4. Fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`.

Without this setup, the "Send to Telegram" button / `pipeline.send_briefing`
still displays the briefing text, just with `sent: false` (not actually sent).

**OpenRouter setup (optional, for Panel 4 "4 Analyses (AI)"):**
1. Sign up at https://openrouter.ai, generate an API key.
2. Fill in `OPENROUTER_API_KEY` (and optionally `OPENROUTER_MODEL`, default
   `anthropic/claude-sonnet-5` — check which model ids are still active at
   https://openrouter.ai/models, older models get deprecated often) in `.env`.
3. Write each persona's system prompt in `prompts/persona_<gema|leon|akela|rivan>.txt`
   (see `prompts/README.md`) — these files are NOT created automatically and are
   NOT committed. Without this, the "Run Analysis" button will tell you in
   the UI that the prompt hasn't been filled in yet.

**Coinalyze setup (optional, for Panel 1 aggregate OI/liquidation/L-S ratio):**
1. Sign up for free at https://coinalyze.net, generate an API key.
2. Fill in `COINALYZE_API_KEY` in `.env`.

Without this, the 4 new fields (Aggregate OI, Long/Short Ratio, 24h Long/Short
Liquidation) in Panel 1's "Crypto (BTC)" category stay `n/a` (`skip`ped, not an
error) — everything else keeps working as normal.

**IHSG Foreign Flow (Panel 3 Positioning) — automatic, NO setup needed:** the
source is idx.co.id (not a public official API), no API key required. One
technical note: the scraper (`scrapers/idx_foreign_flow.py`) uses `curl_cffi`
(not plain `requests`) because idx.co.id sits behind Cloudflare bot-management
that detects Python's TLS fingerprint — if this field stays empty in Panel 3,
check that `curl_cffi` is installed (`pip show curl_cffi`) before suspecting
the API itself changed.

---

## 3. Usage

### DB initialization (called automatically by the pipeline, but can be run manually)
```bash
python -m db.connection
# -> creates kastara-finance.db + 27 tables
```

### Run the daily pipeline
```bash
python -m pipeline.run_daily              # today's date (WIB)
python -m pipeline.run_daily 2026-06-24   # a specific date
python -m pipeline.run_investing_actual   # Evening cron
```
Idempotent — safe to run multiple times for the same date (UPSERT, not
duplicated). Prints a `source ok / fail / skip` summary per API at the end of
each run.

### Backfill historical data (preview first, then commit)
```bash
python -m pipeline.backfill --instrument BTC   --from 2025-01-01 --to 2025-06-01
python -m pipeline.backfill --instrument SP500 --from 2025-01-01 --to 2025-06-01
python -m pipeline.backfill --instrument DXY   --from 2025-01-01 --to 2025-06-01  # needs FRED_API_KEY
python -m pipeline.backfill --instrument BTC   --from 2025-01-01 --to 2025-06-01 --yes  # skip confirmation
```
Supported instruments:
- yfinance / asset_ohlcv: `BTC` `SP500` `IHSG` `GOLD` `USDIDR` `USDJPY`
- FRED / daily_market: `DXY` `US10Y` `VIX` `WALCL` `RRP` `TGA` `HY`

Backfill always shows a **preview** (how many new rows, how many duplicates
skipped) and asks for `[y/N]` confirmation before writing.

Backfill is a **one-time** bootstrap, not a recurring job — don't put it in
the same cron as `run_daily`. Safe to call back-to-back for many instruments
at once (yfinance/FRED return the whole date range in 1 request, the request
count doesn't change however far back the range goes, e.g. from 2010 vs from 2021).

### Manual articles (historical research)

RSS (`scrapers/news.py`) only shows **current** news — there's no way to pull
old headlines (e.g. from 2010) from RSS, that's a structural limitation of the
source, not something that can be backfilled. For historical research, fill
`manual_articles` manually:

```bash
# Add an article you found/curated yourself
python -m pipeline.add_article add --date 2015-06-19 --source CNBC \
    --url "https://..." --headline "Fed hints at rate hike" \
    --notes "An important turning point for DXY that year" \
    --tags fed,rate,dxy --key-event

# Search it again for later research
python -m pipeline.add_article list --tag dxy
python -m pipeline.add_article list --from 2015-01-01 --to 2015-12-31
python -m pipeline.add_article list --search "rate hike"
```
If the same URL was already added before, the tool just **tells you** (doesn't
block) and asks for confirmation — revisiting the same article with a new note
is a valid use case.

### Analysis engine (S&R + breakout/retest, 6 instruments since Phase F+)

```bash
# Run S&R zone detection + breakout/retest signal detection for ALL instruments
# (BTC, GOLD, IHSG, SP500, USDIDR, USDJPY)
python -m pipeline.run_analysis

# Or a single instrument
python -m pipeline.run_analysis --instrument GOLD
```
Idempotent (re-running doesn't duplicate zones/signals, doesn't overwrite
manually-reviewed `validated`/`notes`). **Manual trigger** for now, not yet
cron'd (local is dev-only for now).

```bash
# Review a signal (id MUST be given explicitly — no approve-all mode)
python -m tools.review_signal list
python -m tools.review_signal list --instrument BTC --valid-only
python -m tools.review_signal approve --id 42 --notes "good setup, strong volume"
python -m tools.review_signal reject  --id 42 --notes "DXY breakout at the same time, skip"

# Seed per-asset driver weighting (once, idempotent)
python -m pipeline.seed_context_weight
```

Every signal from `run_analysis` is **suggestion only** — `approved`
is always 0 from the code, and only changes via `review_signal approve`.
There is no execution/trading logic anywhere.

### Web dashboard (8 panels, write-enabled since Phase C)
```bash
python -m web.app
# open http://127.0.0.1:5000
```
9 tabs: **1 Snapshot** (cards +
source_flags + Manual Backfill preview→confirm form), **2 News** (list +
impact filter + mark for Reading + News Threads suggestion chips (multi-link,
confirm/reject/manual-link) + facet tag command-palette (Addendum C §21,
AND/OR filter, "Send to Lens →" feeds a manual article to a persona) +
display_subtitle inline-edit + collapsible RSS summary (Addendum D §22 D-1,
as-is from the feed, not AI) + Add Manual Article), **3 Forward**
(real Economic Calendar data + automatic/manual forecast/previous/actual,
Earnings Emiten + open-position warning, manual FedWatch/Dot
Plot Expectations, automatic COT+ETF Positioning & manual SBN, manual Policy
Tracker, rule-based Dissonance Flag), **4 Reading**
(4 lenses GEMA/LEON/AKELA/RIVAN via OpenRouter + manual External AI Check +
Conflict Notes), **5 Chart** (candlestick + S&R zone overlay + breakout/retest
marker + signal Approve/Reject + MA50/100/200 + range filter +
lane badge), **6 Synthesis** (textarea + instrument outlook + Trading Journal +
position sizing + Prediction Log + prediction scoring + Daily Briefing), **7
History** (synthesis/prediction/journal/lens archive, sub-tabs), **8 Universe &
Grader** (Phase J+: stock universe, candidate intake, eligibility check + grade,
ticker detail + quadrant override, manual bank ratios, bar-replay lane validation,
grader log), **9 Settings** (Addendum C §21.11, slow/reflective curation: Tags
tab -- create/edit description/facet, delete, merge duplicate tags, orphan
tags; Threads tab -- the old `/threads` index page was MOVED here on 17 Jul
2026 (redundant once Settings existed): create a new thread, inline-edit
title/status/current-read/keywords, "Manage" dialog for verdict/persona_tags/
facet tags, stance composition, age, N/7 ACTIVE, "Timeline" button to
`/threads/:id` — that timeline page itself is NOT in the nav, only reached
from here or a News chip).
Panels 1–6 = the TRADE lane's daily rhythm; Panel 8 = the INVEST lane's
weekly/quarterly rhythm; Settings = occasional/quarterly (see
[SOP.md](docs/SOP.md)).

**Session-based login** (`DASHBOARD_PASSWORD` in `.env`, see §Setup —
since the Fase 3 Vue migration, NO LONGER unauthenticated). **No
automatic AI/LLM calls anywhere** — the "External AI Check" in Panel 4
is a manual paste field (you compare another tool's output yourself), Kastara
never calls an AI for it. News Threads auto-suggest & tag validation are also
rule-based (keyword matching / grammar rules), NOT AI.

API: **82 `/api/*` endpoints** (42 GET + 40 POST), all `jsonify(...)` —
`/` serves the Vue build (`web/frontend/dist/`), all data is fetched
client-side. Read-only Phase 1 (`/api/latest`, `/api/daily_market`,
`/api/asset_ohlcv`, `/api/news`, `/api/assets`, `/api/health`) is
unchanged. Other groups: Phase C writes
(`/api/backfill/*`, `/api/reading/save`, `/api/signals/review`,
`/api/synthesis/save`, `/api/journal/add`, `/api/prediction/*`), Phase D
(`/api/expectations`, `/api/positioning`, `/api/disonansi`), Phase E
(`/api/briefing/send`), Persona (`/api/persona/{run,status}`, `run` accepts
an optional `news_ids` -- manual feed §21.4), Phase J+
(`/api/universe`, `/api/intake/*`, `/api/emiten/<t>{,/override,/validate_lane}`,
`/api/sizing/suggest`, `/api/fundamentals/bank_ratios`, `/api/grader_log`,
`/api/lane_validation_log`, `/api/earnings{,/warnings}`), News Threads
(`/api/threads*`, incl. `/api/threads/stats`), and Faceted Tagging Addendum C
fully complete (C-1+C-2, 17 Jul 2026): `/api/tags*` (incl.
`/api/tags/<id>{,/delete}`, `/api/tags/merge`, `/api/tags/orphans`),
`/api/content_tags*`, `/api/news/for_reading`,
`/api/news/<id>/display_subtitle`. Rule-based tag & thread-link auto-suggest
(keyword/tag-match) and stale-thread auto-DORMANT run automatically every
`run_daily` -- no separate endpoint for that. The authoritative list is the
routes in `web/app.py`.

### Daily Briefing to Telegram (Phase E)
```bash
python -m pipeline.send_briefing --dry-run     # print the text, don't send
python -m pipeline.send_briefing               # send to Telegram, today
python -m pipeline.send_briefing --date 2026-07-08
```
Run **manually** by you after finishing Panels 4-6 (4 lenses +
approved signals filled in) — not part of `run_daily`, because the briefing
content is only complete after the morning routine is done (~07:20), not at
data-pull time (07:00). There's also a "Send to Telegram" button on Panel 6
of the dashboard that does the same thing. Any section you haven't filled in
shows `(not filled in)` — not hidden — so anything missed is visible.

### Tests
```bash
python -m pytest -q
```

---

## 4. Data schema (summary)

| Table | Filled by? | Contents |
|---|---|---|
| `daily_market` | ✅ automatic | 1 row/date — global macro context (BTC, DXY, S&P, IHSG, Fear&Greed, net liquidity, etc.) + `source_flags` JSON |
| `asset_ohlcv` | ✅ automatic | 1 row/asset/date — universal OHLCV + `volume_ma20` |
| `daily_news` | ✅ automatic | headline + `impact_level` (HIGH/MED/LOW) |
| `econ_calendar` | ✅ automatic | future economic events (ForexFactory), UPSERT by natural key |
| `manual_articles` | 🖊️ manual (has a tool) | historical research — filled via `python -m pipeline.add_article`, RSS can't backfill |
| `positioning` | ✅ automatic + 🖊️ manual | COT (CFTC) + BTC ETF flow automatic every `run_daily`; SBN foreign flow & manual corrections via dashboard |
| `expectations` | 🖊️ manual | CME FedWatch cut probability, Fed Dot Plot median — no free source exists, filled via dashboard Panel 3 |
| `policy_tracker` | 🖊️ manual | policymaker statements, `literal_statement` vs `inference` kept strictly separate, via dashboard Panel 3 |
| `reading_workspace`, `trade_signals`, `sr_zones`, `trading_journal`, `prediction_log`, `asset_context_weight` | 🖊️/⚙️ | used by Phase B/C (see each section above) |
| `instrument_metadata` | ✅ + 🖊️ | 1 row/stock in the Phase J+ universe — lane, lot_size, sector, `has_daily_limit`, `lane_validated_at` (bar-replay) |
| `fundamentals_quarterly` | ✅ + 🖊️ | quarterly fundamentals (yfinance) + bank ratios CAR/NPL/NIM/LDR (manual) |
| `earnings_calendar` | ✅ | earnings/corporate action schedule (yfinance), enforces the no-hold-through-earnings rule for US stocks |
| `emiten_grade`, `grader_log`, `intake_log` | ⚙️ + 🖊️ | Emiten Grader results + audit log + candidate intake decisions |
| `lane_validation_log` | 🖊️ | bar-replay lane validation trail (append-only, only via `validate_lane()`) |
| `sector_benchmark` | ⚙️ | sector comparison structure (J-5, not yet filled — not worth it with 1 ticker/sector yet) |

`source_flags` (JSON in `daily_market`) records each API's status per run, e.g.:
```json
{"coingecko_ohlcv": "ok", "binance_ohlcv": "fail", "fred_dxy": "skip", "yf_SP500": "ok"}
```

All dates are stored as `YYYY-MM-DD`, times in **WIB (UTC+7)**.

---

## 5. Automation (cron)

**A crontab is already installed** for the current user (`crontab -l` to view),
scheduled `0 0 * * *` (00:00 WIB — this WSL system's TZ is already
`Asia/Jakarta`, no conversion needed). Logs go to `logs/run.log` (gitignored).

```cron
MAILTO=""
0 0 * * *  cd /path/to/kastara-finance && .venv/bin/python -m pipeline.run_daily >> logs/run.log 2>&1
```

**Still needs one manual step (requires sudo password, can't be automated):**

```bash
# 1. Start the cron daemon (once, until this WSL instance restarts)
sudo service cron start

# 2. (optional, recommended) so cron also starts automatically every time
#    this WSL instance starts — edit /etc/wsl.conf, add:
#    [boot]
#    command = service cron start
sudo nano /etc/wsl.conf
```

**Important note about WSL:** cron only runs while this WSL instance is
active. WSL does **not auto-start** when Windows boots unless something
triggers it (opening a WSL terminal, or Windows Task Scheduler configured to
run `wsl.exe` at logon). If you need a schedule that truly never goes down,
consider a small VPS for this later (not a priority right now — see
`plan.txt` §9, a scheduler library isn't used in Phase A).

A scheduler library (APScheduler etc.) is still not used — OS cron is enough.

---

## 6. Implementation notes

- **Binance is often blocked** on some networks/regions (including ID). The
  crypto scraper automatically falls back to CoinGecko for OHLC; funding rate
  & open interest (Binance futures) will `fail` and stay empty — that's by
  design, not a bug. To use Binance (active VPN) or route through a proxy,
  set in `.env`: `BINANCE_BASE`, `BINANCE_FAPI_BASE`, `BINANCE_ENABLED`, or
  `KASTARA_PROXY` (e.g. `socks5://127.0.0.1:1080`). See `.env.example`.
- **`SQLITE_BUSY` / database is locked** (e.g. opening the DB in DBeaver): the
  DB uses **DELETE** mode (SQLite's default) + `busy_timeout=5000` (see
  `db/connection.py`) — our Python processes automatically retry for up to 5
  seconds on a brief lock. The root cause when this shows up in DBeaver is
  usually **DBeaver on Windows connecting via a `\\wsl.localhost\...` path**
  — that's effectively a network share (9P) from Windows' side, and SQLite
  (even in WAL mode, which was tried and didn't help — see
  `docs/ARCHITECTURE.md §6.1`) isn't reliable across the Windows↔WSL
  boundary. **Permanent fix: install DBeaver INSIDE WSL** (not on Windows),
  running via WSLg — file access becomes native and the boundary disappears
  entirely. Already set up at `~/dbeaver` (no-root tarball, bundled JRE, no
  `sudo`/`apt` needed):
  ```bash
  ~/dbeaver/launch.sh          # launch DBeaver (appears as a Windows window via WSLg)
  ```
  Connection in DBeaver: use the native path matching `KASTARA_DB_PATH` in
  `.env` (see the next point — **no longer** inside the project folder), and
  **not** `\\wsl.localhost\...`. If you still want to use the Windows version
  of DBeaver: close all tabs/reconnect fresh (a stale transaction stuck in the
  client is the most common cause) + add the driver property
  `busy_timeout=5000`.
- **`KASTARA_DB_PATH` — DB location**: the DB file is deliberately kept
  **outside the project folder** (`.env`: `KASTARA_DB_PATH=/home/<user>/LOCAL/kastara-finance-data/kastara-finance.db`)
  so it never mixes with the code/git — the DB changes every day
  (pipeline/cron), the code doesn't; this removes the risk of it accidentally
  being committed or included in a git operation. You can also use a Windows
  UNC path (`\\wsl.localhost\<distro>\home\...`) — it's automatically
  translated to the native Linux path (the same file), but for access from
  WSL itself (pipeline, DBeaver-in-WSL) use the native path directly like the
  example above.
- **SQLite vs Postgres/NoSQL**: for backfilling up to ~5 years of daily data,
  SQLite is still a good fit — the data is tabular (a relational fit, not
  NoSQL) and the volume (tens of thousands of `asset_ohlcv` rows, hundreds of
  thousands of `daily_news` rows) is well under SQLite's capacity. Indexes
  have already been added for date-range queries at that scale:
  `idx_asset_ohlcv_instrument_date`, `idx_daily_news_dedup` (also enforces
  dedup by headline at the DB level), `idx_daily_news_impact_date`. Moving to
  Postgres only becomes relevant with concurrent multi-user access or a need
  for managed cloud hosting later — not a question of historical data volume.
- **RSS feeds can die/move.** The registry is `scrapers/feeds_config.py`
  (`FEEDS`) — the only place to change a url/enabled flag, don't touch
  `news.py`. `check_feed_health()` checks every feed on every run (status
  goes into `source_flags` with an `rss_` prefix, `run_daily` prints a `RSS: X
  ok, Y dead` summary) — a dead feed shows up immediately in the log,
  instead of becoming a hidden backlog.
- **FRED series ids sometimes change.** See `scrapers/macro_fred.py` (`SERIES`).
  A failing series is flagged `fail` per-series, the pipeline continues.
- **No API keys in source code.** Everything goes through `.env` +
  `python-dotenv`.
- **No code copied from an AGPL repo** (OpenBB etc.) into this project.

---

*Kastara Finance Master Plan v1.6 (`docs/Master Plan.md`) + Phase J+ Build
Contract v1.3. Status per phase & locked decisions: `docs/ROADMAP.md`. Usage
rhythm: `docs/SOP.md`. Next initiative: FE migration to Vue
(`docs/migrationFE.md`).*
