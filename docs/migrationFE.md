# Plan: Frontend → Vue 3 + Vite (parallel app, strangler cutover)

> Note: this plan file previously held the old plan "Deploy + Coinalyze + IDX
> foreign flow + Persona v4" (Track B/C/D ALREADY DONE, Track A still pending
> as task #61 and tracked in `docs/ROADMAP.md`). That content was replaced with
> this FE migration plan. Track A (deploy/auth) hasn't disappeared — it's still
> tracked separately, and it actually intersects with the "login" step in Phase 3
> below.

> **Status as of Jul 14, 2026: ALL PHASES (0-3) DONE.** The FE migration is
> complete — the dashboard is now Vue 3 + Vite + PrimeVue, one process/port
> (Flask serves the Vue build directly), with session auth. The old vanilla
> code (`web/templates/`, `web/static/`) has been deleted (git-tracked,
> recoverable via history with `git show bcfa625:web/templates/index.html`
> etc. if needed), included in commit `f7168f2 "Migrate to Vue JS"`.
> Backend/API did NOT change at all throughout the entire migration — 292
> Python tests remain green at this point.
>
> Per-phase details of what's been completed:
> - **Phase 0**: scaffold Vite+Vue (`web/frontend/`, found to have already
>   been run by Giel himself but nested in the wrong location
>   `web/frontend/web/frontend/` — moved to the correct location, the
>   already-installed node_modules were kept, not reinstalled). Added
>   Vue Router (8 routes, same order as the old tabs) + Pinia + PrimeVue
>   (Aura preset) + Vue Router history mode. `vite.config.js` proxies `/api`
>   to Flask.
> - **Phase 1**: `src/lib/api.js` (get/post), `src/lib/format.js`
>   (fmt/today/LANE_CLASS/LENS_LABELS, ported from core.js),
>   `src/components/DataTable.vue` (wraps PrimeVue DataTable + search box,
>   used by ~11 tables), `src/composables/useAppToast.js` (wraps PrimeVue
>   Toast, same signature `toast(msg)` as before).
> - **Phase 2**: ALL 8 views migrated & verified live with real data:
>   `SnapshotView` (cards + single-instrument backfill + backfill-all-gaps),
>   `NewsView`, `ForwardView` (econ calendar inline-edit + expectations +
>   positioning + policy tracker + dissonance — the most form-heavy),
>   `ReadingView` (4 persona cards + PrimeVue Dialog modal, replacing the
>   native `<dialog>`), `ChartView` (SVG candlestick WRAPPED AS-IS —
>   `drawCandleChart`/`rollingMA`/`drawMiniLine` moved verbatim into
>   `src/lib/chartMath.js` + template refs, NOT rewritten/swapped for
>   another lib — migrated LAST per plan), `SynthesisView`, `RiwayatView`
>   (History, 4 sub-tabs), `UniverseView` (the largest — 8 sub-sections:
>   main table, intake, eligibility testing, issuer detail+override, lane
>   validation+history, bank ratios, intake history, grader log+outcome).
> - Bug found & fixed during migration: `ForwardView` initially used one
>   shared `ref` for all empty "Actual" econ calendar inputs — wrong when
>   >1 row needs to be filled in at the same time (a real case, since the
>   calendar usually has many future events without an actual value).
>   Fixed to per-row state (`actualInputs` keyed by id) before it could
>   turn into a production bug.
> - **Phase 3 (cutover + login), completed Jul 14, 2026**:
>   - **Auth**: `web/app.py` — `@app.before_request` rejects (401) ALL
>     `/api/*` except `/api/auth/{login,status}` while `session["authed"]`
>     is not yet `True`. `DASHBOARD_PASSWORD` **must be filled in manually
>     in .env** — it is NEVER generated/defaulted by the code (unlike
>     `RISK_CAPITAL_*`, which is indeed a placeholder number; this one is
>     a credential). If empty -> the login endpoint refuses with a clear
>     message ("not yet set"), not an access gap without auth.
>     `FLASK_SECRET_KEY` is optional (random on every start if empty --
>     the session is invalidated on every restart, not a security hole).
>     The password is compared using `secrets.compare_digest`
>     (constant-time).
>   - **Serving**: an SPA catch-all route (`@app.route("/<path:path>")`,
>     registered LAST) serves `web/frontend/dist/` — static files if
>     present on disk, else `index.html` (Vue Router history mode handles
>     client-side routing). `Flask(__name__, static_folder=None)`
>     -- the old `web/static/` folder no longer exists, so no need for
>     Flask's automatic route.
>   - **Vue**: `src/stores/auth.js` (Pinia, the source of truth remains
>     `/api/auth/status` server-side, not just local state), `src/views/
>     LoginView.vue`, a router guard in `src/router/index.js` (redirect to
>     `/login` if not authed, redirect back to `/snapshot` if already
>     authed but opening `/login`). `src/lib/api.js` — a 401 outside the
>     login endpoint itself (expired session) triggers a full-page
>     redirect to `/login`, not a silent fail. `App.vue` hides the sidebar
>     on the login page, adds a "Log out" button.
>   - The old vanilla code (`web/templates/`, `web/static/`, 8 partial
>     HTML files + 10 JS files + 1 CSS file) **was deleted** — Giel himself
>     committed it (`f7168f2`), not an auto-commit from me.
>   - **Verified live**: accessing without a session -> redirects to
>     `/login` + shows the message "password not yet set" (while `.env`
>     is still empty); `curl /api/health` without a cookie -> 401; JS/CSS/
>     font assets are served correctly via the catch-all (network tab: all
>     200/304, zero 404s); AFTER Giel filled in `DASHBOARD_PASSWORD` and
>     logged in himself (I NEVER typed/tested any real password -- that's
>     a credential, not my territory) -- the sidebar + Log out button +
>     real Snapshot data display correctly from the now-authenticated
>     session. The 292 Python tests remain green after all these
>     auth/serving changes.

