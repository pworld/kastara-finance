# KASTARA FINANCE — MASTER PLAN
**Version:** 1.6
**Date:** July 12, 2026 (revision of v1.5, July 11, 2026)
**Author:** Giel × Claude
**Status:** Locked — v1.6 is a corrective revision, not a feature addition:
(1) the labels of Panel 4's 4 lenses are corrected — the old labels swapped
the AKELA/RIVAN domains and assigned a "Sentiment & Psychology" label that
didn't belong to any lens (Section 6), (2) IHSG context weight is
synchronized with the IHSG-foreign-flow decision (Section 3, 4.3), (3) the
SBN flow tension between the v4 persona prompt and the masterplan has been
RESOLVED — SBN is exclusive to the Forward Panel, never enters the persona
slice (Section 4.2), (4) the Phase J+ build order no longer copies step
numbers — Build Contract v1.3 is established as the single source of truth
for specifications (Section 12), the "5 draft tables" status is closed.
Day-to-day execution detail stays in [ROADMAP.md](ROADMAP.md).

---

## 0. HOW TO READ THIS SYSTEM (Mental Model)

This document is large. Before drowning in details, hold onto this map first. Whenever you're confused, come back here.

### Three sides, one system
Table, Panel, and Sprint are **not three different things** — they are one system seen from three sides:
```
TABLE   = how data is STORED       (warehouse)
PANEL   = how data is DISPLAYED    (storefront)
SPRINT  = the order you BUILD in   (contractor's schedule)
```
Example: the `daily_market` table and Panel 1 "Data Snapshot" are the same thing, seen from the storage side vs. the screen side.

### Spine — the whole system is just one straight line
```
①  GATHER  →  ②  STORE  →  ③  PROCESS  →  ④  SERVE  →  ⑤  READ & PREDICT  →  ⑥  ACT & SCORE
  (data comes in) (data bank)  (tools)     (dashboard)   (Giel's seat)          (trade + evaluation)
```
Every component falls into one of these boxes:
```
① GATHER    scraper (CoinGecko, Binance, FRED, yfinance, alt.me, RSS)
            + manual fetch tool + manual article input
② STORE     all tables in Section 4
③ PROCESS   indicator engine, S&R detector, signal engine (Section 7)
④ SERVE     6-panel dashboard (Section 6)
⑤ READ      Forward Panel + Reading Workspace + prediction_log
            ← GIEL'S SEAT. The machine does not sit here.
⑥ ACT       approve signal → trading_journal, evaluate prediction → score,
            optionally turned into content
```

### Core principles not to forget
- **The machine assembles, Giel predicts.** The "predicting machine" only lives in boxes ⑤–⑥. Boxes ①–④ are the pipe: built once, runs on its own every morning.
- **The forward layer sets the LANE, not the ENTRY trigger.** Policy-direction reading shifts bias; entry still requires breakout + retest + volume.
- **Every automated output needs Giel's approval** before becoming a decision (`giel_approved` / `validated_by_giel` flag at the data level).
- **Predictions are logged and scored** (`prediction_log`) — this is what distinguishes an analyst from a pundit.
### How it's used in practice — Giel's morning, ~20 minutes
```
07.00  Panel 1 check data intake · Panel 2 read & flag news
07.05  Panel 3 Forward → set today's LANE (FedWatch, COT, rhetoric)
07.10  Panel 4 Reading → write the 4 lenses + conflicts
07.15  Panel 5 Chart → is the setup valid? approve/skip
07.18  Panel 6 → synthesis + log 1 prediction into prediction_log
07.20  Done. Optionally turn it into content.
```

---

## 1. VISION & POSITIONING

### Core Concept
Kastara Finance is **an engineer who becomes a finance analyst** — not an influencer using AI as a gimmick, and not a fully-automated AI without a human. The tools being built are **not for sale**, but to help Giel himself read the market more sharply. The main goal is not to sell tools — the goal is a **personal-brand finance influencer** who is credible because his analytical process is transparent and backed by self-built tools.

### Value Proposition
```
TOOLS HELP SEE (chart, S&R, indicators, suggest buy limit)
         +
GIEL READS EVERYTHING (news, data, even output from other AI such as
                  TradingAgents, qrak/LLM_trader, etc.)
         =
GIEL'S UNDERSTANDING & SYNTHESIS (not pure AI output)
```

Tools answer "what does the chart show." Giel answers "what does it mean, and what should be trusted." The 4 Personas (GEMA, LEON, AKELA, RIVAN) are **Giel's own thinking framework** for reading the news.

