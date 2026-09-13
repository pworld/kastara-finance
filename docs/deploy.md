# Kastara Finance — Deployment & Mobile Access Strategy
**Version:** 1.0 · July 12, 2026 · Owner: Giel
**Position of this document:** governs WHERE the system runs and WHICH functions may be accessed from which device. Not a detailed UI spec — that's a derivative once the decisions here are made.
**References:** Master Plan v1.6 (§0 spine, §5 pipeline), Application Usage SOP v1.0 (§1 morning ritual, §7 protocol), ARCHITECTURE.md §6.1 (SQLite single-writer).

---

## 0. PRINCIPLE — THIS ISN'T ABOUT SCREEN SIZE

The right question isn't *"Telegram or mobile-friendly?"* but **"which function is allowed to leave the desk?"**

Some functions are deliberately designed to need ritual, not speed. Moving them to a phone isn't an accessibility improvement — it's a **removal of friction that was actually intentional.**

```
DELIBERATE FRICTION (do not remove):
├── 6-step signal-approve gate  → designed as a conscious 3 minutes in the morning session
├── Grade override + mandatory reason   → designed to be reflective
├── Backfill preview-before-commit  → designed to be careful
└── Settings/tag dictionary curation       → designed to be slow (contract §21.11)

UNNECESSARY FRICTION (may be removed):
├── Having to sit at the desk just to READ a briefing
├── Having to wait until getting home just to SAVE an article you found
└── Having to open the laptop just to VIEW a thread timeline
```

**Derived rule:** what's allowed on the phone is **reading** and **capturing**. What's not allowed is **deciding**.

---

## 1. FUNCTION × DEVICE MATRIX

| Function | Telegram | Mobile Web | Desktop | Reason |
|---|---|---|---|---|
| Read the Daily Briefing | ✅ primary | ✅ | ✅ | Push, zero infra, already exists (`send_briefing.py`) |
| Check scraper status / morning data | ✅ summary | ✅ | ✅ | Purely read-only |
| Save an article from outside (send a URL) | ✅ primary | — | ✅ | **The most genuine phone use case** → `manual_articles` |
| Read the thread timeline | — | ✅ | ✅ | Needs layout, doesn't need a decision |
| Read the latest persona output | — | ✅ | ✅ | Read-only |
| Read the journal / ONGOING positions | — | ✅ | ✅ | Read-only |
| Confirm a SUGGESTED tag | — | ✅ light | ✅ | Reversible, not a money decision |
| Confirm a thread link + stance | — | ⚠️ allowed | ✅ | Reversible; but stance ideally isn't rushed |
| Set `for_reading` | — | ✅ | ✅ | Light curation, reversible |
| **Approve/reject a signal** | ❌ | ❌ | ✅ **ONLY** | 6-step gate = conscious ritual (SOP §1) |
| **Sizing / execution** | ❌ | ❌ | ✅ ONLY | Money decision |
| **Grade override** | ❌ | ❌ | ✅ ONLY | Reflective + mandatory reason |
| **Backfill / seed** | ❌ | ❌ | ✅ ONLY | Preview-before-commit |
| **Settings (tag dictionary, merge, thread status)** | ❌ | ❌ | ✅ ONLY | Slow curation (§21.11) |
| **Run persona (LLM cost)** | ❌ | ⚠️ optional | ✅ | Cost savings + avoid idle clicks |

**Enforcement note:** for ✅ ONLY functions, the decision endpoint is **not rendered at all** in the mobile view — not merely hidden via CSS. If the button doesn't exist, there's no temptation.

---

## 2. DECISION: TELEGRAM *AND* MOBILE WEB (not either/or)

The two have different, non-overlapping roles:

**Telegram = the PUSH & CAPTURE channel**
- Already exists (`notify/telegram.py`, `send_briefing.py`) — zero new infra.
- Good for: morning briefing, data-failure alerts, sending an article URL to the bot.
- **Limit:** don't build a "dashboard in Telegram" (inline keyboard for approve, etc.). Chat isn't the place to make risky decisions, and a large set of bot commands ends up more cumbersome than the web anyway.

**Mobile Web = the DEEP READING channel**
- One separate view `/m`, **not** making all seven tabs responsive.
- Content is just 3 things: (a) today's news feed + light tag/thread confirmation, (b) active thread timeline, (c) latest persona output + ONGOING position journal.
- Reason for a separate view: polishing all 7 tabs to be responsive = a big effort on the 70% (commodity) component — see Competitive Mapping §C1. A minimal `/m` view is much cheaper and better targeted.

---

## 3. DEPLOYMENT & SECURITY (the most critical section)

