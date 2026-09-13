# Kastara Finance — Seed Tags & Threads (Init)

Used to populate `tag_dictionary` and propose initial threads, so Giel
doesn't start from an empty dictionary. Tags = seeded in full (vocabulary,
safe to over-include). Threads = candidates only (manual activation, respect
the 7-ACTIVE limit). Principle being maintained: tags are descriptive
(non-directional), threads are directional (they have a `current_read` that
can be wrong). All tags are lowercase, `-` for spaces, `sym:` requires a
region prefix.

Imported via `pipeline/seed_tags.py` (`python -m pipeline.seed_tags`).
**Jul 17, 2026**: run once with candidate threads B–H as **DORMANT** (not
ACTIVE) — the production DB already has 5 ACTIVE threads with their own
titles/direction that differ from the generic candidates here (e.g. "Warsh
Dovish Regime" vs. Candidate A's "Hawkish"), so no candidate was
auto-activated. `who:purbaya` was DELIBERATELY skipped from the seed (see
Usage Rules #3 — title/spelling not yet verified).

## PART 1 — SEED TAGS (goes directly into `tag_dictionary`)

### facet: geo (geography)

```
geo:us          United States
geo:id          Indonesia
geo:cn          China
geo:eu          European Union / eurozone
geo:jp          Japan
geo:uk          United Kingdom
geo:in          India
geo:global      cross-country / global
geo:asia        Asia region (regional)
```

### facet: org (institutions)

```
org:fed         Federal Reserve
org:fomc        FOMC (Fed policy committee)
org:bi          Bank Indonesia
org:ojk         OJK (Indonesia Financial Services Authority)
org:kemenkeu    Ministry of Finance of Indonesia
org:gov-id      Government of Indonesia (executive)
org:pboc        People's Bank of China
org:ecb         European Central Bank
org:boj         Bank of Japan
org:imf         IMF
org:worldbank   World Bank
org:comex       COMEX
org:lbma        LBMA
org:idx         Indonesia Stock Exchange (institution)
```

### facet: who (figures)

```
who:warsh       Kevin Warsh (Fed Chair)
who:powell      Jerome Powell
who:waller      Christopher Waller
who:williams    John Williams (NY Fed)
who:logan       Lorie Logan (Dallas Fed)
who:trump       Donald Trump
who:prabowo     Prabowo Subianto
who:purbaya     (Indonesian fiscal/monetary official — adjust as needed;
                 SKIPPED during the Jul 17, 2026 seed, title/spelling
                 not yet verified)
```

### facet: sym (instruments — region-prefix REQUIRED)

```
sym:btc         Bitcoin
sym:eth         Ethereum
sym:xau         Gold (gold spot)
sym:dxy         US Dollar Index
sym:us10y       US Treasury 10Y
sym:vix         VIX
sym:sp500       S&P 500
sym:idx         IHSG (index)
sym:usd-idr     USD/IDR
sym:usd-jpy     USD/JPY
sym:id-bbca     BBCA
sym:id-bbri     BBRI
sym:id-bmri     BMRI
sym:id-tlkm     TLKM
sym:us-tsla     Tesla
sym:us-nvda     Nvidia
sym:us-aapl     Apple
```

### facet: theme (policy/market theme — descriptive, non-directional)

```
theme:rate-policy       interest rate policy
theme:inflation         inflation / CPI / PCE / PPI
theme:foreign-flow      foreign capital flows
theme:liquidity         liquidity (net liquidity, QT/QE)
theme:geopolitics       geopolitics / conflict / sanctions
theme:fiscal            fiscal policy / budget / deficit
theme:earnings          corporate earnings / earnings season
theme:commodities       commodities (energy, metals, food)
theme:currency          exchange rate / forex
theme:credit            credit / spreads / bonds
theme:employment        employment / NFP / unemployment
theme:trade             trade / tariffs / trade balance
theme:crypto-regulation crypto regulation
theme:etf-flow          ETF flows (BTC/gold)
```

### facet: sec (sector — for individual stocks, Phase J)

```
sec:banking         banking
sec:consumer        consumer / retail
sec:energy          energy
sec:mining          mining
sec:automotive      automotive
sec:technology      technology
sec:property        property
sec:telco           telecommunications
sec:healthcare      healthcare
sec:industrials     industrials
```

## PART 2 — CANDIDATE THREADS (do NOT activate all — pick the ones actually being tracked)

Each candidate already has a `current_read` (which can be wrong) +
`persona_tags` + initial `tags`. Activate AT MOST 7. Leave the rest as notes
until they become relevant.

### Candidate A — "Warsh Hawkish Regime" ⭐ (already active — keep)

```
current_read : The Fed under Warsh is moving tighter; a hike is still on the table.
persona_tags : GEMA, AKELA
tags         : who:warsh, org:fed, org:fomc, theme:rate-policy, geo:us
```

### Candidate B — "Global Inflation Not Yet Tamed" ⭐ (recommended to activate)

```
current_read : Cross-country inflation is still above target; rate pressure has not eased.
persona_tags : GEMA, AKELA
tags         : theme:inflation, geo:global, geo:us, geo:in, geo:cn
```

### Candidate C — "Foreign Outflow from the IHSG"

```
current_read : Foreigners are net distributing from Indonesian equities; domestic investors are absorbing it.
persona_tags : GEMA, LEON
tags         : theme:foreign-flow, sym:idx, sym:usd-idr, geo:id
```

### Candidate D — "Prabowo's Fiscal Direction"

```
current_read : The new administration's fiscal direction is expansionary; impact on the deficit & government bonds (SBN).
persona_tags : LEON
tags         : who:prabowo, org:gov-id, org:kemenkeu, theme:fiscal, geo:id
```

### Candidate E — "BI vs. The Fed (Policy Divergence)"

```
current_read : BI is squeezed between defending the IDR and supporting growth while the Fed is hawkish.
persona_tags : GEMA, LEON
tags         : org:bi, org:fed, theme:rate-policy, sym:usd-idr, geo:id
```

### Candidate F — "De-dollarization / Central Bank Gold"

```
current_read : Non-Western central banks are accumulating gold, moving away from the dollar.
persona_tags : GEMA, RIVAN
tags         : theme:commodities, sym:xau, org:pboc, org:comex, geo:global
```

### Candidate G — "AI Capex Bubble"

```
current_read : Mega-cap AI spending will not produce commensurate profit; a correction awaits.
persona_tags : AKELA, RIVAN
tags         : theme:earnings, sec:technology, sym:us-nvda, geo:us
```

### Candidate H — "Financial Repression 2026" (Giel's umbrella thesis thread)

```
current_read : Inflation erodes real debt; real assets become the recipients of wealth transfer.
persona_tags : GEMA, RIVAN
tags         : theme:inflation, theme:liquidity, theme:fiscal, sym:xau, geo:global
note         : Long-term thesis thread — be careful it doesn't become a confirmation funnel.
               This thread, of all of them, most needs the discipline of recording COUNTER-evidence.
```

### CONVERSION NOTES (from Giel's old threads that should have been tags)

```
"The Fed"              → NOT a thread. Becomes tag org:fed (+ org:fomc).
"IHSG"                 → NOT a thread. Becomes tag sym:idx (+ theme:foreign-flow).
"Indonesian Government" → NOT a thread. Split into: org:gov-id + who:prabowo.
                          If you want a thread, use Candidate D (directional).
```

> **Note, Jul 17, 2026**: the conversion above was written assuming generic
> old thread titles ("The Fed", "IHSG", etc.). When the seed was actually
> run, the production DB turned out to already have 5 ACTIVE threads with
> their OWN titles & thesis direction (e.g. "Warsh Dovish Regime", "IHSG
> Strengthening, Stocks Bullish") that don't map 1:1 onto this assumption —
> the manual conversion (if it's actually wanted) is Giel's own decision to
> make via Settings, NOT something run automatically by `seed_tags.py`
> (this script never touches/closes existing threads, it only adds tags &
> new DORMANT candidates).

## USAGE RULES

1. Import all of Part 1 into `tag_dictionary` (safe to over-include).
2. Activate Candidates A + B first (most relevant to current news). Add
   C–H only when their narrative is actually being tracked. Max 7 ACTIVE.
3. `who:purbaya` and a few other entries: verify title/spelling at seed
   time — don't use if unsure.
4. New tags are still born from usage (type-Enter in News). This seed is
   just a starting point, not the final dictionary.
