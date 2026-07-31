<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import Dialog from 'primevue/dialog'
import { get, post } from '../lib/api'
import { today, daysAgo, FACET_COLOR } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'
import { useAuthStore } from '../stores/auth'

// Mode Ringkas / PWA (docs/mode_ringkas_pwa_mobile_v1.md BAGIAN A+B) -- layar
// TUNGGAL, scroll vertikal, tombol besar, aksi WAJIB paling atas/dekat jempol.
// Endpoint 100% REUSE dari web/writes.py yang sudah ada (§B.4) -- tidak ada
// API baru di sini. Endpoint keputusan (approve sinyal, sizing, backfill,
// settings, jalankan persona) SENGAJA tidak dipanggil sama sekali dari view
// ini -- itu prinsipnya, bukan lupa.
const { toast } = useAppToast()
const auth = useAuthStore()
const router = useRouter()
const loading = ref(true)

// ---------- Header: status data hari ini ----------
const latest = ref(null)
const dataOk = computed(() => {
  if (!latest.value?.source_flags) return null
  return !Object.values(latest.value.source_flags).includes('fail')
})
async function loadLatest() {
  const d = await get('/api/latest')
  latest.value = d.empty ? null : d
}

// ---------- [WAJIB] Prediksi -- satu-satunya yang tidak bisa di-backfill ----------
const duePredictions = ref([])
const showPredictForm = ref(false)
const p = ref({ horizon: '1w', confidence: '', targetDate: '', claim: '', basis: '' })

async function loadDue() {
  duePredictions.value = await get('/api/prediction/due')
}
async function savePrediction() {
  if (!p.value.claim.trim() || !p.value.targetDate) { toast('Claim & target date wajib diisi'); return }
  await post('/api/prediction/add', {
    date_made: today(), horizon: p.value.horizon, claim: p.value.claim,
    confidence: p.value.confidence || null, basis: p.value.basis, target_date: p.value.targetDate,
  })
  toast('Prediksi dicatat -- hari ini aman, streak jalan')
  p.value = { horizon: p.value.horizon, confidence: '', targetDate: '', claim: '', basis: '' }
  showPredictForm.value = false
}
async function scorePrediction(row, outcome) {
  await post('/api/prediction/score', { id: row.id, outcome })
  toast(`Prediksi dinilai: ${outcome}`)
  loadDue()
}

// ---------- [INTI] Berita HIGH ----------
const highNews = ref([])
async function loadHighNews() {
  highNews.value = await get('/api/news', { impact: 'HIGH', date_from: daysAgo(1), date_to: today(), limit: 30 })
}
async function toggleForReading(row) {
  await post('/api/news/for_reading', { id: row.id, for_reading: !row.for_reading })
  toast(row.for_reading ? 'Dilepas dari Reading' : 'Ditandai for Reading')
  loadHighNews()
}

// ---------- [BONUS] Konfirmasi tag/thread SUGGESTED ----------
async function removeTag(contentTagId) {
  await post(`/api/content_tags/${contentTagId}/remove`, {})
  loadHighNews()
}
async function confirmTag(contentTagId) {
  await post(`/api/content_tags/${contentTagId}/confirm`, {})
  toast('Tag diterima')
  loadHighNews()
}

const stanceDialogOpen = ref(false)
const stanceDialogLink = ref(null)
const selectedStance = ref('MENDUKUNG')
function openStanceDialog(threadLink) {
  stanceDialogLink.value = threadLink
  selectedStance.value = 'MENDUKUNG'
  stanceDialogOpen.value = true
}
async function confirmThreadLink() {
  await post(`/api/threads/link/${stanceDialogLink.value.link_id}/confirm`, { stance: selectedStance.value })
  toast(`Ditautkan ke "${stanceDialogLink.value.thread_title}"`)
  stanceDialogOpen.value = false
  loadHighNews()
}
async function rejectThreadLink(threadLink) {
  await post(`/api/threads/link/${threadLink.link_id}/reject`, {})
  loadHighNews()
}

// ---------- Thread aktif (ringkas, klik -> timeline penuh) ----------
const activeThreads = ref([])
async function loadActiveThreads() {
  const rows = await get('/api/threads/stats')
  activeThreads.value = rows.filter((t) => t.status === 'ACTIVE')
}

