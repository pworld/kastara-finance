<script setup>
import { ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// Sidebar collapse (6 Agustus 2026) -- reclaim lebar layar utk konten
// (mis. tabel lebar di Universe/Chart). Persist ke localStorage supaya
// pilihan bertahan lintas reload, bukan reset tiap buka app.
const SIDEBAR_COLLAPSED_KEY = 'kastara_sidebar_collapsed'
const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1')
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed.value ? '1' : '0')
}
const navGroups = [
  {
    title: 'Daily',
    items: [
      { to: '/snapshot', label: 'Snapshot' },
      { to: '/news', label: 'News' },
      // Threads dipindah ke sini (di bawah News, 28 Jul 2026) -- konfirmasi/
      // tolak saran tautan sudah jadi bagian ritual baca News harian, jadi
      // menunya deket News, bukan di Pengaturan (yang kurasi lambat/reflektif).
      { to: '/threads', label: 'Threads' },
      { to: '/forward', label: 'Forward' },
      { to: '/reading', label: 'Reading' },
      { to: '/chart', label: 'Chart' },
      { to: '/synthesis', label: 'Synthesis' },
    ],
  },
  {
    // Lane INVEST (ritme mingguan/kuartalan) -- dulu digabung "Universal"
    // bareng Riwayat, dipisah biar jelas ini lane investasi saham, bukan
    // ritual harian (lihat docs/SOP.md Bagian C).
    title: 'Investing',
    items: [
      { to: '/universe', label: 'Universe' },
    ],
  },
  {
    // Track record lintas-lane (synthesis/prediksi/jurnal/lensa) -- dibaca
    // saat review mingguan/bulanan, bukan tiap hari.
    title: 'Arsip',
    items: [
      { to: '/riwayat', label: 'Riwayat' },
    ],
  },
  {
    // Kurasi lambat/reflektif (Addendum C §21.11) -- BEDA sifat dari Daily,
    // grup sendiri biar tidak tercampur ritual harian.
    title: 'Pengaturan',
    items: [
      { to: '/tags', label: 'Tags' },
    ],
  },
]

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <Toast />
  <RouterView v-if="route.path === '/login' || route.path === '/m'" />
  <div v-else class="shell">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="brand-row">
        <div class="brand" v-show="!sidebarCollapsed">KASTARA FINANCE</div>
        <button
          class="sidebar-toggle" @click="toggleSidebar"
          :title="sidebarCollapsed ? 'Perluas sidebar' : 'Ciutkan sidebar'"
        >{{ sidebarCollapsed ? '»' : '«' }}</button>
      </div>
      <nav v-show="!sidebarCollapsed">
        <div v-for="group in navGroups" :key="group.title" class="nav-group">
          <div class="nav-group-title">{{ group.title }}</div>
          <RouterLink
            v-for="item in group.items" :key="item.to" :to="item.to"
            class="nav-item" :class="{ active: route.path === item.to }"
          >{{ item.label }}</RouterLink>
        </div>
      </nav>
      <button class="btn small secondary logout-btn" v-show="!sidebarCollapsed" @click="logout">Keluar</button>
    </aside>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: var(--panel);
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  transition: width .15s ease;
  overflow: hidden;
}
.sidebar.collapsed {
  width: 44px;
}
.brand-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px 18px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 10px;
}
.sidebar.collapsed .brand-row {
  padding: 0 10px 18px;
  justify-content: center;
}
.brand {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .5px;
  white-space: nowrap;
}
.sidebar-toggle {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
}
.sidebar-toggle:hover {
  color: var(--text);
  border-color: var(--muted);
}
nav {
  display: flex;
  flex-direction: column;
  flex: 1;
}
.nav-group {
  display: flex;
  flex-direction: column;
  margin-bottom: 18px;
}
.nav-group-title {
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .6px;
  padding: 0 20px 6px;
}
.nav-item {
  color: var(--muted);
  text-decoration: none;
  font-size: 13px;
  padding: 10px 20px;
  border-left: 3px solid transparent;
}
.nav-item:hover {
  color: var(--text);
}
.nav-item.active {
  color: var(--text);
  border-left-color: var(--accent);
  background: var(--panel2);
}
.logout-btn {
  margin: 12px 20px 0;
}
.content {
  flex: 1;
  padding: 20px 24px;
  max-width: 1200px;
}
</style>
