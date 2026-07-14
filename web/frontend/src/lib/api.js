// Bungkus fetch ke /api/* -- menggantikan raw fetch + postJSON() di
// web/static/js/core.js (lihat docs/migrationFE.md peta reuse). Path
// relatif ("/api/...") sama persis dgn dashboard lama -- dev di-proxy Vite
// ke Flask (vite.config.js), prod disajikan same-origin oleh Flask.

async function handle(res) {
  if (res.status === 401 && !res.url.endsWith('/api/auth/login')) {
    // Sesi expired/belum login (BUKAN password salah di form login itu
    // sendiri, yang harus tampil sbg pesan error inline, bukan redirect
    // paksa) -- reload penuh ke /login supaya router guard & Pinia state
    // ke-refresh bersih dari nol (lihat router/index.js).
    window.location.href = '/login'
    return new Promise(() => {}) // tahan promise, halaman keburu reload
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `HTTP ${res.status}`)
  }
  return res.json()
}

export function get(path, params) {
  const url = new URL(path, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v)
    }
  }
  return fetch(url.pathname + url.search).then(handle)
}

export function post(path, body) {
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  }).then(handle)
}