## Context

The frontend is currently ~2,200 lines of vanilla code across 8 panels
(`web/static/js/` 1,216 lines, `web/templates/partials/` ~823 lines,
`web/static/css/dashboard.css` 173 lines). All rendering is done client-side
via `innerHTML` template strings, with global-scope coupling (load-bearing
`<script>` order, global `$`/`fmt`/`postJSON`/`tableCache`). Giel feels this
raw stack is **too heavy to grow** — he wants to add **login, a sidebar,
etc.**, and that's expensive to hand-write in vanilla.

The good news: **the API is already a clean data boundary**. `web/app.py` has
57 `/api/*` endpoints that all `jsonify(...)`, and the `/` route just does
`render_template("index.html")` **without passing any data from the server at
all** (a static shell, everything filled in by JS). So the FE migration is
just swapping out the render layer, pointing at the same API. The backend &
287 Python tests **do not change**.

**Locked-in decisions (from Q&A):**
- Framework: **Vue 3 + Vite** (SFCs separate template/script/style — the
  gentlest jump from vanilla; `v-model` removes the boilerplate of form
  panels 3/6/8).
- Strategy: **parallel app** in `web/frontend/`, running side by side with
  the old dashboard until parity, then cut over. This is also what makes
  "split off into its own project later" trivial (it's already standalone).
- Chart panel5 (250 lines of hand-written SVG): **wrapped as-is for now**,
  not rewritten.
- Backend/API + all Python tests: **left untouched**.

## Approach: parallel Vue app + strangler cutover

Create a new Vite+Vue project in `web/frontend/`. Dev: Vite dev server
proxies `/api` → Flask `127.0.0.1:5000` (no CORS). The old dashboard stays at
`/` until the new app reaches parity, then Flask's `/` is switched over to
the built Vue output. Since all of the old FE's `fetch` calls use relative
paths and there's no CORS, a one-line dev proxy is enough.

**UI kit (for login/sidebar/cheap tables): PrimeVue** (recommendation —
batteries-included: `DataTable` with built-in sort/filter/paginate,
Sidebar/Menu components, form inputs, Dialog, Toast; ready-made theme).
Alternative: shadcn-vue (Tailwind, copy-paste, higher design control but more
CSS to learn — less suited to the "CSS is too heavy" complaint).

## Phases

**Phase 0 — Scaffold (foundation, no panels yet)**
- `npm create vite@latest web/frontend -- --template vue` (or `vue-ts`).
  Add PrimeVue, Vue Router, Pinia.
- `web/frontend/vite.config.*`: `server.proxy` `/api` → `http://127.0.0.1:5000`.
- App shell: **sidebar** layout (replacing the top tabs in
  `index.html:17-26`) + Vue Router with 8 routes (one per panel).
- Port design tokens from `web/static/css/dashboard.css` (`:root` vars) →
  a global Vue theme.
- `web/app.py`: add a route serving `web/frontend/dist` for prod (dev uses
  the Vite server). Does not change any `/api/*` route.

**Phase 1 — Shared foundation (repeatedly reused parts)**
- `src/lib/api.ts` — wraps fetch: `get()`/`post()` replacing raw `fetch` +
  `postJSON` (`core.js:138`).
- `src/lib/format.ts` — `fmt()` (`core.js:28`), `today()`, `LANE_CLASS`
  (`core.js:19`), `LENS_LABELS` (`core.js:7`).
- `src/components/DataTable.vue` — **the highest-leverage component**:
  replaces `applyTableControls` + `renderTableBar` +
  `tableCache`/`tableState`/`tableRerender` + the delegated sort handler
  (`core.js:39-136`), used by ~11 tables. Uses **PrimeVue `DataTable`**
  (built-in sort/filter/paginate) → mostly becomes configuration, not code.
- Toast: PrimeVue `Toast` replacing `toast()` (`core.js:21`).

**Phase 2 — Panel migration, leaf-first (parity, one at a time)**
Ordered from easiest/most independent:
1. **panel2 News, panel7 History, panel8 Universe** (table-heavy → best
   payoff from `DataTable`).
2. **panel3 Forward, panel6 Synthesis** (form-heavy → best payoff from
   `v-model`).
3. **panel1 Snapshot** (cards + backfill), **panel4 Reading** (persona
   cards + modal → PrimeVue `Dialog`).
4. **panel5 Chart LAST** — wrap the existing SVG builder (`panel5.js`
   `drawCandleChart`, `rollingMA`) into `<CandleChart.vue>` nearly
   verbatim; swapping to a charting lib is deferred.
Each panel = one route/view; forms → `v-model`; tables → `<DataTable>`;
`innerHTML` strings → Vue templates.

**Phase 3 — Cutover + login (new requirement)**
- After all 8 panels reach parity: switch Flask's `/` to the built Vue
  app; delete `templates/partials/` + `static/js/*` + the old
  `index.html`. The API + `writes.py` stay.
- Add **login** here: session/login in Flask + a Vue login view + a router
  guard. This pairs naturally with Track A (deploy/auth, task #61) — the
  auth built for internet-facing use gets reused by the SPA.

**Phase 4 — (later) lift out into a separate project**
- Move `web/frontend/` into its own repo. It already talks to the API over
  HTTP — just needs a base URL change + adding CORS in Flask. No other
  refactor needed.

## Reuse map (old → Vue)
| Old | New |
|---|---|
| `core.js` `postJSON` (raw fetch) | `src/lib/api.ts` `get()/post()` |
| `core.js` `fmt`/`today`/`LANE_CLASS`/`LENS_LABELS` | `src/lib/format.ts` |
| `core.js` table engine (`applyTableControls`/`renderTableBar`/`tableCache`/`tableState`/`tableRerender`/sort) | `src/components/DataTable.vue` (PrimeVue DataTable) |
| `core.js` tabs handler + `index.html` nav | Vue Router + sidebar layout |
| `panel5.js` SVG chart | `CandleChart.vue` (wrapped as-is) |
| 57 `/api/*` endpoints | unchanged, consumed by `api.ts` |

## What does NOT change
`web/app.py` route/logic (except adding the dist-serving route + login
later), `web/writes.py`, all Python code, the 287 tests, DB/schema.

## Verification
- **Dev**: Vite dev server + Flask running together. Open the new app,
  check each migrated panel: data loads via `/api` (network tab), form
  POSTs are correct, table sort/paginate work. Compare side by side with
  the old dashboard at `/` for parity.
- **Prod build**: `vite build`; Flask serves `dist`; smoke test.
- **pytest -q stays at 287 green** (backend frozen) — run every time the
  serving/login route in `app.py` is changed.
- **Browser MCP**: load the app, check `read_console_messages` for errors,
  screenshot each panel.

## Effort (summary)
- **Moderate, mostly mechanical** — the API is a contract, the backend is
  frozen, rollback is clean (the old dashboard keeps running throughout
  the migration).
- Cost centers: `DataTable.vue` (written once, foundational), wrapping the
  panel5 chart, the volume of forms in panels 3/6/8.
- Risk: **low** — a parallel app means the old `/` keeps working; cutover
  only happens at parity; login + sidebar, the main motivations, come
  essentially "free" from the PrimeVue ecosystem rather than being
  hand-written.
