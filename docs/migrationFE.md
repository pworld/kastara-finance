# Plan: Frontend → Vue 3 + Vite (parallel app, strangler cutover)

> Nota: file plan ini sebelumnya memuat rencana lama "Deploy + Coinalyze + IDX
> foreign flow + Persona v4" (Track B/C/D SUDAH SELESAI, Track A masih pending
> sebagai task #61 & tercatat di `docs/ROADMAP.md`). Isi itu diganti dengan
> rencana migrasi FE ini. Track A (deploy/auth) tidak hilang — tetap ditrack
> terpisah, dan justru bersinggungan dengan langkah "login" di Fase 3 di bawah.

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