// ---------- Posisi ONGOING + warning earnings/event ----------
const ongoing = ref([])
const earningsWarnings = ref([])
async function loadOngoing() {
  const [journal, warnings] = await Promise.all([
    get('/api/journal', { limit: 200 }),
    get('/api/earnings/warnings'),
  ])
  ongoing.value = journal.filter((j) => j.outcome === 'ONGOING')
  earningsWarnings.value = warnings
}
function warningFor(instrument) {
  return earningsWarnings.value.find((w) => w.instrument === instrument)
}

async function loadAll() {
  loading.value = true
  await Promise.all([loadLatest(), loadDue(), loadHighNews(), loadActiveThreads(), loadOngoing()])
  loading.value = false
}
onMounted(loadAll)

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="mobile-shell">
    <header class="mobile-header">
      <div>
        <div class="mobile-brand">KASTARA</div>
        <div class="src">{{ today() }} · <span v-if="dataOk === true">🟢 data ok</span><span v-else-if="dataOk === false">🔴 ada source gagal</span><span v-else>-</span></div>
      </div>
      <div class="mobile-header-actions">
        <RouterLink to="/snapshot" class="btn small secondary">Dashboard →</RouterLink>
        <button class="btn small secondary" @click="logout">Keluar</button>
      </div>
    </header>

    <p v-if="loading" class="src" style="padding:16px">Memuat...</p>

    <template v-else>
      <section class="mobile-card mobile-wajib">
        <div class="mobile-card-title">WAJIB · ~1 menit</div>
        <p class="src">Catat 1 prediksi ATAU nilai 1 yang jatuh tempo -- satu-satunya yang tidak bisa dikejar besok.</p>
        <div class="mobile-btn-row">
          <button class="btn mobile-btn-big" @click="showPredictForm = !showPredictForm">+ Catat prediksi</button>
          <span v-if="duePredictions.length" class="badge HIGH">Nilai ({{ duePredictions.length }} due)</span>
        </div>

        <div v-if="showPredictForm" class="mobile-form">
          <select v-model="p.horizon"><option>1w</option><option>2w</option><option>1m</option></select>
          <input v-model="p.claim" type="text" placeholder="Klaim, mis. BTC tembus $70K sebelum FOMC">
          <input v-model="p.targetDate" type="date">
          <input v-model="p.confidence" type="number" min="0" max="100" placeholder="Confidence % (opsional)">
          <textarea v-model="p.basis" placeholder="Basis (opsional)"></textarea>
          <button class="btn mobile-btn-big" @click="savePrediction">Simpan Prediksi</button>
        </div>

        <div v-for="r in duePredictions" :key="r.id" class="mobile-predict-due">
          <div>{{ r.claim }}</div>
          <div class="src">target {{ r.target_date }} · confidence {{ r.confidence ?? '-' }}%</div>
          <div class="mobile-btn-row">
            <button class="btn small secondary" @click="scorePrediction(r, 'BENAR')">Benar</button>
            <button class="btn small danger" @click="scorePrediction(r, 'SALAH')">Salah</button>
            <button class="btn small secondary" @click="scorePrediction(r, 'PARTIAL')">Partial</button>
          </div>
        </div>
      </section>

      <section class="mobile-card">
        <div class="mobile-card-title">INTI · Berita HIGH</div>
        <p v-if="!highNews.length" class="src">tidak ada berita HIGH hari ini/kemarin</p>
        <div v-for="n in highNews" :key="n.id" class="mobile-news-row">
          <a v-if="n.raw_url" :href="n.raw_url" target="_blank" rel="noopener">{{ n.headline }}</a>
          <span v-else>{{ n.headline }}</span>
          <div class="src">{{ n.date }} · {{ n.source }}</div>

          <div v-for="t in n.tags" :key="t.id" class="mobile-chip-row">
            <input v-if="t.source === 'SUGGESTED'" type="checkbox" @change="confirmTag(t.id)">
            <span class="badge" :class="FACET_COLOR[t.facet]" :style="t.source === 'SUGGESTED' ? { border: '1px dashed currentColor', opacity: 0.75 } : {}">
              {{ t.canonical }}<span v-if="t.source === 'SUGGESTED'">?</span>
            </span>
            <a href="#" @click.prevent="removeTag(t.id)">&times;</a>
          </div>

          <div v-for="tl in n.thread_links || []" :key="tl.link_id" class="mobile-chip-row">
            <template v-if="tl.link_status === 'SUGGESTED'">
              <span class="badge link-suggested">Saran: {{ tl.thread_title }}?</span>
              <button class="btn small secondary" @click="openStanceDialog(tl)">Konfirmasi</button>
              <button class="btn small danger" @click="rejectThreadLink(tl)">Tolak</button>
            </template>
            <template v-else>
              <span class="badge link-confirmed">{{ tl.thread_title }} ({{ tl.stance }})</span>
              <button class="btn small danger" @click="rejectThreadLink(tl)">Lepas</button>
            </template>
          </div>

          <button
            class="btn small mobile-btn-big" :class="n.for_reading ? 'key-on' : 'secondary'"
            @click="toggleForReading(n)"
          >{{ n.for_reading ? '★ Reading' : '📖 tandai for Reading' }}</button>
        </div>
      </section>

      <section class="mobile-card">
        <div class="mobile-card-title">BONUS · Thread Aktif</div>
        <p v-if="!activeThreads.length" class="src">tidak ada thread ACTIVE</p>
        <RouterLink v-for="t in activeThreads" :key="t.thread_id" :to="`/threads/${t.thread_id}`" class="mobile-thread-row">
          <span>{{ t.title }}</span>
          <span class="src">🟢{{ t.composition?.MENDUKUNG || 0 }} / 🔴{{ t.composition?.KONTRA || 0 }}<template v-if="t.pending_suggested"> · {{ t.pending_suggested }} saran baru</template></span>
        </RouterLink>
      </section>

      <section class="mobile-card">
        <div class="mobile-card-title">Posisi ONGOING</div>
        <p v-if="!ongoing.length" class="src">tidak ada posisi terbuka</p>
        <div v-for="j in ongoing" :key="j.id" class="mobile-ongoing-row">
          <span>{{ j.instrument }}</span>
          <span v-if="warningFor(j.instrument)" class="src" :style="{ color: warningFor(j.instrument).hard_rule ? 'var(--fail)' : 'var(--muted)' }">
            ⚠ earnings H-{{ warningFor(j.instrument).days_until }} ({{ warningFor(j.instrument).earnings_date }})
            <template v-if="warningFor(j.instrument).hard_rule"> -- WAJIB tutup penuh</template>
          </span>
        </div>
      </section>
    </template>

    <Dialog v-model:visible="stanceDialogOpen" modal header="Konfirmasi Tautan Thread" style="width:90vw; max-width:420px">
      <p v-if="stanceDialogLink" class="src">Tautkan ke "<b>{{ stanceDialogLink.thread_title }}</b>" -- pilih stance:</p>
      <select v-model="selectedStance" style="width:100%; margin-bottom:12px">
        <option value="MENDUKUNG">MENDUKUNG</option>
        <option value="KONTRA">KONTRA</option>
        <option value="NETRAL">NETRAL</option>
      </select>
      <button class="btn mobile-btn-big" @click="confirmThreadLink">Konfirmasi</button>
    </Dialog>
  </div>
</template>

<style scoped>
.mobile-shell {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  padding-bottom: 32px;
}
.mobile-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--bg);
  z-index: 5;
}
.mobile-brand {
  font-weight: 700;
  letter-spacing: .5px;
  font-size: 14px;
}
.mobile-header-actions {
  display: flex;
  gap: 8px;
}
.mobile-card {
  margin: 12px 16px;
  padding: 14px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
}
.mobile-wajib {
  border-color: var(--accent);
}
.mobile-card-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .5px;
  color: var(--muted);
  margin-bottom: 8px;
}
.mobile-btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
}
.mobile-btn-big {
  min-height: 44px;
  padding: 10px 16px;
  font-size: 14px;
}
.mobile-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}
.mobile-form input, .mobile-form select, .mobile-form textarea {
  width: 100%;
}
.mobile-predict-due {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.mobile-news-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.mobile-news-row:last-child {
  border-bottom: none;
}
.mobile-chip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.mobile-thread-row, .mobile-ongoing-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  text-decoration: none;
  color: inherit;
}
.mobile-thread-row:last-child, .mobile-ongoing-row:last-child {
  border-bottom: none;
}
</style>
