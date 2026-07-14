# Kastara Finance — Frontend (Vue 3 + Vite)

Migrasi frontend dari `web/static/js/*.js` + `web/templates/*.html` (vanilla)
ke Vue 3 + Vite. Rencana lengkap: [`../../docs/migrationFE.md`](../../docs/migrationFE.md).

App paralel — dashboard lama (`web/app.py` -> `/`) tetap jalan sampai app ini
capai parity, baru di-cutover (Fase 3 migrationFE.md).

## Dev

Backend Flask harus jalan duluan (`python -m web.app`, port 5000 default) --
`vite.config.js` proxy `/api/*` ke situ.

```bash
npm install
npm run dev
# buka http://localhost:5173
```

## Build (prod)

```bash
npm run build
# hasil di dist/, disajikan Flask (Fase 3)
```

## Stack

- **Vue 3** (Composition API, `<script setup>`)
- **Vue Router** — 1 route per panel lama (`src/router/index.js`)
- **Pinia** — state management (dipakai mulai Fase 2 sesuai kebutuhan)
- **PrimeVue** (preset Aura) — komponen UI (DataTable, Dialog, Toast, dll) --
  alasan pemilihan ada di migrationFE.md
- **`src/lib/api.js`** — bungkus fetch ke `/api/*`, menggantikan `postJSON`/
  raw fetch di `core.js` dashboard lama
