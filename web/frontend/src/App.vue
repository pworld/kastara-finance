<script setup>
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import Toast from 'primevue/toast'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const navGroups = [
  {
    title: 'Daily',
    items: [
      { to: '/snapshot', label: 'Snapshot' },
      { to: '/news', label: 'News' },
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
]

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <Toast />
  <RouterView v-if="route.path === '/login'" />
  <div v-else class="shell">
    <aside class="sidebar">
      <div class="brand">KASTARA FINANCE</div>
      <nav>
        <div v-for="group in navGroups" :key="group.title" class="nav-group">
          <div class="nav-group-title">{{ group.title }}</div>
          <RouterLink
            v-for="item in group.items" :key="item.to" :to="item.to"
            class="nav-item" :class="{ active: route.path === item.to }"
          >{{ item.label }}</RouterLink>
        </div>
      </nav>
      <button class="btn small secondary logout-btn" @click="logout">Keluar</button>
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
}
.brand {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: .5px;
  padding: 0 20px 18px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 10px;
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