> **Explicit deviation (v1.5, at Giel's request):** originally designed to be
> filled manually by Giel himself. Since Panel 4 was rebuilt, the 4 lenses
> became **AI-generated** via OpenRouter (`llm/persona_analysis.py`) — triggered
> manually per card (the "Run Analysis" button), the result is read-only in a
> popup, and CANNOT be edited. Each persona's system prompt is written
> manually by Giel himself (`prompts/persona_<lens>.txt`, personal IP,
> gitignored) — so the output remains "Giel's thinking framework," just
> executed by AI, not typed by Giel word for word. Giel still approves/uses/
> discards the results; no output automatically becomes a decision. Since the
> v4 prompt (July 2026), the 4 personas also each receive **different data
> context per lens** (Shared Core + Slice — see Section 4.2, 6), not one
> identical blob — so that the 4 viewpoints are genuinely independent and can
> conflict productively, rather than being 4 speaking styles reading the same
> data.

When used in content, this simulates the way Giel breaks down an analysis, not raw bot output without curation.

### Differentiation from a Typical Finance Influencer
| Typical Influencer | Kastara Finance |
|---|---|
| Opinion + gut feel | Rules-based system (breakout + retest, locked) |
| Hides the process | Show the work — tools and data bank are open |
| Relies on one source/feel | Cross-checks many sources (RSS, other AI agents, own data) before concluding |
| Single point of view | 4 lenses (GEMA/LEON/AKELA/RIVAN) — conflicts are recorded, not hidden |
| Reactive/viral content | Structured, repeatable content, based on a daily data bank |

### Market Research Context (GitHub Landscape)
There are many open-source projects that are technically similar (TradingAgents — multi-agent debate; qrak/LLM_trader — multi-persona with claim validation and enforced R:R 1.5; Freqtrade/FreqAI; Sibyl). All of these projects are **fully automated with no human gate**, free, and have no Indonesian context (BI, IDR, IHSG). Kastara Finance's moat is not the sophistication of the tools — it's the combination: human judgment as the final filter, local Indonesian context, a transparent/locked system (not a black box), and a personal brand the audience trusts because its process is visible.

### Vertical within the Kastara Ecosystem
- Kastara Tools (security) — already live
- Kastara HR — already live
- **Kastara Finance** — in development
---

## 2. PHASE ROADMAP

```
PHASE 1 — FOUNDATION          (now)
Data bank + personal analysis tools
No public content required yet

PHASE 2 — CONTENT             (once tools are used daily & stable)
Analysis content based on Giel's real process
4 personas as a public format (manual, not auto-generated)
Platform: X + Telegram

PHASE 3 — COMMUNITY            (once there's an audience)
Telegram paid community
Tools STILL not sold as the main product —
  dashboard/journal access is only a member bonus, not the core offer

PHASE 4 — EDUCATION / B2B      (validated demand, optional)
How Giel builds these tools himself
Consulting if there's demand
```

**Important note:** the tools-monetization roadmap has been deliberately loosened compared to earlier drafts — the main goal of Phase 1–2 is personal brand & Giel's own analytical ability, not selling a product.

---

## 3. TRADING SYSTEM — CODED RULES

### Instruments — One Gateway, Many Assets
Kastara Finance is designed as **a single predictive-analysis gateway for many assets**: BTC, IHSG, S&P 500, Gold, Forex (e.g., USD/IDR, USD/JPY). The pipeline is identical (spine ①–⑥) — what differs is only the data fed in and how it's presented per asset. The S&R + breakout/retest engine is universal (price action behaves the same on all charts), so it isn't rewritten per asset.

- **Trade Engine (signal execution):** starts with BTC/USDT, then duplicates to other assets gradually (daily timeframe)
- **Context Engine:**
  - *Tier 1 (mandatory):* DXY, S&P 500, US10Y, BTC Dominance, Fear & Greed, **VIX, USD/JPY, Net Liquidity (WALCL−RRP−TGA), Economic Calendar**
  - *Tier 2:* IHSG, USD/IDR, Gold
  - *Optional (recorded, activated when scaling):* stablecoin supply, BI–Fed spread
  - ~~BTC L/S ratio + liquidation (Coinglass)~~ — **implemented (July 2026)**
    via **Coinalyze** (free, not paid Coinglass): aggregate OI across
    exchanges, L/S ratio, and liquidation **split into long vs. short** (not
    1 combined figure — RIVAN needs to read the composition to tell
    short-covering apart from pure spot buying). See Section 4 columns
    `btc_oi_aggregate`/`btc_liq_long_24h`/`btc_liq_short_24h`.
  - ~~HY credit spread~~ — **implemented**, FRED `BAMLH0A0HYM2` (checked: limited
    to a rolling 3-year window by the ICE Data source license, not a scraper gap).
**Important — context weight per asset is not the same.** The pipeline is universal, but the dominant driver differs per asset. The engine must know which asset it's reading so the context is weighted correctly:
```
BTC      → net liquidity, ETF flow, F&G, BTC dominance
GOLD     → real yield (US10Y − inflation), DXY, geopolitics
S&P 500  → earnings, Fed path, net liquidity
IHSG     → IHSG foreign flow (ihsg_ff), IDR, BI rate, commodities
           (SBN foreign flow = manual weekly complement, Forward Panel only
            — see 4.2 Stage 2)
FOREX    → rate differential / carry, trade balance
```
Without this weighting, IHSG will be misread (it's more sensitive to foreign flow & IDR than to BTC ETF flow). See Section 4.3 for the schema implementation.

**Build discipline (non-negotiable):** multi-asset is *architectural design now, staged execution later*. BTC first until the engine is truly working & tested, then duplicate. Don't build five assets at once — one strong system beats five half-finished ones.

### Entry Rules (all must be met)
```
1. VALID S&R
   └── Zone touched a minimum of 2–3 times historically
   └── Use an area/zone, not a single line

2. VALID BREAKOUT
   └── Daily candle CLOSES above resistance (not a wick)
   └── Breakout volume > moving average volume

3. VALID RETEST
   └── Price returns to the new support zone (former resistance)
   └── Daily candle CLOSE above the zone = confirmation
   └── Retest volume: present (not thin)

4. ENTRY
   └── Buy limit = close price of the confirming retest candle

5. STOP LOSS
   └── Below the swing low / lower bound of the support zone
   └── Trigger: daily candle CLOSES below the zone (not a wick)

6. TAKE PROFIT
   └── TP1 = next nearest resistance (from historical chart)
   └── Minimum R:R = 1:1.5
   └── Ideal R:R = 1:2.5 and above
   └── If R:R < 1:1.5 → SKIP

7. INVALIDATION
   └── Daily candle closes below SL = cut loss, exit
```

### Tool Output for This Rule
Tools **suggest**, they do not generate decisions: S&R zone detection (semi-automatic + manual validation by Giel), valid breakout/retest detection, automatic R:R calculation, suggested entry/SL/TP1. Giel approves, rejects, or modifies before it's considered a final signal in trading_journal.

---

## 4. DATA ARCHITECTURE

### Philosophy
**One snapshot per day.** Not a real-time stream. The scraper runs automatically in the early morning, data is ready before 07.00 WIB. Giel sits down once per morning session to read, analyze, and write in the Reading Workspace — not AI generating the analysis for him.

### Data Bank — Schema

> **Multi-asset architecture note:** `daily_market` is the **global macro
> context shared by all assets** (DXY, US10Y, net liquidity, F&G, VIX, etc.) —
> one row per date. The price of the assets being traded (BTC, IHSG, Gold,
> Forex) moves to the universal table `asset_ohlcv` (see 4.3). The `btc_*`
> columns below still exist because BTC dominance/funding/OI double as a
> crypto macro signal, not just a price.

#### Table: `daily_market` (global macro context — one row per date)
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
btc_oi_aggregate    FLOAT       (v1.5 — cross-exchange aggregate: Binance+
                                OKX+Bybit, source Coinalyze, summed manually
                                since the API has no ready-made combined symbol)

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

btc_long_short_ratio FLOAT      (v1.5 — FILLED, source Coinalyze not Coinglass)
btc_liquidation_24h  FLOAT      (LEGACY, deliberately left empty — intended
                                for Coinglass in the original draft, never
                                filled; see the 2 liq long/short columns
                                below as its replacement, not deleted since
                                a DROP COLUMN migration is risky for a live DB)
btc_liq_long_24h     FLOAT      (v1.5 — source Coinalyze, SPLIT from short:
                                RIVAN needs to read the composition, e.g. a
                                rebound with short-liq dominant = short
                                covering rather than pure spot buying — one
                                combined figure can't answer that)
btc_liq_short_24h    FLOAT      (v1.5 — pairs with the column above)
stablecoin_supply    FLOAT      (optional — dry powder proxy, not yet done)
hy_credit_spread     FLOAT      (FILLED, FRED BAMLH0A0HYM2 — limited to a
                                rolling 3-year window by the ICE Data source
                                license, not a gap)
bi_fed_spread        FLOAT      (optional — calculated: BI rate − Fed rate,
                                not yet done)

created_at          TIMESTAMP
source_flags        JSON        (status per API: ok/fail)
```

#### Table: `asset_ohlcv` (universal — price of all traded assets)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE
instrument          TEXT        (BTC / IHSG / SP500 / GOLD / USDIDR / USDJPY / etc.)
open                FLOAT
high                FLOAT
low                 FLOAT
close               FLOAT
volume              FLOAT
volume_ma20         FLOAT       (calculated)
created_at          TIMESTAMP

UNIQUE(date, instrument)

One table for ALL assets. Adding a new asset = adding a row with a
different instrument label, NOT adding a new table. Engine ③ (PROCESS)
reads this table, runs the same S&R + breakout/retest logic, and outputs
per instrument. This is what makes the pipeline "one engine, many assets."
```

#### Table: `econ_calendar` (prediction timeline — holds FUTURE events)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
event_date          DATE        (event date — may be in the future)
event_time          TEXT        (release time, if any)
event_name          TEXT        (FOMC / CPI / NFP / RDG BI / options expiry)
country             TEXT        (US / ID / JP / etc.)
importance          TEXT        (HIGH/MED/LOW)
forecast            TEXT        (consensus, if any)
previous            TEXT        (previous release)
actual              TEXT        (filled in after the release)
is_watched          BOOLEAN     (Giel flags as a key catalyst)
created_at          TIMESTAMP

Source: ForexFactory / Trading Economics (scrape). This is the only table
that stores FUTURE dates — the backbone of "what catalyst, when."
Also used by the SOP rule: move SL to breakeven before a HIGH event.
```

#### Table: `daily_news` (from RSS aggregator, shown raw — no automatic AI summary)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE        FOREIGN KEY → daily_market
source              TEXT        (FED/BI/MACRO/CRYPTO/NASDAQ)
headline            TEXT
raw_url             TEXT
impact_level        TEXT        (HIGH/MED/LOW — rule-based keyword scoring, not LLM)
is_key_trigger      BOOLEAN     (manually flagged by Giel after reading)
created_at          TIMESTAMP
```

#### Table: `reading_workspace` (Giel's manual analysis — replaces the old "daily_analysis")
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE        FOREIGN KEY → daily_market
lens                TEXT        (GEMA/LEON/AKELA/RIVAN/SYNTHESIS)
notes               TEXT        (written manually by Giel)
external_ai_ref     TEXT        (optional: comparison notes from TradingAgents/qrak/etc.)
verdict             TEXT        (one sentence, written by Giel)
created_at          TIMESTAMP
```

#### Table: `trade_signals` (suggested by the tools, before Giel approves)
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
giel_approved       BOOLEAN     (default false — filled manually)
notes               TEXT
created_at          TIMESTAMP
```

#### Table: `sr_zones` (S&R zone bank — semi-automatic + manual validation)
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

#### Table: `manual_articles` (manual input — not from the automatic scraper)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE
source              TEXT
url                 TEXT
headline            TEXT
full_text           TEXT
personal_notes      TEXT        (Giel's notes/interpretation)
tags                TEXT        (comma-separated, custom)
is_key_event        BOOLEAN     (flags an event that changed the view)
created_at          TIMESTAMP
```

#### Table: `trading_journal` (personal analysis & trade-result notes — final record)
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date                DATE
instrument          TEXT
setup_type          TEXT        (breakout/retest/other)
entry_price         FLOAT
sl_price            FLOAT
tp1_price           FLOAT
outcome             TEXT        (WIN/LOSS/ONGOING)
personal_notes      TEXT
lesson_learned      TEXT
created_at          TIMESTAMP
```

#### Table: `prediction_log` (prediction record & score — the heart of the "prediction engine")
```
id                  INT         PRIMARY KEY AUTO INCREMENT
date_made           DATE        (when the prediction was made)
horizon             TEXT        (1w / 2w / 1m)
claim               TEXT        (e.g. "BTC breaks $70K before FOMC")
confidence          INT         (% confidence at the time it was made)
basis               TEXT        (what data/lens was used)
target_date         DATE        (when the prediction falls due for evaluation)
outcome             TEXT        (CORRECT/WRONG/PARTIAL — filled in later)
was_actioned        BOOLEAN     (did it become an actual trade?)
lesson              TEXT        (what was learned from the outcome)
created_at          TIMESTAMP

Why mandatory: without this table, what's built is just a dashboard — not
a prediction engine. A true prediction engine LEARNS from its own scores.
This measurable track record is also a brand moat: "here's my prediction
from 3 months ago, here's its score."
```

### 4.1 Manual Data Input — Filter Pull (Backfill)

Besides the daily automatic scraper, the data bank has a **manual input path** fully controlled by Giel — when to pull, which instrument, what date range. Not hardcoded to any specific time range.

```
INPUT FORM — Manual Backfill
├── Instrument     [dropdown: BTC / DXY / S&P500 / IHSG / Gold / USD-IDR]
├── Date Range     [from] — [to]
├── Timeframe      [1D default]
├── Source         [auto-mapped per instrument, see table below]
└── [PULL] → preview number of new rows vs. duplicates → [CONFIRM & SAVE]

SOURCE MAP per instrument
├── BTC            → Binance historical API
├── DXY, US10Y     → FRED API
├── S&P500, IHSG,
│   Gold, USD/IDR  → yfinance historical
```

The core logic: fetch → check for overlap with existing data in `daily_market` → show a preview (number of new rows, number of duplicates, the actual date range successfully pulled) → only commit to the database after confirmation. Prevents duplicate or corrupt data without Giel's knowledge.

Articles (`manual_articles`) and the trading journal (`trading_journal`) go through a similar manual input path — a simple form, paste a URL/text or write a note directly, the system saves it with a date and tags, queryable later for historical research (e.g., "what was I thinking when DXY broke out in March 2026").

### 4.2 Forward-Looking Layer — from Lagging to Predictive

**Problem being solved:** All data in `daily_market` is *lagging* — the market's reaction to something that has already happened. For predictive analysis, Kastara Finance needs *leading* data: what will/is expected to happen, and which direction policymakers are moving before price responds.

**Placement principle (non-negotiable):** The Forward-Looking Layer **determines the lane, not the entry.** Reading Warsh/Purbaya/etc.'s direction shifts the *bias* (which lane is allowed to be played), but entry still requires breakout + retest + volume. This layer is reading material in the Reading Workspace — not a button/veto in the chart engine. This keeps the decision chain intact and prevents the prediction framework from being used to override the system.

Built in 3 stages:

#### Stage 1 — Layer B: Expectations (numbers, most concrete)
Data that is explicitly forward-looking and frames all other readings.

```
Table: expectations
├── id, date
├── metric           (cme_fedwatch_cut_prob / dot_plot_median /
│                      bond_implied_rate / etc.)
├── value            FLOAT
├── horizon          TEXT   (next_meeting / EOY2026 / etc.)
├── source           TEXT
└── created_at

Sources:
├── CME FedWatch     → implied rate-cut probability (scrape,
│                       endpoint to be verified at build time)
└── Fed Dot Plot/SEP → Fed's internal projection (manual, quarterly release)
```

#### Stage 2 — Layer C: Positioning (what is being DONE, not what is SAID)
Validator for Layer A — if the rhetoric and big money's positioning point in different directions, that's a dissonance worth reading.

```
Table: positioning
├── id, date
├── instrument       (BTC / DXY / GOLD / S&P / SBN / etc.)
├── metric           (cot_net_long / etf_net_flow / sbn_foreign_flow)
├── value            FLOAT
├── source           TEXT
└── created_at

Sources:
├── COT report       → CFTC, free, weekly release (a cadence that
│                       fits swing trading)
├── BTC ETF flow     → daily net flow
├── SBN foreign flow → DJPPR / Indonesian data — STILL MANUAL (SPA
│                       site, not reliably scrape-able, checked directly)
│                       ⚠️ CONSUMPTION RULE (v1.6, resolving the tension
│                       with the v4 persona prompt): SBN flow is
│                       EXCLUSIVE to Giel's manual reading in the Forward
│                       Panel (Layer C). It NEVER enters any persona
│                       slice — the v4 prompt forbids GEMA/LEON from
│                       citing it, and that prohibition STAYS IN EFFECT
│                       even when the data happens to be available.
│                       Reason: the manual-weekly cadence doesn't suit
│                       daily AI analysis (risk of stale data being cited
│                       as fresh); for a human eye that knows when the
│                       data was entered, that risk doesn't exist.
└── IHSG foreign flow → v1.5, AUTOMATIC. Source: idx.co.id internal JSON
    API "Digital Statistic" (undocumented, found via the source code of
    the open-source project NeaByteLab/IDX-API, confirmed live), no API
    key needed, just a session cookie. NOT a replacement for SBN — SBN is
    foreign flow in bonds, this is foreign flow in equities, two
    different but complementary metrics. Stored as 3 separate RAW
    components + 1 calculated net (metric prefix `ihsg_ff_*`), NOT just
    the net — so the persona slice (Section 6) can read the composition,
    not just the direction:
      foreignForeign  (F2F) = Foreign Sell − Foreign Buy (foreign-to-foreign,
                              NOT a directional signal — internal rotation)
      foreignDomestic (F2D) = Foreign Sell − Domestic Buy (a legitimate
                              distribution signal)
      domesticForeign (D2F) = Domestic Sell − Foreign Buy
      Foreign Net Buy = D2F − F2D (validated against actual figures 2026-06-02)
    Important correction: the column labels `foreignForeign`/
    `foreignDomestic` in the reference library NeaByteLab/IDX-API
    incorrectly map them as direct "buy"/"sell" — the ORIGINAL labels
    (from the IDX response's own `columns[].Title`) have been re-confirmed
    above.
```

#### Stage 3 — Layer A: Policy Maker Rhetoric (high value, manual)
Crown jewel — not a scraper problem, but knowledge management. Tools only provide the structure to capture statements and track the *drift* of their direction over time. Interpretation remains Giel's job.

```
Table: policy_tracker
├── id, date
├── speaker          (Warsh / Powell / Purbaya / etc.)
├── institution      (Fed / BI / Kemenkeu / etc.)
├── source_url
├── literal_statement   TEXT   ← what was ACTUALLY said (testable)
├── stance_score        INT    ← directional scale (e.g. -2 dovish to +2
│                                hawkish, or fiscal expansionary/contractionary)
├── giel_inference      TEXT   ← reading direction/intent (your read)
├── inference_flag      TEXT   ← TESTABLE / SPECULATIVE
├── drift_note          TEXT   ← changed from the previous statement?
└── created_at
```

**Mandatory editorial discipline (built into the schema):** every Layer A entry separates the `literal_statement` (which is testable) from the `giel_inference` (the reading), and every inference is given an `inference_flag`. Speculative inference may be recorded, but **must be marked SPECULATIVE** — it may not disguise itself as fact. Without this separation, Layer A would slowly turn into a conspiratorial space; with this separation, it stays analytical. This is part of Kastara Finance's analytical identity: testable economic claims are analyzed, speculative/ideological framing is named as speculative.

### 4.3 Multi-Asset Context Weighting

The pipeline is universal, but each asset has a different dominant driver. For the engine to read each asset with the correct context (rather than treating them the same), a weight-mapping table is needed.

```
Table: asset_context_weight
├── instrument        (BTC / IHSG / SP500 / GOLD / FOREX)
├── driver            (net_liquidity / us10y / dxy / ihsg_foreign_flow /
│                       sbn_foreign_flow / etf_flow / etc.)
├── weight            (HIGH / MED / LOW — how dominant this driver is)
└── notes

Sample content (v1.6 — the IHSG row synchronized with the IHSG foreign
flow decision):
BTC   → net_liquidity=HIGH, etf_flow=HIGH, fear_greed=MED, dxy=MED
GOLD  → real_yield=HIGH, dxy=HIGH, geopolitics=MED
SP500 → earnings=HIGH, fed_path=HIGH, net_liquidity=MED
IHSG  → ihsg_foreign_flow=HIGH, usd_idr=HIGH, bi_rate=HIGH,
        sbn_foreign_flow=MED (manual/weekly — Forward Panel only,
        not the persona slice), komoditas=MED
FOREX → rate_differential=HIGH, trade_balance=MED
```

Its function: when the Forward Panel & Reading Workspace read a given asset, the panel highlights the HIGH-weighted drivers for that asset first. IHSG is not read through the BTC ETF lens; it's read through foreign flow & IDR. This prevents misreading as the system scales to many assets. Initial weights are manually seeded by Giel (judgment), and can be refined over time as `prediction_log` data shows which driver is actually predictive per asset.

---

## 5. PIPELINE ARCHITECTURE

### Execution Schedule
```
00.00 WIB     → Automatic scraper runs (US market already closed)
00.00–05.00   → Pull all Tier 1 + Tier 2 data, save to daily_market
                Pull & rank RSS news into daily_news (rule-based scoring, not LLM)
05.00–06.00   → Indicator engine runs: MA, volume ratio, S&R zone re-check,
                breakout/retest detection → written to trade_signals (giel_approved=false)
06.00–06.30   → Chart rendering ready (BTC + 4 context charts)
06.30         → Dashboard ready to open
07.00         → Giel opens the dashboard:
                reads daily_news, fills in reading_workspace manually,
                reviews/approves trade_signals, optionally cross-checks
                with an external AI agent (TradingAgents/qrak/etc.)
07.30+        → Writes to trading_journal if a position is taken
                Optionally turned into content material
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
├── SQLite (development / early stage)
└── PostgreSQL (if scaling / multi-device access)

ANALYSIS LAYER (tools — not an automatic AI agent)
├── Python + pandas          → indicator calculation
├── pandas-ta                → MA, RSI, volume analysis
├── Custom S&R detector      → zone clustering + touch count
├── Signal engine            → breakout + retest + R:R validator
└── (optional, manual trigger) Anthropic API → helps Giel summarize 1
    article on request — not an automatic process every morning
    + OpenRouter (llm/persona_analysis.py) → Panel 4's 4 lenses, triggered
    manually per card (v1.5 deviation, see Section 1)

DASHBOARD LAYER
├── Python + Flask/FastAPI → backend API
├── HTML + JS              → frontend dashboard
└── Chart: custom SVG/Canvas → not a TradingView dependency

CONTENT OUTPUT (Phase 2+, optional, not required in Phase 1)
├── Telegram bot           → push daily briefing once publishing begins
└── X/Twitter              → manual short-form insight
```

**Note:** The Anthropic API/LLM is not a mandatory process that runs automatically every morning. Its role is an *optional aid* that Giel calls manually whenever needed (e.g., asking for a summary of one long article) — not an automatic generator of the 4-persona analysis.

---

## 6. DASHBOARD STRUCTURE

### Main Layout (6 Panels)

```
┌─────────────────────────────────────────────────────┐
│  HEADER: Kastara Finance · date · run status        │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│   SIDEBAR    │         MAIN CONTENT AREA            │
│              │                                      │
│  • Nav       │   [Active panel based on step]       │
│  • Macro     │                                      │
│    snapshot  │                                      │
│  • Signal    │                                      │
│    status    │                                      │
│              │                                      │
└──────────────┴──────────────────────────────────────┘
```

### Panel 1 — Data Snapshot
**Purpose:** Confirm all data was successfully pulled
**Content:** 9 metric cards (BTC OHLCV, DXY, S&P500, US10Y, F&G, BTC Dom, Funding Rate, IHSG, USD/IDR), source + timestamp per data point, scraper execution log, red flag if any source failed. A button to access the Manual Backfill form (Section 4.1) is on this panel.

### Panel 2 — News Briefing
**Purpose:** Reading material, not a ready-made conclusion
**Content:** News cards ranked by impact (HIGH/MED/LOW, rule-based keyword scoring), source label + timestamp, a manual "key trigger" flag button that Giel clicks himself after reading. A "+ Add Manual Article" button to add to `manual_articles`.

### Panel 3 — Forward Panel (Prediction Layer)
**Purpose:** Frame the daily reading with leading data before Giel writes the analysis
**Position:** Deliberately placed BEFORE the Reading Workspace — because expectations, positioning, and rhetoric direction must be read first as context.
**Content:**
- **Expectations (Layer B):** CME FedWatch cut probability, latest Dot Plot median — numbers, concise
- **Positioning (Layer C):** COT net long BTC/DXY/Gold, ETF flow, IHSG foreign flow (automatic), SBN foreign flow (manual weekly — **shown only on this panel**, does not enter the persona slice) — big money's direction
- **Policy Tracker (Layer A):** latest entries from `policy_tracker`, with `literal_statement` and `giel_inference` clearly separated, SPECULATIVE flag visible. "+ Add Policy Note" button for manual input.
- **Economic Calendar:** upcoming HIGH/MED events (from `econ_calendar`) — countdown to the next FOMC/CPI/RDG BI. This is the timeline: "what catalyst, how many days left."
- **Dissonance flag:** if rhetoric (Layer A) and positioning (Layer C) point in opposite directions, the panel flags it — this is a signal worth reading, not an automatic conclusion.
> Reminder on the panel: this layer shifts BIAS/LANE, not the entry trigger. Entry still comes from Panel 5 (chart) with breakout + retest + volume.

### Panel 4 — Reading Workspace
**Purpose:** Where Giel reads the 4 analytical lenses as a thinking structure before synthesis
**Content (v1.6 — lens labels CORRECTED from v1.5):** 4 cards labeled by function — the internal codes GEMA/LEON/AKELA/RIVAN are hidden from the UI:

```
Card 1 (GEMA)  : "Global Macro & Capital Flows"
Card 2 (LEON)  : "Domestic Policy & System"
Card 3 (AKELA) : "Timing, Expectations & Pricing"
Card 4 (RIVAN) : "Asset Structure & Fundamentals"

⚠️ v1.6 correction: the v1.5 labels ("On-chain-Fundamental" for AKELA and
"Sentiment & Market Psychology" for RIVAN) SWAPPED the two lenses' domains
and assigned a label that belonged to neither lens. Per the v4 prompt:
AKELA is NOT a sentiment analyst (F&G/funding is only an INPUT to his
pricing-in), and RIVAN is NOT a psychology analyst (he is the structural
realist — funding/OI/liquidation is crypto's "balance sheet"). There is no
"Sentiment & Psychology" lens in this system — that's by design, not an
oversight: sentiment is an input, not a viewpoint. The UI label is read
every morning; a wrong label slowly reshapes how the lens is used.
```

The "Run Analysis" button per card triggers 1 OpenRouter call (`llm/persona_analysis.py`), the result shown read-only in a popup modal. Each persona's system prompt (`prompts/persona_<lens>.txt`) is written manually by Giel himself — so the direction of the analysis is still determined by Giel, not the model's default.

**Shared Core + Slice (v4 system prompt):** the 4 personas no longer receive the same data (this panel's original design). All get a **Shared Core** (date, key news, BTC close+delta) — then each lens gets a **different slice** from the Panel 1/3 columns matching its focus:
- **GEMA** (Global Macro & Capital Flows): DXY/US10Y/VIX/Net Liquidity/USD-JPY/Gold/SP500/BTC Dominance, COT DXY, ETF flow, IHSG foreign flow read as **the direction of foreign capital flow**, Policy Tracker foreign speakers.
- **LEON** (Domestic Policy & System): IHSG/USD-IDR, IHSG foreign flow read as **a report card of policy confidence**, ID econ calendar, Policy Tracker domestic speakers.
- **AKELA** (Timing, Expectations & Pricing): full econ calendar (forecast/previous/actual), FedWatch/Dot Plot, Dissonance Flag, Fear & Greed history + funding rate **as pricing-in/exhaustion input — not a sentiment lens**, VIX, Vol MA20, delta across all horizons.
- **RIVAN** (Asset Structure & Fundamentals): funding rate, aggregate OI+delta, 24h long/short liquidation, L/S ratio, ETF flow, volume vs. MA — read as **the asset's structure/balance sheet**; for equities: quarterly fundamentals (Phase J+).

The same field deliberately given to 2 slices with different framing (e.g., funding rate to AKELA & RIVAN, IHSG foreign flow to GEMA & LEON) is treated as "productive conflict," not duplication that needs removing. **SBN foreign flow enters no slice** (see 4.2 Stage 2).

The optional "External AI Check" field records & compares results from TradingAgents/qrak/LLM_trader/others — pitted against each other, not followed automatically. The "Conflict Notes" area is free-form for Giel to record points he himself hasn't reconciled between lenses. The results of the 4 lenses (AI) + External AI Check + Conflict Notes are all saved to `reading_workspace` — NO new table for this pivot, only its content is now a mix of AI-generated (lenses) and manual (the rest).

### Panel 5 — Chart + Technical Analysis
**Purpose:** Visual confirmation of the trading setup, with suggestions from the engine
**Content:**

BTC Chart (Trade Engine): daily OHLCV candles (90 days from the data bank), MA50/100/200 overlay, volume bars + volume MA20, S&R zones overlay (from `sr_zones`), breakout/retest point markers, entry/SL/TP1 annotations if there's a signal in `trade_signals`. An "Approve Signal" / "Reject" button that writes to `giel_approved`.

Context charts (4 small ones): DXY, S&P 500, US10Y, Fear & Greed — 30 days each, to read the macro environment, not for direct trading.

### Panel 6 — Synthesis (Personal Record)
**Purpose:** Where Giel writes the daily conclusion — not automatic output
**Content:** A free textarea for Giel's own personal synthesis paragraph (drawn from Panel 4's content, rewritten by Giel himself). Outlook per instrument (Bullish/Bearish/Neutral) — a manual dropdown, not computed by the system. The approved trading signal card from Panel 5, shown again as a final summary before being saved to `trading_journal`.

**Prediction capture:** a concise form to log 1 prediction into `prediction_log` (claim, horizon, confidence, basis, target_date). Plus a "Prediction Score" widget: shows old predictions that have come due, asking Giel to rate CORRECT/WRONG/PARTIAL. This is the calibration loop — the part that makes the system sharper every month.

```
SIGNAL: BREAKOUT DETECTED / WAIT RETEST / NO SETUP
─────────────────────────────────────────
Instrument  : BTC/USDT
Setup       : Breakout + Retest
Entry       : $68,200
Stop Loss   : $66,800  (daily close below the zone)
TP1         : $71,500  (nearest resistance)
R:R         : 1 : 2.4
Volume      : ✓ Confirmed
Status      : SUGGESTED — awaiting Giel's approval
```

---

## 7. CHART ANALYSIS — TECHNICAL ENGINE

### Indicators Computed from the Data Bank
```
TREND
├── MA20, MA50, MA100, MA200 (simple)
├── Price vs MA position (above/below)
└── MA stack order (bullish/bearish alignment)

VOLUME
├── Volume MA20
├── Volume ratio (today vs MA20)
└── Breakout volume flag (ratio > 1.5 = confirmed)

MOMENTUM (optional, Phase 2)
├── RSI 14
└── MACD (12, 26, 9)

S&R DETECTION (custom, semi-automatic)
├── Swing high / swing low detection (20-day lookback)
├── Zone clustering (price within ±0.5% range)
├── Touch count per zone
├── Zone validity (minimum 2–3 touches)
└── Final validation still manual by Giel before a zone is considered active

SIGNAL DETECTION
├── Breakout: close > resistance zone upper + volume confirmed
├── Retest: price returns to the zone + close above zone lower + volume present
└── Suggested entry = retest candle close, suggested SL = below the zone,
    suggested TP1 = next resistance, R:R auto-calculated
```

---

## 8. CONTENT OUTPUT (Phase 2+ — optional, not a Phase 1 prerequisite)

Content is made from the content of `reading_workspace` and `trading_journal` that Giel has already written — not an auto-generate template. The following formats are frameworks; the content itself remains manual writing.

### Daily Briefing (if published to Telegram/X)
```
🔷 KASTARA FINANCE · [date]

📊 MARKET SNAPSHOT
BTC: $XX,XXX (+X.X%) | DXY: XX.XX | F&G: XX

📰 KEY EVENTS
[headline Giel flagged as a key trigger]

🧠 4 LENSES (written by Giel)
GEMA: [one sentence]
LEON: [one sentence]
AKELA: [one sentence]
RIVAN: [one sentence]

📈 SIGNAL
[status from trade_signals that has been approved, if any]

⚠️ This is not financial advice.
The decision is yours.
```

### Video Format (if and when video content production starts)
```
00:00  Greet the audience + state today's event
00:30  Open Panel 1 — Data Snapshot
01:30  Panel 2 — News Briefing
02:30  Panel 3 — Reading Workspace, explain the thinking process per lens
05:00  Panel 4 — BTC Chart, explain the setup
07:00  Context chart — DXY, S&P, US10Y
08:30  Panel 5 — Personal synthesis
09:30  Signal card if any, and why it was taken/skipped
10:00  Close
```

---

## 9. REPO ADOPTION STRATEGY — License & Borrow Policy

Kastara Finance is built with ATM (Observe, Imitate, Modify): there's no new concept that needs to be invented, so adopting from other repos drastically speeds things up. But adoption has two rules that must not be broken: the **license rule** (legal) and the **pipe-vs-brain rule** (strategic).

### 9.1 The "Sane Frankenstein" Principle
Not rebuilding five systems — but pulling out **one best organ** from each repo and assembling them for a new purpose that none of the donors have: **an analysis gateway for a human to decide, not a machine to execute.** All five repos point toward automation (removing the human); Kastara reverses direction toward augmentation (sharpening the human). Same organs, opposite purpose, different species.

```
FROM                TAKE THE ORGAN               DISCARD
──────────────────────────────────────────────────────────────
Nautilus (MIT)    → async/event-driven pattern → execution engine
FinRL (MIT)       → indicator calculation method → RL / black-box
OpenBB (AGPL!)    → multi-source ingestion       → DON'T copy code;
                                                    use via API only
Deltalytix        → log + statistics idea        → IB integration
                    (check license first)
Streamlit ecosys  → speed of building UI          → its shallowness
```

### 9.2 The License Rule (legal — non-negotiable)
A license doesn't care how much code is changed. Heavy modification still produces a *derivative work* bound to the source license. Only two things matter: the **source license** and the **manner of use**.

```
SOURCE LICENSE
├── MIT / Apache 2.0  → SAFE. Copy, modify, commercialize, keep
│                       proprietary — all OK. Just keep the license notice.
├── GPL               → copying code = the ENTIRE project must become GPL.
└── AGPL  ⚠️          → even stricter. Access via a NETWORK (web/Telegram/
                        dashboard) already counts as distribution → the
                        ENTIRE source must be opened, including the moat.
                        POISON for a proprietary project like Kastara.

MANNER OF USE (decisive for copyleft repos)
├── Copy/modify code into the Kastara repo → derivative work → the
│   license carries over
└── Use as a separate service/library (API call) → Kastara is just a
    CONSUMER → Kastara's code stays its own → SAFE

Concrete example, OpenBB (AGPLv3, verified):
✅ pip install openbb → call obb.equity.price.historical(...) → safe
❌ copy OpenBB's source files into the Kastara repo → AGPL carries over
(note: the "linking vs. derivative" boundary for AGPL is a legal gray
 area; the safe approach is to use it via the public API, don't pull the
 source into the repo.)
```

**30-second checklist before adopting any repo:**
```
[ ] Open the LICENSE file — MIT/Apache? GPL/AGPL?
[ ] If MIT/Apache → copy/modify freely, keep the notice
[ ] If GPL/AGPL → DON'T copy code; use via API if possible,
    or rewrite the idea clean-room (see 9.3)
[ ] Record the origin of every piece of code → so it's clear whose is whose
```

### 9.3 The Pipe-vs-Brain Rule (strategy)
"Adopt everything quickly" is right for the pipe, a trap for the brain.

```
PIPE (boxes ①–④)        → ADOPT AGGRESSIVELY
data, storage,               commodity — every repo has this. Copy the
indicators, chart,           MIT ones, rewrite the AGPL ones. Saves months.
dashboard

BRAIN (boxes ⑤–⑥)       → WRITE IT YOURSELF
forward layer, reading,      NO repo has this. Nothing here can be
prediction log,              adopted — it genuinely has to be original.
Indonesian context           This is exactly where "the new stuff" lives.
                              If everything could be adopted, Kastara would
                              just be a remix. What makes it new is the part
                              that has to be handwritten.
```

**The formula:** fast on the pipe, original on the brain. Speed of adoption in ①–④ frees up time — so the energy pours into ⑤–⑥, the part that is truly Kastara's own and can't be cloned by anyone.

### 9.4 The Safe Version of ATM
```
OBSERVE     → free. Study the architecture/patterns of any repo,
              without limit. Ideas aren't licensed.
IMITATE     → for AGPL: "imitate" = rewrite the idea clean-room with your
              own code. NOT copy then modify. For MIT/Apache: copying is fine.
MODIFY      → modifying copyleft code does NOT remove the license. No
              matter how much it's modified it's still a derivative. Only
              MIT/Apache is safe to modify freely.
```

---

## 10. BUILD ORDER (Hands-On)

Split into two dimensions. **PHASE A–E = build the engine once for BTC** (the full pipeline finished & tested). **PHASE F+ = replicate to other assets** (cheap, because the pipeline is the same — just add data + context weight + presentation). Discipline: don't enter Phase F before A–E is solid for BTC.

> **v1.6 Status: Foundation A–E ✅ and Expansion F–I ✅ COMPLETE.** The
> checklist below is kept as a design archive. Active build = Phase J+
> (Section 12).

```
═══════════════════════════════════════════════════════
  FOUNDATION — build the engine once (instrument = BTC)   ✅ COMPLETE
═══════════════════════════════════════════════════════

PHASE A — DATABASE & SCRAPER
[x] Set up the SQLite schema (all tables: daily_market, asset_ohlcv,
    daily_news, econ_calendar, reading_workspace, trade_signals,
    sr_zones, manual_articles, trading_journal, prediction_log,
    asset_context_weight + forward layer tables)
[x] Scraper: CoinGecko + Binance (BTC → asset_ohlcv + crypto macro)
[x] Scraper: FRED (DXY, US10Y, VIX, WALCL/RRP/TGA → net liquidity, HY spread)
[x] Scraper: yfinance (S&P500, Gold, USD/IDR, USD/JPY → context)
[x] Scraper: Alternative.me (Fear & Greed)
[x] Scraper: Economic Calendar (ForexFactory/Trading Economics)
[x] RSS parser: news ingestion + rule-based impact scoring
[x] Manual fetch tool (instrument + date range filter)
[x] Scheduler: local cron job 00.00 WIB (VPS later)

PHASE B — ANALYSIS ENGINE (universal, tested on BTC first)         ✅
PHASE C — DASHBOARD (6 panels, instrument = BTC)                    ✅
PHASE D — FORWARD-LOOKING LAYER (Stage 1–3, see 4.2)                ✅
PHASE E — TELEGRAM (external reading window)                        ✅

═══════════════════════════════════════════════════════
  EXPANSION — replicate to other assets (same pipeline)   ✅ COMPLETE
═══════════════════════════════════════════════════════

PHASE F — GOLD    ✅   PHASE G — IHSG   ✅
PHASE H — S&P 500 ✅   PHASE I — FOREX  ✅

* Note: context data (DXY, US10Y, etc.) has been pulled since Phase A,
  so most of the expansion is presentation + weighting, not new scraping.
```

---

## 11. OPEN QUESTIONS — Status

```
1. Database location  → RESOLVED: local first, VPS later
2. Scheduler          → RESOLVED: local cron first, VPS later
3. Dashboard access   → RESOLVED: Telegram as an external reading window
4. Initial S&R zones  → RESOLVED: hybrid — auto-detect provides candidates,
                        Giel validates (validated_by_giel), can also seed
                        a few key zones manually as a baseline
5. Initial backfill   → RESOLVED: the manual fetch tool moves up to Phase A
                        as a bootstrap; Giel manually pulls historical data
                        before going live
6. SBN vs persona     → RESOLVED (v1.6): SBN flow is exclusive to the
                        Forward Panel (Giel's manual reading); it never
                        enters the persona slice. The v4 prompt and the
                        masterplan are now in sync. (see 4.2)
```

---

## 12. PHASE J+ — EQUITY EXPANSION (Multi-Market, Individual Stocks)

**Status: Build Contract v1.3 LOCKED (July 11, 2026), kickoff underway.**

> **Single Source of Truth (v1.6 rule):**
> - **SPECIFICATION** (final schema, grading rubric, per-market calibration,
>   sizing, execution layer, decisions G1–G7) = **`phase_j_build_contract_v1_3_LOCKED.md`**.
>   This section does NOT copy step numbers or field details from the
>   contract — if there's a discrepancy between this section and the
>   contract, the CONTRACT is correct.
> - **DAILY EXECUTION** (checklist, changelog) = [ROADMAP.md](ROADMAP.md).
> - **The Masterplan (this document)** = strategy & core concept only.
>
> The v1.5 note "5 draft tables because the source document hasn't been
> provided" is CLOSED: contract v1.3 contains the final specification for
> `fundamentals_quarterly`, `earnings_calendar`, `sector_benchmark`,
> `emiten_grade`, `grader_log` — hand the contract file to Claude Code,
> sync schema.sql, remove the draft marker.

### Why This Expansion Differs from Section 3/Phase F-I

Phase F–I extended **a single analysis gateway** to macro/index assets —
few instruments, and fixed. Phase J+ extends the SAME gateway to
**individual stocks** (starting with IDX, then US) — a much larger
instrument population, and each instrument carries new complexity that
doesn't exist for macro assets: quarterly fundamentals, an earnings
calendar, sector classification, ARA/ARB (daily limits), lot size, and
the risk of "a new instrument being tradeable the moment it's added,
without validation" — which is why Phase J+ is designed with an explicit
**gate**, rather than simply "switching on a new instrument" the way
Phase F-I did.

### Core Principles of Phase J+ (strategic summary — details in the contract)

- **`lane` per instrument (TRADE / INVEST / BOTH / NONE)** — determines
  WHETHER an instrument may be used by the engine to generate
  `trade_signals`. New instruments MUST start in `INVEST`/`NONE` until
  validated by bar-replay (`lane_validated_at`). A direct extension of
  "The machine assembles, Giel predicts" (Section 0).
- **Decision hierarchy (the official sentence, locked decision #1):** the
  persona determines the LANE → the engine finds CANDIDATE triggers →
  **Giel decides at the final gate.** The Entry Rules (Section 3) don't
  change — the expansion adds COVERAGE, not a change to signal validation.
- **3 Gates (G1 lane+SOP, G2 universe, G3 fundamentals source)** — all
  require Giel's direct input, none can be assumed.
- **Emiten Grader** — two axes (fundamental quality 0–100 × market
  integrity flag) → INVESTABLE/WATCH/SPECULATIVE/AVOID quadrant. Grade =
  context & universe filter, NOT a trigger. `grader_log` = the only legal
  path for revising weights (anti-overtuning). Social OSINT = Phase 2
  grader, a conditional backlog item.
- **Sizing & lot quantization** — round DOWN, skip on
  `RISK_CAPACITY_EXCEEDED`, no moving SL to fit a lot, 1.5× ARA/ARB buffer
  (default guideline, revised only via journal). The system talks in
  units of risk, not "expensive/cheap."
- **Manual-only execution (Stockbit/IBKR)** — a ban on broker trading APIs
  applies for phases J–K; any future reconsideration must go through a
  separate written review, done while NOT holding a position/in drawdown
  (guarded in contract Section 15).
- **US stock earnings rule: full version** — positions closed before the
  earnings date, no compromise on size.

### What's Waiting on the Gate (not a technical gap)

The full universe list (G2 — build starts with BBCA as the single
instrument), final lane for all instruments + SOP v4.1 amendment (G1),
final fundamentals source (G3), the dashboard's manual-input UI (explicit
backlog — currently via the CLI `pipeline/seed_universe.py`), and the
Emiten Grader module itself.

---

*Kastara Finance Master Plan v1.6 — Foundation A–E ✅, Expansion F–I ✅,
AI-generated personas with corrected lens labels (Section 6), SBN-persona
tension resolved (Section 4.2, 11), Phase J+ locked with contract v1.3 as
the single source of truth for specification (Section 12). Living
document — change history & daily execution are in [ROADMAP.md](ROADMAP.md).*