> **Warning:** `web/app.py` currently has **no authentication**, and since Phase C has write endpoints. Exposing it to the public internet as-is means anyone who finds the URL can write to the database.

### 3.1 Recommendation: a private network, not a public exposure

| Option | How it works | Pros | Cons |
|---|---|---|---|
| **Tailscale / WireGuard** ⭐ | The app stays on your own machine; the phone connects via a private VPN mesh | **Zero open ports**, zero auth code, one evening to set up, free for personal use | Needs an active VPN app on the phone |
| Cloudflare Tunnel + Access | Outbound tunnel; auth at the Cloudflare layer | No VPN needed on the phone; email/SSO auth | Traffic goes through a third party; more setup hassle |
| VPS + reverse proxy + own auth | Move the app to a VPS | Always online even if the laptop is off | **Requires building auth**, HTTPS, hardening — the biggest burden |
| ~~Expose port + basic auth~~ | Router port forward | — | ❌ **AVOID.** Risky, easy to misconfigure |

**Recommended decision:** start with **Tailscale**. Reason: it solves the phone-access problem without writing a single line of auth code, and without moving the database. If always-online becomes necessary later (laptop often off), then consider a VPS — and at that point auth becomes a prerequisite, not optional.

### 3.2 Hard rule: ONE DATABASE
```
❌ DON'T: run a local DB on its own + a VPS DB on its own, then sync them.
✅ ALWAYS: one DB file, one location. Moving = moving everything.
```
The **single-writer** assumption in ARCHITECTURE.md §6.1 and FLOW.md §5 immediately collapses if two active copies exist. SQLite conflicts are painful and often only discovered after days of corrupted data.

