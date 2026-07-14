# Plan: Frontend → Vue 3 + Vite (parallel app, strangler cutover)

> Nota: file plan ini sebelumnya memuat rencana lama "Deploy + Coinalyze + IDX
> foreign flow + Persona v4" (Track B/C/D SUDAH SELESAI, Track A masih pending
> sebagai task #61 & tercatat di `docs/ROADMAP.md`). Isi itu diganti dengan
> rencana migrasi FE ini. Track A (deploy/auth) tidak hilang — tetap ditrack
> terpisah, dan justru bersinggungan dengan langkah "login" di Fase 3 di bawah.

> **Status per 14 Jul 2026: SEMUA FASE (0-3) SELESAI.** Migrasi FE tuntas —
> dashboard sekarang Vue 3 + Vite + PrimeVue, satu proses/port (Flask
> menyajikan build Vue langsung), dgn session auth. Kode vanilla lama
> (`web/templates/`, `web/static/`) sudah dihapus (git-tracked, recoverable
> via history `git show bcfa625:web/templates/index.html` dkk kalau perlu),
> masuk commit `f7168f2 "Migrate to Vue JS"`. Backend/API TIDAK berubah sama
> sekali sepanjang seluruh migrasi — 292 test Python tetap hijau di titik ini.
>
> Detail per-fase yang sudah selesai:
> - **Fase 0**: scaffold Vite+Vue (`web/frontend/`, ditemukan sudah pernah
>   dijalankan Giel sendiri tapi ke-nested salah lokasi
>   `web/frontend/web/frontend/` — dipindah ke lokasi benar, node_modules
>   yang sudah ter-install dipertahankan, bukan install ulang). Tambah
>   Vue Router (8 route, urutan sama tab lama) + Pinia + PrimeVue (preset
>   Aura) + Vue Router history mode. `vite.config.js` proxy `/api` ke Flask.
> - **Fase 1**: `src/lib/api.js` (get/post), `src/lib/format.js`
>   (fmt/today/LANE_CLASS/LENS_LABELS, port dari core.js),
>   `src/components/DataTable.vue` (wrap PrimeVue DataTable + search box,
>   dipakai ~11 tabel), `src/composables/useAppToast.js` (wrap PrimeVue
>   Toast, signature `toast(msg)` sama seperti lama).
> - **Fase 2**: SEMUA 8 view dimigrasi & diverifikasi live dgn data real:
>   `SnapshotView` (cards + backfill 1-instrumen + backfill-semua-gap),
>   `NewsView`, `ForwardView` (econ calendar inline-edit + expectations +
>   positioning + policy tracker + disonansi — paling banyak form),
>   `ReadingView` (4 persona cards + PrimeVue Dialog modal, ganti `<dialog>`
>   native), `ChartView` (SVG candlestick DIBUNGKUS APA ADANYA —
>   `drawCandleChart`/`rollingMA`/`drawMiniLine` dipindah verbatim ke
>   `src/lib/chartMath.js` + template refs, BUKAN ditulis ulang/ganti lib —
>   dimigrasi TERAKHIR sesuai rencana), `SynthesisView`, `RiwayatView` (4
>   sub-tab), `UniverseView` (paling besar — 8 sub-bagian: tabel utama,
>   intake, uji kelayakan, detail emiten+override, validasi lane+riwayat,
>   rasio bank, riwayat intake, grader log+outcome).
> - Bug ditemukan & diperbaiki selama migrasi: `ForwardView` awal pakai 1
>   `ref` bersama utk semua input "Actual" econ calendar yang kosong —
>   salah kalau >1 baris butuh diisi bersamaan (kasus nyata, kalender
>   biasanya banyak event future tanpa actual). Diperbaiki jadi state
>   per-baris (`actualInputs` keyed by id) sebelum sempat jadi bug produksi.
> - **Fase 3 (cutover + login), selesai 14 Jul 2026**:
>   - **Auth**: `web/app.py` — `@app.before_request` menolak (401) SEMUA
>     `/api/*` kecuali `/api/auth/{login,status}` selama `session["authed"]`
>     belum `True`. `DASHBOARD_PASSWORD` **wajib diisi manual di .env** —
>     TIDAK PERNAH di-generate/default oleh kode (beda dari `RISK_CAPITAL_*`
>     yang memang placeholder angka; ini kredensial). Kosong -> endpoint
>     login menolak dgn pesan jelas ("belum di-set"), bukan celah akses
>     tanpa auth. `FLASK_SECRET_KEY` opsional (random tiap start kalau
>     kosong -- sesi ke-invalidate tiap restart, bukan lubang keamanan).
>     Password dibanding pakai `secrets.compare_digest` (constant-time).
>   - **Serving**: route SPA catch-all (`@app.route("/<path:path>")`,
>     didaftarkan PALING TERAKHIR) menyajikan `web/frontend/dist/` — file
>     statis kalau ada di disk, else `index.html` (Vue Router history mode
>     yang urus routing client-side). `Flask(__name__, static_folder=None)`
>     -- folder `web/static/` lama sudah tidak ada, tidak perlu route
>     otomatis Flask.
>   - **Vue**: `src/stores/auth.js` (Pinia, sumber kebenaran tetap
>     `/api/auth/status` server-side, bukan cuma state lokal), `src/views/
>     LoginView.vue`, router guard di `src/router/index.js` (redirect ke
>     `/login` kalau belum auth, redirect balik ke `/snapshot` kalau sudah
>     auth tapi buka `/login`). `src/lib/api.js` — 401 di luar endpoint
>     login sendiri (sesi expired) memicu full-page redirect ke `/login`,
>     bukan silent-fail. `App.vue` sembunyikan sidebar di halaman login,
>     tambah tombol "Keluar".
>   - Kode vanilla lama (`web/templates/`, `web/static/`, 8 partial HTML +
>     10 file JS + 1 CSS) **dihapus** — Giel sendiri yang commit
>     (`f7168f2`), bukan auto-commit dariku.
>   - **Diverifikasi live**: akses tanpa sesi -> redirect ke `/login` +
>     tampil pesan "password belum di-set" (saat `.env` masih kosong);
>     `curl /api/health` tanpa cookie -> 401; asset JS/CSS/font ke-serve
>     benar via catch-all (network tab: semua 200/304, nol 404); SETELAH
>     Giel isi `DASHBOARD_PASSWORD` & login sendiri (aku TIDAK pernah
>     mengetik/menguji password asli manapun -- itu kredensial, bukan
>     wilayahku) -- sidebar + tombol Keluar + Snapshot data real tampil
>     benar dari sesi yang sudah authenticated. 292 test Python tetap
>     hijau setelah semua perubahan auth/serving ini.

