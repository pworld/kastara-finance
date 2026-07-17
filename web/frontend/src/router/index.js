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
  // News Threads N-1 (Addendum B §20) -- route dinamis PERTAMA di app ini
  // (`:id` via useRoute().params.id, bukan props -- lihat ThreadDetailView.vue).
  { path: '/threads', name: 'threads', component: () => import('../views/ThreadIndexView.vue') },
  { path: '/threads/:id', name: 'thread-detail', component: () => import('../views/ThreadDetailView.vue') },
  // Settings (Addendum C §21.11, C-1 gap ditutup 17 Jul 2026) -- kurasi
  // lambat/reflektif tag & thread, terpisah dari command-palette cepat.
  { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue') },
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
  if (!auth.authenticated) return '/login'
  return true
})

export default router
