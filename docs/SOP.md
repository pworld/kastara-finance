# APPLICATION USAGE SOP — Kastara Finance
**Version:** 1.2 · July 28, 2026 · Owner: Giel
**Position of this document:** governs WHEN to open which panel and WHAT is allowed to be done there. Asset-level rules stay in their own SOPs (single source of truth):

> **Document structure:** **Part A (§0–§7)** = rhythm & rules (when to open what).
> **Part B (§8)** = **how to READ each item in each panel** (what the numbers mean, what
> up/down means) — used when you forget "what does this field mean". **Part C
> (§9)** = the Investing lane (formerly the "Universal" sidebar) — how to read + how to fill in.
> If you just want the morning ritual: Part A is enough. Part B/C are reference dictionaries.

- Entry/SL/TP/sizing rules for trades → Master Plan §3 + Build Contract v1.3
- Gold triggers & brackets, stock investment screening → Saham Emas SOP v2.0
- Multi-asset allocation & low-point trigger → Investment SOP v4.1
If this document feels like it contradicts the SOPs above: the asset SOP wins, and the conflict is logged for review.

---

## 0. USAGE PRINCIPLES

1. **Two lanes, two rhythms, one application.** TRADE lane = daily rhythm (Panel 1–6). INVEST lane = weekly/quarterly rhythm (Tab 8 + invest SOP). Don't swap their rhythms: checking invest positions every day = inviting yourself to become a trader in a portfolio that's supposed to be boring (principle from Saham Emas SOP §0.1).
2. **The application suggests, Giel decides.** No decision is valid without passing through the gate (`giel_approved`) — and no trade is valid without an approved `trade_signals` row first. A trade without a logged signal = an SOP violation, regardless of the outcome.
3. **Missing data = analysis postponed, not guessed.** A red `source_flags` on a field needed that day → the part of the analysis that depends on it is skipped and noted, not filled in with assumptions.
4. **The morning session is a reading & decision session — not a research session.** Deep research (backfill, issuer intake, tuning) has its own slot outside the morning ritual.

---

## 1. DAILY SOP — MORNING RITUAL (±20 minutes, 07:00 WIB)

> Automatic prerequisite: scraper runs at 00:00, dashboard ready by 06:30.

**07:00 — Panel 1 · Data Snapshot (2 minutes)**
- [ ] Check `source_flags`: all green? If any are red → note which field; if that field is used in today's analysis (e.g. funding rate red while about to read BTC), mark the related analysis as LOW_CONFIDENCE for today.
- [ ] Glance at major anomalies (extreme daily deltas) — not to draw conclusions, just flag them to read in the next panel.

**07:02 — Panel 2 · News Briefing (3 minutes)**
- [ ] Read HIGH headlines first, then MED. Flag `key_trigger` ONLY for news that could genuinely change the lane — not every interesting piece of news.
- [ ] Long articles that need dissecting → put into `manual_articles` for a separate reading session, DO NOT spend the morning slot on them.

