import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// 8 tab lama (index.html + templates/partials/panelN_*.html) -> 8 route di
// sini, 1:1, urutan sama (lihat docs/migrationFE.md Fase 2). Lazy-load
// tiap view supaya bundle awal kecil.
const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
  { path: '/', redirect: '/snapshot' },
  { path: '/snapshot', name: 'snapshot', component: () => import('../views/SnapshotView.vue') },
  { path: '/news', name: 'news', component: () => import('../views/NewsView.vue') },
  { path: '/forward', name: 'forward', component: () => import('../views/ForwardView.vue') },
  { path: '/reading', name: 'reading', component: () => import('../views/ReadingView.vue') },
  { path: '/chart', name: 'chart', component: () => import('../views/ChartView.vue') },
  { path: '/synthesis', name: 'synthesis', component: () => import('../views/SynthesisView.vue') },
  { path: '/riwayat', name: 'riwayat', component: () => import('../views/RiwayatView.vue') },
  { path: '/universe', name: 'universe', component: () => import('../views/UniverseView.vue') },
  // News Threads (Addendum B §20 + Addendum C §21.11 komposisi/umur/tags).
  // 17 Jul 2026: sempat digabung jadi "Settings" dgn tab Tags/Threads, Giel
  // minta dipecah lagi jadi 2 menu berdiri sendiri (bukan tab).
  // `/threads` = index/kelola (ThreadsView.vue), `/threads/:id` = timeline
  // per-thread (konfirmasi/tolak SUGGESTED, TETAP terpisah -- fungsi beda,
  // baca hasil bukan kurasi) -- route dinamis PERTAMA di app ini
  // (`:id` via useRoute().params.id, bukan props -- lihat ThreadDetailView.vue).
  { path: '/threads', name: 'threads', component: () => import('../views/ThreadsView.vue') },
  { path: '/threads/:id', name: 'thread-detail', component: () => import('../views/ThreadDetailView.vue') },
  // Tags (Addendum C §21.11, C-1 gap ditutup 17 Jul 2026) -- kurasi
  // lambat/reflektif kamus tag, terpisah dari command-palette cepat.
  { path: '/tags', name: 'tags', component: () => import('../views/TagsView.vue') },
  // Mode Ringkas / PWA mobile (docs/mode_ringkas_pwa_mobile_v1.md BAGIAN B) --
  // layar tunggal, dipisah dari sidebar 7-tab desktop (lihat App.vue: /m
  // render standalone tanpa shell, sama seperti /login). start_url manifest
  // PWA (vite.config.js) mengarah ke sini.
  { path: '/m', name: 'mobile', component: () => import('../views/MobileView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Guard auth (Fase 3 migrasi FE) -- /api/auth/status adalah sumber
// kebenaran (session cookie Flask), state Pinia cuma cache lokal, di-refresh
// tiap navigasi pertama (checked=false) supaya sesi yang expired kedetek.
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.checked) await auth.checkStatus()
  if (to.path === '/login') {
    if (auth.authenticated) return '/snapshot'
    return true
  }
  if (!auth.authenticated) {
    // 6 Agustus 2026: dulu redirect ke /login TANPA bawa tujuan asli --
    // hasilnya login SELALU mendarat di /snapshot, biar orang buka /m
    // (mis. dari PWA di HP) tetap kelempar ke tampilan desktop stlh login.
    // Simpan tujuan asli di query `redirect`, LoginView.vue baca ini.
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