**If moving to a VPS later:** the scraper cron moves too (don't have a local scraper writing to the VPS DB over the network). This is also a logged trigger for revisiting SQLite → Postgres (ARCHITECTURE §6.1).

### 3.3 Checklist before accessing from outside
```
[ ] Tailscale installed on the host machine + phone, connection verified
[ ] Flask bound to the Tailscale interface / localhost — NOT public 0.0.0.0
[ ] Automatic DB backup before starting remote access (SQLite file, copied daily)
[ ] Verify: from an outside network WITHOUT the VPS/VPN, the dashboard CANNOT be opened
[ ] .env (OpenRouter API key, etc.) is not exposed within a static directory
```

---

## 4. EXECUTION ORDER (cheapest first)

```
STAGE 1 — ACCESS (one evening, ZERO code)
[ ] Tailscale setup + checklist §3.3
[ ] Open the desktop dashboard as-is from the phone
[ ] USE for 1–2 weeks. Note: which functions are genuinely needed outside?
    (don't guess — let actual usage tell you)

STAGE 2 — TELEGRAM (small, high value)
[ ] Morning briefing via Telegram (already exists — make sure the schedule is right)
[ ] Bot handler: send URL → save to manual_articles
[ ] (optional) Alert on total scraper failure

STAGE 3 — /m VIEW (only for what's PROVEN to be used often in Stage 1)
[ ] Read-only /m route: news feed, thread timeline, latest persona, journal
[ ] Tag/thread confirmation + for_reading (light write, reversible)
[ ] Decision endpoints NOT rendered in this view
[ ] Test: make sure no approve/backfill/settings path leaks into /m

STAGE 4 — VPS (only if always-online is needed)
[ ] Prerequisite: real auth, HTTPS, automatic backup
[ ] Move DB + cron ALL together (rule §3.2)
[ ] Revisit SQLite → Postgres if a parallel writer emerges
```

---

## 5. RISKS BEING MONITORED

| Risk | Early sign | Mitigation |
|---|---|---|
| **Morning ritual erodes** | Starting to think "reading the briefing on the phone is enough" and skipping the desktop session | The briefing is a reminder, not a replacement. If the desktop session is missed 3 days in a row, that's not a UI problem — it's a discipline problem (SOP §7) |
| **Decisions creep onto the phone** | The urge appears to "just approve quickly from the phone" | The endpoint doesn't exist on /m. If tempted to add it, re-read SOP §7 + Experience Vision Part 4 |
| **Two databases** | "Let's use the local DB for now" while the VPS has issues | Rule §3.2 — no exceptions |
| **Unintentional exposure** | Flask bound to 0.0.0.0 + a "temporary" port forward | Checklist §3.3 run every time the deployment changes |
| **Effort leaking into the 70%** | Spending a week polishing the mobile UI | Keep the /m view minimal. UI polish is TradingView's territory (Competitive Mapping §C1) |

---

## 6. RELATION TO THE SOP

Additions to Application Usage SOP v1.0:
- **§1 (morning ritual):** still desktop. The Telegram briefing may be read first, but it doesn't replace the session.
- **§3 (weekly):** check that the DB backup is running; verify outside access is still closed off from the public network.
- **§7 (abnormal protocol):** add a line — *"The urge to approve a signal from the phone appears → that's an emotional/rushed signal, not a feature need. Wait for the next morning session."*

---

## 7. RAILWAY DEPLOYMENT (override, July 31, 2026)

> **Transparency note:** Giel explicitly asked to deploy straight to Railway
> (public cloud) — not Tailscale first as in the §4 sequence above. This is
> Giel's own conscious decision, not a retraction of the §3/§4 recommendation — if
> "zero-setup, one evening" access is needed again in another context later, §3/§4 still
> apply. Auth (§Auth `web/app.py`) has existed since the Vue migration, so the
> "real auth" prerequisite for public exposure (§3.1's VPS row) was already
> met beforehand — not added specifically for Railway.

### 7.1 Decision: stay on SQLite, not Postgres

There are 3 triggers for moving to Postgres in ARCHITECTURE §6.1: many concurrent
users, many simultaneous writer processes, or needing managed cloud hosting. Railway
switches on the third reason, but **doesn't require a DB migration** — just attach a
**Railway Volume** (persistent disk) to the service and point `KASTARA_DB_PATH`
at it. This app remains single-user/single-writer (pipeline cron + 1 browser
session for Giel), so there's no real reason for Postgres (concurrent write,
managed backup/replication) — that's all cost with no real benefit here.

### 7.2 What's already been prepared in the repo (July 31, 2026)

- **`Dockerfile`** (multi-stage): stage 1 (`node:22-alpine`) builds
  `web/frontend/` → `dist/`; stage 2 (`python:3.12-slim`) installs
  `requirements.txt` + copies the source + copies `dist/` from stage 1. `CMD`
  runs `gunicorn web.app:app --bind 0.0.0.0:$PORT --workers 2
  --timeout 300` — the timeout is generous because `/api/run_daily_now`
  (triggers today's pipeline from the Snapshot) can take a while (fetching all
  external sources).
- **`.dockerignore`** — excludes `.venv/`, `node_modules/`, `*.db`,
  `kastara-finance-data/`, `.git/`, `.env`, `prompts/persona_*.txt`, `logs/`,
  and `*.md` (docs aren't read by the app at runtime).
- **`requirements.txt`** — adds `gunicorn`.
- **`web/app.py`** — `init_db()` moved to module level (not just inside
  `main()`) — REQUIRED, because gunicorn imports the module directly without ever
  executing `if __name__ == "__main__"`. Without this, an empty Volume on the first
  deploy would fail on the first API query (tables don't exist yet). It's idempotent,
  so it's fine to keep calling it on every process start.
- **`tests/test_web_app.py`** — sets `KASTARA_DB_PATH` to a temp file BEFORE
  importing `web.app` (the change above means importing this module now
  triggers `init_db()` — without this guard, tests would silently hit
  Giel's real production DB via his local `.env`).
- **Verified locally**: `docker build` succeeds, the container runs
  (`docker run` + dummy env vars), `/` (SPA) returns 200, `/api/auth/login` +
  `/api/auth/status` + `/api/latest` (authenticated) all work correctly
  end-to-end inside the image. The test image was deleted after verification
  (not left sitting on disk).

### 7.3 Railway setup steps (not yet executed — needs Giel's own account/login)

```
[ ] 1. Create a new project on Railway, connect this repo (or railway up
       from the CLI if not going through GitHub).
[ ] 2. Attach a Volume to the service, mount path e.g. /data.
[ ] 3. Set environment variables (Settings -> Variables):
       - KASTARA_DB_PATH=/data/kastara-finance.db
       - DASHBOARD_PASSWORD=<fill in yourself, I should NOT fill this in -- credential>
       - FLASK_SECRET_KEY=<fill in yourself, a long random string -- MUST be
         set explicitly on Railway, unlike local where it may auto-generate;
         if left empty, every redeploy invalidates all login sessions>
       - FRED_API_KEY, OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN,
         TELEGRAM_CHAT_ID, COINALYZE_API_KEY, RISK_CAPITAL_IDR,
         RISK_CAPITAL_USD (same as the local .env, see .env.example)
[ ] 4. First deploy (Volume still empty) -- make sure the container is alive
       & /api/auth/status responds (an empty schema is created automatically via
       the module-level init_db() above).
[ ] 5. Fresh start (Giel's decision, August 4, 2026) -- the old local DB is NOT
       uploaded, it stays as dev data on the local machine. The Railway Volume starts
       empty, the module-level init_db() automatically creates 30 fresh tables.
[ ] 6. ~~Add a SECOND service (cron)~~ -- NOT USED. See §8: a Railway
       Volume can only attach to ONE service (confirmed from Railway's own
       docs, August 4, 2026) -- a second service would get a separate Volume
       = a separate DB, violating the §3.2 "ONE DATABASE" rule.
       Instead: manual trigger via the Telegram bot (§8).
[ ] 7. Verify: log in from a public browser, check /m + PWA install from the phone
       (start_url is already /m, see ROADMAP.md July 31, 2026), check that the News
       Trigger from the Snapshot actually fills in data.
```

### 7.4 What was NOT done in this session

Postgres migration (deemed unnecessary, §7.1). Uploading the old local DB to
Railway (fresh start chosen instead, §7.3 step 5). Cron via a separate Railway
service (not possible due to the Volume constraint, §8).

## 8. DAILY CRON via TELEGRAM (not a second service, August 4, 2026)

### 8.0 Why not a regular Railway Cron Job

The original plan in §7.3 step 7 (a second service dedicated to cron, custom start command
`python -m pipeline.run_daily`, Railway Cron Schedule) **cannot be used**
for this app: verified directly against Railway's docs during execution (August 4, 2026) --
**one Volume can only attach to one service**. A second service would
automatically need its own Volume (a separate, empty SQLite DB) -- that
violates the hard rule §3.2 "ONE DATABASE, moving = moving everything", not
merely duplicate data but 2 sources of truth silently diverging.

### 8.1 Solution: manual trigger via a Telegram bot (2-way, webhook, 3 commands)

Instead of a Railway Cron Job (which needs a second service), the daily pipeline is triggered
via a Telegram command that calls an endpoint on the SAME SERVICE (which
already has the real Volume/DB) -- not a separate process, not long-polling.
- **`POST /api/telegram/webhook`** (`web/app.py`) -- exempt from session
  auth (Telegram calls it, not Giel's browser), but gated by 2 layers:
  (1) the message's `chat_id` MUST be in the `TELEGRAM_CHAT_IDS` allowlist (plural,
  comma-separated -- falls back to the single `TELEGRAM_CHAT_ID` if not yet set,
  silently ignored if not on the list, no info leaked to an
  unknown sender), (2) an optional secret token header
  `X-Telegram-Bot-Api-Secret-Token` (if `TELEGRAM_WEBHOOK_SECRET`
  is set) -- an extra defense beyond just chat_id.
- **3 commands** (per Giel's spec "Telegram Bot Commands v1.0", August 5-6, 2026):
  - `/start` -- list of commands.
  - `/status` -- reads the latest `daily_market` (when run_daily last ran) +
    the latest date for `asset_ohlcv`/`daily_news` EACH SEPARATELY (not
    assumed to be in sync) + upcoming `econ_calendar` events + pending
    `trade_signals` awaiting approval + SUGGESTED thread links waiting for review.
  - `/run_daily` -> runs `run_daily_mod.run_daily()` in a **background
    thread** (not directly in the handler) -- Telegram retries sending the update
    if the webhook doesn't reply quickly, and `run_daily()` can take a while (fetching
    all external sources). The handler replies with a quick ack ("⏳ run_daily
    started..."), then sends a follow-up message (SAME format as `/status`)
    once the process is actually done, reusing `notify/telegram.py::send_message()`.
    Gated by a **lock file** (`$TMPDIR/kastara_run_daily.lock`, containing
    PID+timestamp, stale after >30 minutes taken over -- prevents 2 concurrent runs,
    SQLite single-writer §6.1) + a **5-minute rate limit** between triggers
    (a separate file, prevents SEQUENTIAL spam-triggering right after the
    previous run finishes).
- **Other commands were DELIBERATELY not built** (`approve/reject signal`,
  `backfill`, `settings/grader override`) -- per spec §1: those are operations
  that need a gate/conscious ritual (anti-impulsivity, deliberate friction), not
  idempotent pipeline operations like `run_daily`/`run_analysis` (well,
  `run_analysis` also hasn't been built as a command -- marked "allowed" in
  the spec but not among the 3 commands actually specified, so it hasn't
  been implemented yet, can be added later if proven necessary).
- **Why STILL webhook, not long-polling+systemd** (the original spec draft
  wanted a separate VPS): Railway is ALREADY an always-on host -- that
  prerequisite of the spec is already met. Long-polling+systemd would need a 2nd
  process running continuously, which on Railway means a 2nd service -- hitting
  the exact same Volume-only-1-service blocker that killed the cron-service
  plan above (§8.0). A webhook on the same service avoids this problem
  entirely.

### 8.2 Setup (manual action, needs Giel's real token/domain)

```
[ ] 1. Set env vars on Railway (Settings -> Variables), same as .env:
       TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (already there from the Daily Briefing
       if set up locally before). Also add:
       TELEGRAM_WEBHOOK_SECRET=<random string, recommended but optional>
       TELEGRAM_CHAT_IDS=<optional, comma-separated if you want >1 chat_id able
       to trigger the bot -- falls back to the single TELEGRAM_CHAT_ID if empty>
[ ] 2. After the service is live & has a public domain (§7.3 step 4/7), register
       the webhook with Telegram ONCE (from the local machine, replace <TOKEN>/
       <URL>/<SECRET>):
       curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
         -d "url=https://<your-railway-domain>/api/telegram/webhook" \
         -d "secret_token=<SECRET, same as TELEGRAM_WEBHOOK_SECRET>"
[ ] 3. Verify: send "/run_daily" from your Telegram account to the bot -- an ack
       reply should appear within seconds, then a result summary a
       while later (the actual duration of run_daily(), fetching all sources over the network).
[ ] 4. Check `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo` if you
       want to confirm the webhook is registered correctly (check the "url" field & that there's
       no "last_error_message").
```

### 8.3 What was NOT done

Telegram commands other than `/run_daily`. Rate-limiting/anti-spam on the
webhook endpoint (deemed unnecessary -- the chat_id gate is already strict enough
for this single-user app). A 2-step confirmation before triggering (e.g. "are you sure?"
before running) -- `/run_daily` is considered safe to trigger directly, same
as the "Trigger News (Now)" button on the Snapshot, which also has no confirmation.

## 9. PERSONA PROMPTS ON RAILWAY (August 10, 2026)

`prompts/persona_<lens>.txt` (Panel 4, 4 AI Analyses) is deliberately gitignored
(`prompts/README.md`) -- its content is Giel's own way of thinking/analyzing, the
same principle as `.env`. Consequence: `git push` NEVER carries these
files to Railway. If uploaded manually into the regular `prompts/`
(not on the Volume), they disappear again on the next deploy -- the app's
filesystem outside the Volume is rebuilt from the image on every deploy,
only the Volume persists (the same lesson behind why the second cron service
was rejected in §8.0).

**Solution**: `llm/persona_analysis.py` now reads the optional env var
`KASTARA_PROMPTS_DIR` -- empty (default) = use `prompts/` in the source
tree as usual (local dev, UNCHANGED). Set = use that folder,
pointed at the SAME Volume as `KASTARA_DB_PATH` so the prompts
survive across deploys.

```
[ ] 1. Set the Railway env var: KASTARA_PROMPTS_DIR=/data/prompts
       (change /data if your Volume mount path differs -- check against
       the existing KASTARA_DB_PATH, usually the same folder)
[ ] 2. Create the folder first + upload the 4 prompt files (ONCE, from the
       local machine, run via railway ssh -- same pattern as the earlier
       data migration):
       railway ssh -- "mkdir -p /data/prompts"
       railway ssh -- "cat > /data/prompts/persona_gema.txt" < prompts/persona_gema.txt
       railway ssh -- "cat > /data/prompts/persona_leon.txt" < prompts/persona_leon.txt
       railway ssh -- "cat > /data/prompts/persona_akela.txt" < prompts/persona_akela.txt
       railway ssh -- "cat > /data/prompts/persona_rivan.txt" < prompts/persona_rivan.txt
[ ] 3. Deploy the staged env var change (Railway doesn't auto-apply).
[ ] 4. Verify: GET /api/persona/status on Railway should return all 4 lenses
       as true. Try actually running "Run Analysis" in Panel 4.
```

If a prompt is edited locally later, repeat step 2 for the lens that
changed (not an automated process -- it's personal & rarely changes, not worth
turning into a pipeline).

---

*Deployment & Mobile Access Strategy v1.0 — start from Stage 1, let real usage determine Stage 3. Use it first, build after you know.*
*§7 (Railway) added July 31, 2026 as Giel's explicit override — see the transparency note above.*
*§8 (Telegram cron trigger) added August 4, 2026 after Giel's first deploy uncovered Railway's Volume-per-service constraint in practice.*
*§9 (Persona prompts on Volume) added August 10, 2026 -- Giel asked for the already-written prompts to be made active & uploaded to production.*