**07:05 — Panel 3 · Forward Panel (5 minutes)**
- [ ] Read in order: Expectations (FedWatch/Dot Plot) → Positioning (COT, ETF flow, IHSG FF) → latest Policy Tracker → calendar: how many days until the HIGH catalyst?
- [ ] Check the Dissonance Flag. If active → must be mentioned in the synthesis later.
- [ ] **Output of this step: today's LANE per active instrument** (bullish/bearish/neutral — bias, not entry).
- [ ] Open US stock position? → check the earnings countdown. Earnings D-1 = **close fully today** (locked decision #3), not tomorrow.
- [ ] HIGH event < 48 hours away & an open position exists → run the SL-to-breakeven rule per the SOP.

**07:10 — Panel 4 · Reading Workspace (5 minutes)**
- [ ] Run persona lenses AS NEEDED, not as a ritual of 4 cards every day:
  - Key-trigger news / nearby catalyst → run the relevant lens (Fed news → GEMA+AKELA; domestic policy → LEON; anomalous BTC movement → RIVAN).
  - Quiet day with no catalyst → zero calls is fine. An empty card is not a failure.
- [ ] Lens results = material, not a verdict. Conflict between lenses → write it in Conflict Notes, don't force a reconciliation.
- [ ] External AI output (if any) goes into External AI Check — compared against, not followed.

**07:15 — Panel 5 · Chart & Signal (3 minutes)**
- [ ] Check SUGGESTED signals. For each signal, run the gates in sequence:
  1. Instrument lane badge = TRADE/BOTH? (not INVEST/NONE/AVOID)
  2. S&R zone already `validated_by_giel`?
  3. Breakout + retest + volume per the rules (not a wick, volume present)?
  4. R:R ≥ 1.5?
  5. Lane from Panel 3 doesn't flatly contradict? (bearish lane + long signal = strong reason to reject/skip, logged)
  6. Calendar: no earnings (US stock) / HIGH event violating the hold rule?
- [ ] All pass → APPROVE. Any fail → REJECT with a one-sentence note. **There's no "approve later this evening after more thought"** — the decision happens this session or it's a reject.
- [ ] Approve ≠ execution. Execution = step §2 below.

**07:18 — Panel 6 · Synthesis (2 minutes)**
- [ ] Write a 1-paragraph synthesis IN YOUR OWN WORDS (not copied from lens results).
- [ ] Set the outlook per active instrument.
- [ ] Log AT MOST 1 prediction to `prediction_log` — only if there's actually a claim worth testing. An empty prediction is better than a careless one.
- [ ] Any old prediction due? Score it now (CORRECT/WRONG/PARTIAL) — don't defer it to "later".

**07:20 — Done.** Optional: send the Daily Briefing (Panel 6 button) if you want to publish the content.

### What is PROHIBITED during the morning session
- Opening Tab 8 (Universe & Grader) — that's a weekly/quarterly rhythm. Except for one thing: viewing the lane/quadrant badge that's already displayed automatically in Panel 5.
- Backfill, issuer intake, parameter tuning, reading long articles.
- Approving a signal that failed one of the gates "because it feels right".

### Quick Mode — 5-minute session (busy days)

> Full details + rationale: `docs/mode_ringkas_pwa_mobile_v1.md`. Principle:
> this application is a **habit engine**, not a replacement for heavy tools — its health
> metric is the **daily streak** (opened yesterday, and the day before), not
> feature completeness. Quick Mode keeps the daily chain from breaking on a day
> that only leaves 5 minutes — it is **not a replacement** for the full morning ritual above.

**[REQUIRED · ~1 minute]** — this alone = "the day isn't broken":
- [ ] Log 1 prediction OR score 1 due prediction (`prediction_log`)
  — the ONE thing that CANNOT be backfilled; a prediction not logged
  today is lost permanently.

**[CORE · ~2 minutes]** — if there's time:
- [ ] 10-second scan of morning data: any major anomaly? (look, don't analyze)
- [ ] Read HIGH news/briefing: anything changing today's lane? Flag
  `for_reading` if it deserves a serious read later.

**[BONUS · ~2 minutes]** — if genuinely relaxed:
- [ ] Confirm SUGGESTED tag/thread (click, no need to think hard).
- [ ] Check ONGOING positions: does any hit today's rule? (US stock
  earnings D-1 = close fully; HIGH event < 48 hours = SL breakeven.)

**NOT in Quick Mode** (wait for the laptop session): approve/reject signals,
sizing, running personas (LLM cost), long synthesis, backfill, settings,
grader override.

**Mental rule (habit anchor):** *"Even on the busiest day, I log or
score one prediction."* If that's all there was time for, the day is still a success —
the streak stays intact. Everything else can be caught up in the next laptop session.

**Honest limit:** Quick Mode is not a substitute for the full session, and does not
produce trade decisions (anti-impulsivity, not a bug). 5 consecutive days
of Quick Mode only = a signal to be honest about discipline vs. busyness (§7).

---

## 2. EXECUTION SOP (after approval — outside the application)

> The application stops at an approved signal + calculated size. Execution = Giel's hand at the broker. (Contract §15 — no broker API.)

**Crypto (exchange):**
- [ ] Place a buy limit at the signal's entry price + SL per the signal. Size from the sizing engine, without rounding up.

**IDX Stocks (Stockbit) — WIB market hours:**
- [ ] Size = result of lot quantization (rounded DOWN). If the signal is flagged skip `RISK_CAPACITY_EXCEEDED` → NOT executed, period. Shifting the SL to make the lot fit is prohibited.
- [ ] Remember the ARA/ARB buffer: real risk > SL distance. If the 1.5× buffer pushes total risk beyond the per-trade limit → skip, log it.

**US Stocks (IBKR) — placed midday/evening WIB:**
- [ ] GTC buy limit at the signal's entry price. Fractional shares allowed — sizing precision takes priority.
- [ ] Check the instrument's EARNINGS DATE before placing the order: if earnings fall before a reasonable swing horizon → consider skipping from the start, since the position must be fully closed before earnings.

**After execution (same day):**
- [ ] Fill in `trading_journal`: actual entry, planned_size vs actual_size, and (if skipped) skip_reason. The journal is filled in THAT DAY — a journal filled in retroactively is a fictional journal.

---

## 3. WEEKLY SOP — MONDAY SESSION (±20 minutes, outside the morning ritual)

- [ ] **Gold**: run the bracket trigger check per Saham Emas SOP Tab 01 (logammulia.com vs the database). If there's a trigger → execute the tranche per its SOP. The application doesn't manage this — it's just a place to log it if you want.
- [ ] **SBN foreign flow**: manual input into the Forward Panel (Layer C). Remember the rule: this is your own eyes' reading, it never goes into the persona slice.
- [ ] **Weekly COT**: the CFTC release is already ingested automatically — read the changes in large positions, especially if the Dissonance Flag was active last week.
- [ ] **Review ONGOING positions** in the journal: still consistent with the premise? Is the SL still in place (not shifted)? Earnings/HIGH event next week?
- [ ] **Tab 8 — glance at the universe**: any new integrity flags (UMA/suspension) on an issuer you hold or are watching? An issuer that becomes AVOID while you're holding it = an agenda item for evaluation that very day, not something to wait for the quarter.

---

## 4. MONTHLY SOP (±30 minutes, end of month)

- [ ] **Score predictions**: all predictions due this month are scored. Roughly calculate the hit-rate — if it keeps dropping, that's material for reflecting on your prediction basis, not a reason to stop logging them.
- [ ] **Review the journal**: read all trades + skips this month. Look for patterns of SOP violations (not market patterns): any SL shifted? Any trade without a signal? Any approval outside the morning session? A violation = write it in lesson_learned, regardless of the trade's outcome.
- [ ] **Data health check**: date gaps & NULL rate on key columns (pattern: a field that's long been red in source_flags). Systematic gaps → a scraper-fix task, not something to leave alone.
- [ ] **Invest lane — routine contribution**: run the monthly allocation per Investment SOP v4.1 (index mutual funds via Bibit/Bareksa, etc.). The application plays exactly one role here: check Panel 3/Tab 8 for context — BUT the low-point trigger from SOP v4.1 is what decides, not the persona lens. Personas don't govern routine saving.

---

## 5. QUARTERLY SOP (±1 hour, after earnings season)

- [ ] **Refresh fundamentals**: pull/input the latest quarter for the universe (J-4). Issuers with <8 quarters remain LOW_CONFIDENCE.
- [ ] **Re-run the grader** across the whole universe → review quadrant changes in Tab 8. A drastically changed quadrant → read its components, not just the badge.
- [ ] **Fill in grader_log outcomes** for grades that are 3/6 months old (component D widget). This is the ONLY session where revising the rubric weights MAY be considered — and only if the log shows a pattern, not because of one annoying case.
- [ ] **Review the universe**: any watchlist issuer moving up into the universe? Any universe issuer that has worsened for 2 consecutive quarters → downgrade its lane / remove it, logged with a reason.
- [ ] **Lane calibration**: an INVEST instrument moving up to TRADE → must pass bar-replay validation first (`lane_validated_at`), not just because "it's been watched for a long time".
- [ ] **Review this SOP itself**: any step that hasn't been run in 3 consecutive months? Remove or fix it — an ignored SOP is more dangerous than no SOP at all.

---

## 6. INVEST LANE SOP — THE APPLICATION'S ROLE (summary)

The invest lane lives in SOP v4.1 + Saham Emas SOP. The application's role is only to:
1. **Quality filter**: individual-stock saving candidates must pass the grader (Tab 8) — an AVOID quadrant is not bought for any lane, including invest. INVESTABLE/WATCH = may be considered under the invest SOP.
2. **Cycle context**: Panel 3 (net liquidity, DXY, foreign flow) as a "season" reading — enriching the tranche decision, NOT overriding the invest SOP's objective triggers. Drawdown in real assets during dollar strength = forced-selling mechanics, not a reason to change allocation (a financial-repression principle already held).
3. **Intake**: an interesting new issuer → the Tab 8 intake path (component C), grade it first, then it enters the consideration list. No buying-because-of-news without going through intake.
4. **Recording**: invest transactions are recorded (journal/sheet per the asset's SOP) — the application is not a replacement for the invest SOP's existing recording process.

PROHIBITED: using `trade_signals` for timing invest purchases, and using invest triggers to justify a trade. Two lanes, two logics, one cross-prohibition.

---

## 7. ABNORMAL CONDITION PROTOCOL

| Condition | Protocol |
|---|---|
| Total scraper failure (many red) | The morning ritual still runs but WITHOUT any new signal decisions that day. Fixing the scraper = an afternoon task, not a morning panic. |
| A signal appears but Giel is emotional (just took a loss, revenge mood) | Reject it or leave it without a decision until tomorrow morning. A valid signal will remain valid; the feeling of "must act now" is an emotional signal, not a market signal. |
| Position hits SL | Execute the cut per the rule (D1 close below the zone). Fill in the journal that day + lesson. Opening the chart to look for a new entry on the same instrument on the same day is PROHIBITED. |
| ARB for several days (can't exit) | Place a sell queue every day at the best available price, log it in the journal each day. This is the exact scenario the 1.5× buffer anticipates — not a system failure. |
| Wanting to change a rule (SL, weights, threshold) | Write the proposal + reasoning, SLEEP ON IT ONE NIGHT, review it when there's no open position in the related instrument. Changes only happen through a revision of the SOP/contract document, never through a "just this once exception". |

---

# PART B — HOW TO READ EACH PANEL (reference dictionary)

> The principle that applies throughout this entire section: **numbers = material, not a verdict.**
> The "how to read" column below explains the general meaning of a movement — NOT a
> buy/sell command. Decisions still go through the gate (§0 point 2). One field
> moving rarely means anything on its own; what you're looking for in the synthesis is
> **several fields telling the same story** (confirmation) or **contradicting each other**
> (dissonance — which is actually the interesting part).

## 8. PANEL BY PANEL

### 8.1 Panel 1 · Market Snapshot
Each card = 1 latest number + **delta** (comparison vs Day/Week/Month/
Year, chosen in the dropdown above). Green ▲ = up, red ▼ = down. The delta is what
matters, not the absolute number.

**Crypto Group (BTC):**

| Item | Meaning | How to read its movement |
|---|---|---|
| **BTC Close** | BTC closing price | Up = bullish price momentum. Always cross-check against volume & funding below — price up without volume = weak. |
| **BTC Vol MA20** | 20-day average volume | Today's volume far > MA20 = high participation (breakout/news). Below MA20 = quiet market, the move is less trustworthy. |
| **BTC Dominance %** | BTC's share of market cap vs total crypto | Up = money flowing into BTC (risk-off within crypto / altcoins abandoned). Down = "altseason", risk-on. |
| **Funding Rate** | Perpetual futures cost | **Positive** = longs pay shorts → crowd is LONG (prone to a long-squeeze if extreme). **Negative** = shorts pay longs → crowd is SHORT. Extreme on one side = a signal positioning is too crowded. |
| **Aggregate OI** | Open interest (total open contracts) | Up + price up = new money coming in (healthy trend). Up + price flat = leverage building up (risky). Down = positions closed/liquidated. |
| **Long/Short Ratio** | Ratio of long : short accounts | > 1 = majority long. Extremely high = crowd on one side, contrarians often turn cautious. |
| **Liquidation Long 24h** | Notional LONGs forced to close (price dropping) | Large = a fresh forced-selling cascade → often a wash-out / local reversal point. |
| **Liquidation Short 24h** | Notional SHORTs forced to close (price rising) | Large = short-squeeze → part of the upward push is "forced fuel", not organic demand. |

**Global Macro Group:**

| Item | Meaning | How to read its movement |
|---|---|---|
| **DXY** | US dollar index | Up = strong dollar → pressure on risk assets, gold, EM (including IHSG/rupiah), often BTC too. Down = pressure easing. This is the macro "gravity" most often used. |
| **US10Y %** | 10-year US treasury yield | Up = cost of capital rising, pressure on long-duration/growth assets/gold. Down = the opposite. |
| **VIX** | Volatility index (S&P "fear index") | > 20 starting to get uneasy, > 30 = panic. Sharp rise = risk-off. Low & flat = calm/complacent market. |
| **Fear & Greed** | Crypto sentiment 0–100 (+ label) | < 25 Extreme Fear, > 75 Extreme Greed. Contrarian: extreme greed = beware of euphoria; extreme fear = often near a bottom. |
| **Net Liquidity** | Fed liquidity = WALCL − RRP − TGA | Up = liquidity flowing into the system (tailwind for risk assets). Down = tightening. A slow "seasonal" reading, not a daily trigger. |

**Equity & FX Group:**

| Item | Meaning | How to read its movement |
|---|---|---|
| **S&P 500** | US market | Proxy for global risk-on/off. Up = positive global risk appetite. |
| **IHSG** | Indonesian market | Cross-check against foreign flow (Panel 3): IHSG up + foreigners selling = propped up by locals (less solid). |
| **USD/IDR** | Rupiah per dollar | Up = rupiah **weakening** (capital-outflow pressure). Down = rupiah strengthening. |
| **USD/JPY** | Yen per dollar | Proxy for global carry trade; a fast spike often coincides with a risk-off shock. |
| **Gold** | Gold | Rising while DXY & yields fall = the classic pattern. Rising ALONGSIDE a strong dollar = a signal of stress/safe-haven demand (see the Saham Emas SOP). |

**Data Source Status (source_flags):** open the collapsible section below the card.
🟢 ok / 🟡 skip / 🟠 stale / 🔴 fail per source. **`stale`** (specific to
`fred_dxy`/`fred_us10y`/`fred_vix`/etc.) = the fetch SUCCEEDED but the FRED
observation obtained is older than the reasonable limit (`MAX_LAG_DAYS`,
`scrapers/macro_fred.py`) — different from `fail`. The number on the card is still
shown (stale is still more useful than empty), but don't read it as
"today" — check the actual observation date if unsure. A field you
need today is red (fail) OR orange (stale) and is critical → the analysis
depending on it is LOW_CONFIDENCE / postponed (§0 point 3), not guessed.

> **Manual Backfill** on this panel = a tool for filling historical data gaps, NOT a
> daily reading. Gap info appears per instrument when you switch the dropdown; "Check &
> Preview All Gaps" checks all instruments at once. This is research-session work (§0 point
> 4), not the morning ritual.

### 8.2 Panel 2 · News
| Column | How to read |
|---|---|
| **Impact HIGH** | Potentially lane-moving (Fed, CPI, BI rate, major geopolitics). Read first. |
| **Impact MED** | Important context, rarely changes direction on its own. |
| **Impact LOW** | Background / noise. Skip during the morning. |
| **🚩 Key button** | You mark this yourself. **ONLY** for news that could genuinely change the lane — this is what appears in Panel 4 as material for the 4 lenses. Don't flag everything that's interesting (§1 07:02). |

> Impact here is rule-based (keywords), not AI — treat it as a rough
> sorter, the final judgment is still your own eyes. Long articles that need dissecting →
> `manual_articles`, not spent in the morning slot.

### 8.3 Panel 3 · Forward
This is the "what's waiting ahead" panel. Read in order: Calendar → Expectations →
Positioning → Policy → Dissonance.

**Economic Calendar** — upcoming economic events (automatic via ForexFactory; `actual`
is filled automatically by the evening investing.com pass or manually).

| Column | How to read |
|---|---|
| **Importance HIGH** ("3-star") | Heavy-class catalysts (CPI, FOMC, NFP, BI board meeting). Default table filter = HIGH only. Toggle "HIGH + MED" to see everything. |
| **Countdown (D-n)** | How many days away. This is the trade's **time axis**: "what catalyst, how many days away". HIGH event < 48 hours + an open position → SL-to-breakeven rule (§1 07:05). |
| **Forecast vs Previous** | Consensus expectation vs the previous release. Direction of change = the market's expectation. |
| **Actual** | The released result. **What moves the market is Actual vs Forecast**, not Actual alone. Actual far above forecast (e.g. **Core CPI** actual 0.4% vs forecast 0.2%) = inflation hotter than expected → hawkish → pressure on risk assets. "Core" = excluding food & energy (the core inflation trend). |

**Expectations (Layer B — manual):**
- **CME FedWatch cut probability** — market probability (0–1) of a rate cut at
  the next meeting. 0.72 = the market prices in a 72% chance of a cut. Rising = expectations
  turning more dovish.
- **Fed Dot Plot median** — the FOMC's median interest-rate projection. Read as
  the medium-term direction.
- *Filled manually* — the official API is paid (see the panel note).

**Positioning (Layer C):** who holds what position.
- **COT** (automatic) — speculators' net positions in BTC/DXY/GOLD/SP500. Extreme
  net-long = crowd on one side.
- **BTC ETF net flow** (automatic) — ETF inflows/outflows. Positive for several days =
  institutional demand.
- **IHSG foreign flow** (automatic) — positive `foreign_net_buy_value` = foreigners are
  net buying. Cross-check against IHSG in Panel 1.
- **SBN foreign flow** (manual, weekly) — foreigners in government bonds. This is
  **your own eyes' reading, NEVER goes into the persona slice** (§3).

**Policy Tracker (Layer A):** what central bank officials say.
| Column | How to read |
|---|---|
| **Literal statement** | What was ACTUALLY said (a quote). Fact. |
| **Stance score −2..+2** | Your own assessment: −2 very dovish (loose) … +2 very hawkish (tight). |
| **Inference** | A reading of direction/intent — **subjective, your own guess**. |
| **TESTABLE / SPECULATIVE flag** | Be honest: can this inference be tested later (TESTABLE) or is it just a guess (SPECULATIVE)? |
| **Drift note** | Changed from the previous statement? A tone shift is a signal. |

**Dissonance Flag:** compares **Policy Tracker stance** vs **DXY COT
positioning**. `ALIGNED` = rhetoric & positioning move together. `DISSONANCE` = they conflict
(e.g. officials hawkish but dollar-bet positioning weakening) — **must be mentioned in the
synthesis** (§1 07:05). Requires stance_score filled in + ≥ 2 DXY COT rows; if
not yet available → "not enough data yet".

### 8.4 Panel 4 · Reading
| Section | How to read / use |
|---|---|
| **Today's Key News** | What you flagged 🚩 in Panel 2. Raw material for the 4 lenses. Empty = flag it in Panel 2 first. |
| **4 Analyses (AI)** | The 4 persona lenses (labels: Global & Capital Flow, Domestic Policy & System, Market Dynamics & Timing, Fundamentals & Realist). Click "Run" per card AS NEEDED — not a ritual of 4 cards every day (§1 07:10). Quiet day = zero is fine. |
| **Lens results** | **Material, not a verdict.** Lenses contradicting each other is normal → write it in Conflict Notes, don't force a reconciliation. |
| **External AI Check** | Paste external AI comparison results (optional). Compared against, NOT followed. |
| **Conflict Notes** | Points the lenses haven't agreed on. This is actually the most valuable material for the synthesis. |

> A card marked "Prompt not yet filled in" = the `prompts/persona_*.txt` file is empty;
> that lens can't run until the prompt is written.

### 8.5 Panel 5 · Chart
**Reading the candlestick chart:**
- **Green candle** = close ≥ open (up), **red** = down. Wick = high–low, body = open–close.
- **MA lines** — MA50 (yellow), MA100 (purple), MA200 (pink). Price above MA200 = bullish long-term structure; a short MA crossing above a longer MA = strengthening momentum. Color legend is in the chart header.
- **Volume bars** (bottom) + blue line = MA20 volume. A breakout **must** be accompanied by volume above MA20 — if not, be suspicious.
- **S&R zones** — box **green = SUPPORT**, **red = RESISTANCE**. The chart meta shows how many zones are active (near the price). A zone only counts as a valid signal gate once you've validated it (`validated_by_giel`).
- **Signal markers** — **filled green circle = BREAKOUT**, **empty blue circle = RETEST**, at the entry point.

**Range** (dropdown): 1 month … All. **Lane badge** in the header (TRADE/BOTH/
INVEST/NONE) = whether this instrument may be traded.

**Signal Table (Breakout/Retest):**
| Column | How to read |
|---|---|
| **Type** | BREAKOUT (zone broken through) / RETEST (zone re-tested). |
| **Entry / SL / TP1** | Suggested prices from the engine. |
| **R:R** | Risk-reward. **Mandatory gate ≥ 1.5** (§1 07:15). Below that = reject. |
| **Status** | pending / APPROVED / REJECTED. Approve/Reject here runs the 6-step gate (§1 07:15). **Approve ≠ execution.** |

**Context Charts (30 days):** mini-lines for DXY, S&P 500, US10Y, Fear & Greed —
quick macro context without switching panels. Green = up over the period, red = down.

### 8.6 Panel 6 · Synthesis
This is where all the readings above become ONE decision. Fill-in order:

| Section | How to fill it in |
|---|---|
| **Daily Synthesis** | 1 paragraph **written by hand yourself** (not copied from lens results). Change the date to read/edit another day. |
| **Outlook per Instrument** | Set Bullish/Bearish/Neutral per active instrument. This is bias, not entry. |
| **Trading Journal** | Log the trade THAT DAY (a retroactive journal = fiction, §2). The **Calculate Size** button = the sizing engine (Phase J+ universe only): give it Entry+SL, it outputs `suggested_units`. `SKIP — RISK_CAPACITY_EXCEEDED` = budget insufficient for 1 lot → **not executed**, don't shift the SL. A note on the 1.5× ARA/ARB buffer appears if applied (real risk > SL distance). |
| **Prediction Log** | MAX 1 prediction/day, only if there's a claim worth testing. Fill in the claim + target date + basis. An empty prediction > a careless one. |
| **Due Prediction Score** | An old prediction comes due → score it CORRECT/WRONG/PARTIAL now, don't defer it. |
| **Daily Briefing → Telegram** | Optional, after Panels 4–6 are filled in. Assembled from data that ALREADY exists, not generated on its own. |

**Checklist of "what should I analyze" when you reach the synthesis:**
1. **Macro direction** (Panel 1): DXY & yields up/down? That's today's gravity.
2. **Catalysts ahead** (Panel 3): how many days until the HIGH event? Did last night's actual vs forecast change anything?
3. **Crowd positioning** (Panel 1 funding/LS + Panel 3 COT): is anything too crowded on one side?
4. **Dissonance** (Panel 3): rhetoric vs positioning conflicting? If so, that's the synthesis headline.
5. **Price structure** (Panel 5): where is the price relative to MA200 & the zones? Any valid signal?
6. **Lens conflict** (Panel 4): what hasn't been agreed on? Don't hide it.
7. Pull it into 1 paragraph + outlook. If key data is red/missing → write down
   the uncertainty, don't polish it over.

---

# PART C — INVESTING LANE ("Investing" & "Archive" sidebar)

> The sidebar used to be called **"Universal"** (confusing) → now split into
> **"Investing"** (the Universe page — the stock-investment lane) and **"Archive"**
> (the History page — cross-lane track record). Both are **weekly/
> quarterly rhythm**, not daily (§0 point 1). Prohibited to open during the morning
> ritual except to view the lane/quadrant badge (§1 "What is PROHIBITED").

## 9. THE "INVESTING" PAGE (Universe & Grader)

### 9.1 How to READ the Universe table
| Column | How to read |
|---|---|
| **Ticker / Sector / Market** | Issuer identity (IDX/US). |
| **Lane** | TRADE / BOTH / INVEST / NONE — which lane(s) it may be used in. New instruments **may only be INVEST/NONE** until they pass bar-replay validation (§9.5). |
| **Validated** | Date the lane was signed off via bar-replay. Empty = never done → don't TRADE it. |
| **Quadrant** | The two-axis grader result (see §9.3). "not yet graded" = run the Eligibility Test first. |
| **Score** | Raw `fund_score` (fundamental). Read its components in Detail, not just the number. |
| **Flags** | Number of integrity flags (UMA/suspension etc.). > 0 = there's a note, open the detail. |

### 9.2 How to FILL IN — new issuer intake flow (in order)
1. **+ Intake Candidate (Wave 1)** — basic metadata (ticker, market,
   sector, mcap, free float, lot size, is it financial?, daily ARA/ARB limit?). Lane
   from here **must be INVEST/NONE**. This only registers it, doesn't grade it yet.
2. **Eligibility Test (Wave 2)** — 3 sequential steps:
   - **1. Integrity Check (UMA)** — scrape the IDX UMA flag. `UMA_ACTIVE` = an
     active unusual-activity warning → be careful.
   - **2. Run Grade** — compute `fund_score` + quadrant + flags.
   - **3. Log Decision** — Add to Universe / Watchlist / Reject + **reason
     required**. Logged in the Intake Decision History.
3. **Same rubric as the existing universe** — no special-case path.

### 9.3 Reading the Grader Quadrant
Two axes: **fund_score** (fundamental quality) × **integrity flags** (clean/
problematic).
- **INVESTABLE** — strong fundamentals + clean. May be considered under the invest SOP.
- **WATCH** — worth monitoring, not yet fully qualified.
- **SPECULATIVE** — has some appeal but flags/quality aren't convincing yet.
- **AVOID** — **not bought for any lane**, including invest (§6 point 1).
  An issuer that becomes AVOID while being held = an agenda item for evaluation that very day.

The engine gives the quadrant; if you disagree → **Override** (requires a reason).
The override shows as a separate badge, the engine's quadrant is still saved.

### 9.4 Issuer Detail (Component B)
Adaptive fundamentals table:
- **Regular issuer:** Revenue, Net Income, OCF (operating cash flow), FCF (free
  cash flow) per quarter.
- **Financial issuer (bank):** Net Income, **CAR** (capital adequacy, the higher
  the stronger), **NPL** (non-performing loans, the lower the healthier), **NIM** (net interest
  margin), **LDR** (loan-to-deposit ratio).
- **Confidence** per row: < 8 quarters = LOW_CONFIDENCE (data too short).

### 9.5 Lane Validation (Bar-Replay Sign-off)
"An engine tested on BTC ≠ tested on BBRI" (Contract §13.1). A lane moves up to TRADE/BOTH
**only** after you yourself have reviewed that issuer's historical chart
(manual bar-replay, in Panel 5), then **recorded** the conclusion here. This form only
RECORDS — there's no automatic validation. Evidence is required (what was checked &
the conclusion). Its history shows in "Lane Validation History".

### 9.6 Bank Ratios (Manual)
CAR/NPL/NIM/LDR **aren't available in yfinance** → filled in manually from official
reports (OJK/annual reports). Won't be overwritten by automatic backfill. Specific to
financial issuers.

### 9.7 Grader Log & Calibration (Component D)
The "Score Outcome" widget for grades that are 3/6 months old (same pattern as the Prediction Score).
**Revising the grader rubric weights ONLY through this log** (if the log shows a PATTERN,
not because of one annoying case) — the quarterly session §5.

## 10. THE "ARCHIVE" PAGE (History) — how to read
Track record, read during review (§3/§4), not filled in here (entry happens in
the source panel). 4 sub-tabs:
- **Synthesis** — archive of daily conclusions. Read your own thinking patterns over time.
- **Predictions** — track record of claims + outcomes (CORRECT/WRONG/PARTIAL) + lesson.
  A steadily declining hit-rate = material for reflecting on your prediction basis (§4).
- **Trading Journal** — every entry & SKIP. Look for patterns of **SOP violations** (SL
  shifted? trade without a signal? approval outside the morning session?), not market patterns (§4).
- **4 Lenses** — archive of persona results by date.

---

*Application Usage SOP v1.1 — Part A (rhythm) + Part B (how to read panels) +
Part C (Investing lane). Reviewed together with the quarterly SOP (§5 last point).
This document governs panel rhythm & literacy; asset rules stay in their own SOPs.*