## Context

Frontend sekarang ~2,200 baris vanilla di 8 panel (`web/static/js/` 1,216 baris,
`web/templates/partials/` ~823 baris, `web/static/css/dashboard.css` 173 baris).
Semua render dilakukan client-side lewat template string `innerHTML`, dengan
coupling global-scope (urutan `<script>` load-bearing, global `$`/`fmt`/
`postJSON`/`tableCache`). Giel merasa stack mentah ini **terlalu berat untuk
tumbuh** — dia ingin menambah **login, sidebar, dll**, dan itu mahal ditulis
tangan di vanilla.

Kabar baiknya: **API sudah jadi batas data yang bersih**. `web/app.py` punya 57
endpoint `/api/*` yang semuanya `jsonify(...)`, dan route `/` cuma
`render_template("index.html")` **tanpa mengoper data server sama sekali**
(shell statis, semua diisi JS). Jadi migrasi FE = mengganti lapisan render saja,
menunjuk ke API yang sama. Backend & 287 test Python **tidak berubah**.

**Keputusan terkunci (dari Q&A):**
- Framework: **Vue 3 + Vite** (SFC memisahkan template/script/style — lompatan
  paling landai dari vanilla; `v-model` menghapus boilerplate form panel 3/6/8).
- Strategi: **app paralel** di `web/frontend/`, jalan berdampingan dgn dashboard
  lama sampai parity, baru cut over. Ini juga yang bikin "dipisah jadi projek
  sendiri nanti" trivial (sudah standalone).
- Chart panel5 (250 baris SVG tangan): **dibungkus apa adanya dulu**, tidak
  ditulis ulang.
- Backend/API + semua test Python: **tidak disentuh**.

## Approach: app Vue paralel + strangler cutover

Buat projek Vite+Vue baru di `web/frontend/`. Dev: Vite dev server proxy `/api`
→ Flask `127.0.0.1:5000` (tanpa CORS). Dashboard lama tetap di `/` sampai app
baru capai parity, lalu Flask `/` dialihkan ke hasil build Vue. Karena semua
`fetch` FE lama pakai path relatif & tidak ada CORS, proxy dev satu baris cukup.

**UI kit (untuk login/sidebar/tabel murah): PrimeVue** (rekomendasi —
batteries-included: `DataTable` dgn sort/filter/paginate bawaan, komponen
Sidebar/Menu, input form, Dialog, Toast; theme siap pakai). Alternatif:
shadcn-vue (Tailwind, copy-paste, kontrol desain lebih tinggi tapi lebih banyak
CSS untuk dipelajari — kurang cocok dgn keluhan "CSS berat").

## Fase

**Fase 0 — Scaffold (fondasi, belum ada panel)**
- `npm create vite@latest web/frontend -- --template vue` (atau `vue-ts`).
  Tambah PrimeVue, Vue Router, Pinia.
- `web/frontend/vite.config.*`: `server.proxy` `/api` → `http://127.0.0.1:5000`.
- App shell: layout **sidebar** (menggantikan tab atas `index.html:17-26`) +
  Vue Router 8 route (satu per panel).
- Port design token dari `web/static/css/dashboard.css` (`:root` vars) → theme
  global Vue.
- `web/app.py`: tambah route penyaji `web/frontend/dist` untuk prod (dev pakai
  Vite server). Tidak mengubah route `/api/*` manapun.

**Fase 1 — Fondasi bersama (bagian yang dipakai berulang)**
- `src/lib/api.ts` — bungkus fetch: `get()`/`post()` menggantikan raw `fetch` +
  `postJSON` (`core.js:138`).
- `src/lib/format.ts` — `fmt()` (`core.js:28`), `today()`, `LANE_CLASS`
  (`core.js:19`), `LENS_LABELS` (`core.js:7`).
- `src/components/DataTable.vue` — **komponen paling berleverage**: menggantikan
  `applyTableControls` + `renderTableBar` + `tableCache`/`tableState`/
  `tableRerender` + handler sort delegated (`core.js:39-136`), dipakai ~11
  tabel. Pakai **PrimeVue `DataTable`** (sort/filter/paginate bawaan) → sebagian
  besar jadi konfigurasi, bukan kode.
- Toast: PrimeVue `Toast` menggantikan `toast()` (`core.js:21`).

**Fase 2 — Migrasi panel, leaf-first (parity, satu per satu)**
Urut dari paling mudah/independen:
1. **panel2 News, panel7 Riwayat, panel8 Universe** (berat-tabel → payoff
   `DataTable`).
2. **panel3 Forward, panel6 Synthesis** (berat-form → payoff `v-model`).
3. **panel1 Snapshot** (kartu + backfill), **panel4 Reading** (kartu persona +
   modal → PrimeVue `Dialog`).
4. **panel5 Chart TERAKHIR** — bungkus builder SVG yang ada (`panel5.js`
   `drawCandleChart`, `rollingMA`) ke `<CandleChart.vue>` nyaris verbatim; swap
   ke charting lib ditunda.
Tiap panel = satu route/view; form → `v-model`; tabel → `<DataTable>`; string
`innerHTML` → template Vue.

**Fase 3 — Cutover + login (kebutuhan baru)**
- Setelah 8 panel parity: alihkan Flask `/` ke app Vue hasil build; hapus
  `templates/partials/` + `static/js/*` + `index.html` lama. API + `writes.py`
  tetap.
- Tambah **login** di sini: session/login di Flask + view login Vue + router
  guard. Ini berpasangan alami dengan Track A (deploy/auth, task #61) — auth
  yang dibangun untuk internet-facing dipakai ulang oleh SPA.

**Fase 4 — (nanti) angkat keluar jadi projek terpisah**
- Pindahkan `web/frontend/` ke repo sendiri. Sudah bicara ke API lewat HTTP —
  cuma perlu ubah base URL + tambah CORS di Flask. Tidak ada refactor lain.

## Peta reuse (lama → Vue)
| Lama | Baru |
|---|---|
| `core.js` `postJSON` (raw fetch) | `src/lib/api.ts` `get()/post()` |
| `core.js` `fmt`/`today`/`LANE_CLASS`/`LENS_LABELS` | `src/lib/format.ts` |
| `core.js` table engine (`applyTableControls`/`renderTableBar`/`tableCache`/`tableState`/`tableRerender`/sort) | `src/components/DataTable.vue` (PrimeVue DataTable) |
| `core.js` tabs handler + `index.html` nav | Vue Router + layout sidebar |
| `panel5.js` SVG chart | `CandleChart.vue` (bungkus apa adanya) |
| 57 endpoint `/api/*` | tidak berubah, dikonsumsi `api.ts` |

## Yang TIDAK berubah
`web/app.py` route/logic (kecuali tambah route penyaji dist + login nanti),
`web/writes.py`, semua Python, 287 test, DB/schema.

## Verifikasi
- **Dev**: Vite dev server + Flask jalan bareng. Buka app baru, cek tiap panel
  yang sudah dimigrasi: data termuat via `/api` (network tab), form POST benar,
  tabel sort/paginate jalan. Bandingkan berdampingan dgn dashboard `/` lama utk
  parity.
- **Prod build**: `vite build`; Flask sajikan `dist`; smoke test.
- **pytest -q tetap 287 hijau** (backend beku) — jalankan tiap kali route
  penyaji/login di `app.py` diubah.
- **Browser MCP**: muat app, `read_console_messages` cek error, screenshot tiap
  panel.

## Effort (ringkas)
- **Moderat, sebagian besar mekanis** — API adalah kontrak, backend beku,
  rollback bersih (dashboard lama hidup sepanjang migrasi).
- Cost center: `DataTable.vue` (tulis sekali, fondasional), bungkus chart
  panel5, volume form panel 3/6/8.
- Risiko: **rendah** — app paralel berarti `/` lama tetap jalan; cut over hanya
  saat parity; login + sidebar yang jadi motivasi utama justru "gratis" dari
  ekosistem PrimeVue, bukan ditulis tangan.