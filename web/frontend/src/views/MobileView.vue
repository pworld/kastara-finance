<script setup>
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import Dialog from 'primevue/dialog'
import { get, post } from '../lib/api'
import { today, daysAgo, FACET_COLOR, fmt } from '../lib/format'
import { drawCandleChart } from '../lib/candleChart'
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

// ---------- Get News / Get Price (6 Agustus 2026) ----------
// Giel minta trigger manual terpisah dari HP -- pola sama "Trigger Berita"
// di SnapshotView.vue TAPI dipecah 2 tombol scoped (`run_news_only()` /
// `run_price_only()`, pipeline/run_daily.py) drpd 1 tombol yang selalu
// jalankan semua scraper (kadang cuma mau lihat berita terbaru TANPA
// nunggu semua scraper market ikut jalan, atau sebaliknya). Sinkron
// (blocking) sama seperti tombol desktop -- bukan background thread.
const newsFetching = ref(false)
const priceFetching = ref(false)
async function fetchNewsNow() {
  newsFetching.value = true
  const r = await post('/api/news/fetch_now', {})
  newsFetching.value = false
  if (r.error) { toast(`Gagal: ${r.error}`); return }
  const deadStr = r.rss_dead && r.rss_dead.length ? `, feed mati: ${r.rss_dead.join(', ')}` : ''
  toast(`${r.news_inserted} berita baru, RSS ${r.rss_ok} ok${deadStr}`)
  loadHighNews()
}
async function fetchPriceNow() {
  priceFetching.value = true
  const r = await post('/api/price/fetch_now', {})
  priceFetching.value = false
  if (r.error) { toast(`Gagal: ${r.error}`); return }
  toast(`${r.asset_rows} baris market -- ${r.sources_ok} sumber ok / ${r.sources_fail} gagal`)
  loadLatest()
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

// ---------- [INTI] Berita HIGH (default) / semua (toggle, 6 Agustus 2026) ----------
// Default tetap HIGH-only (prinsip layar tunggal tidak berubah), tapi Giel
// minta bisa lihat SEMUA berita hari ini dari HP juga -- toggle drpd ganti
// default, biar buka /m tetap cepat/ringkas kalau tidak disentuh.
const showAllNews = ref(false)
const highNews = ref([])
async function loadHighNews() {
  const params = { date_from: daysAgo(1), date_to: today(), limit: showAllNews.value ? 100 : 30 }
  if (!showAllNews.value) params.impact = 'HIGH'
  highNews.value = await get('/api/news', params)
}
function toggleShowAllNews() {
  showAllNews.value = !showAllNews.value
  loadHighNews()
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
// 6 Agustus 2026: mobile sempat ketinggalan F-1/F-2 (Opini Sekunder +
// readability layer) yang sudah ada di ThreadDetailView.vue sejak 3-4
// Agustus -- data-nya (trend_30d, shift_warning, opinions) SUDAH ikut di
// /api/threads/stats (thread_stats() di writes.py), cuma belum ditampilkan
// di sini. Ditambah di sini, bukan endpoint baru.
// (Sempat coba tampilkan thread non-ACTIVE juga di sini krn salah duga
// keluhan "inactive tidak jalan" soal visibility -- ternyata itu soal
// tombol Simpan status CLOSED gagal di ThreadsView.vue desktop, sudah
// diperbaiki di sana. Giel eksplisit minta bagian non-aktif TIDAK usah
// ditampilkan di /m -- balik ke ACTIVE-only, sesuai prinsip layar tunggal.)
const activeThreads = ref([])
async function loadActiveThreads() {
  const rows = await get('/api/threads/stats')
  activeThreads.value = rows.filter((t) => t.status === 'ACTIVE')
}

const ALLOWED_SOURCE_TYPE = ['VIDEO', 'BOOK', 'PAPER', 'PODCAST', 'REPORT', 'OTHER']
const ALLOWED_TESTABLE = ['TESTABLE', 'SPEKULATIF']
const opinionDialogOpen = ref(false)
const opinionThread = ref(null)
const opinionForm = ref({
  source_type: 'VIDEO', source_ref: '', author: '', my_summary: '', core_claim: '',
  testable: 'TESTABLE', my_stance: '', conflict_of_interest: '', relation_to_view: '',
})
function openOpinionDialog(thread) {
  opinionThread.value = thread
  opinionForm.value = {
    source_type: 'VIDEO', source_ref: '', author: '', my_summary: '', core_claim: '',
    testable: 'TESTABLE', my_stance: '', conflict_of_interest: '', relation_to_view: '',
  }
  opinionDialogOpen.value = true
}
async function saveOpinion() {
  const f = opinionForm.value
  if (!f.source_ref.trim() || !f.my_summary.trim() || !f.core_claim.trim()) {
    toast('Sumber, ringkasan, & klaim inti wajib diisi'); return
  }
  await post('/api/secondary_opinions', {
    ...f, author: f.author || null, my_stance: f.my_stance || null,
    conflict_of_interest: f.conflict_of_interest || null,
    relation_to_view: f.relation_to_view || null,
    thread_id: opinionThread.value.thread_id,
  })
  toast('Opini sekunder dicatat')
  opinionDialogOpen.value = false
  loadActiveThreads()
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

// ---------- Portofolio / Holdings (6 Agustus 2026) ----------
// Sama alasan spt Opini Sekunder di atas -- ketinggalan dari
// UniverseView.vue Tab Portofolio (docs/universe_portfolio_restructure_v1.md,
// 3 Agustus). Log holding baru diperlakukan sama seperti catat prediksi
// (record-keeping, bukan keputusan trading) -- BUKAN pelanggaran prinsip
// "endpoint keputusan tidak dirender di sini" (itu utk approve sinyal,
// sizing, backfill, settings, run persona -- lihat komentar atas file ini).
const ALLOWED_BOOK = ['TRADE', 'INVEST']
const ALLOWED_CURRENCY = ['IDR', 'USD', 'SGD']
const ALLOWED_SOP_CATEGORY = ['SAHAM_IHSG', 'EMAS', 'CRYPTO', 'VALAS', 'GLOBAL_EQ', 'KAS_IDR']
const holdings = ref([])
const allocation = ref(null)
const showHoldingForm = ref(false)
const holdingForm = ref({
  instrument: '', provider: '', book: 'INVEST', quantity: '', unit: '', avgPrice: '',
  currency: 'IDR', sopCategory: 'SAHAM_IHSG', openedAt: '', notes: '',
})
async function loadHoldings() {
  const [h, a] = await Promise.all([get('/api/holdings'), get('/api/portfolio/allocation')])
  holdings.value = h
  allocation.value = a
}
async function saveHolding() {
  const f = holdingForm.value
  if (!f.instrument.trim() || !f.provider.trim() || !f.unit.trim() || !f.quantity) {
    toast('Instrumen, provider, unit, & quantity wajib diisi'); return
  }
  await post('/api/holdings', {
    instrument: f.instrument, provider: f.provider, book: f.book,
    quantity: Number(f.quantity), unit: f.unit,
    avg_price: f.avgPrice ? Number(f.avgPrice) : null, currency: f.currency,
    sop_category: f.sopCategory, opened_at: f.openedAt || null, notes: f.notes || null,
  })
  toast('Holding dicatat')
  holdingForm.value = {
    instrument: '', provider: '', book: f.book, quantity: '', unit: '', avgPrice: '',
    currency: f.currency, sopCategory: f.sopCategory, openedAt: '', notes: '',
  }
  showHoldingForm.value = false
  loadHoldings()
}

// ---------- Chart (6 Agustus 2026) -- reuse drawCandleChart dari ChartView.vue
// (diekstrak ke lib/candleChart.js), viewBox SVG scale otomatis ke lebar
// layar HP lewat CSS. Read-only murni -- TIDAK ada tombol approve/reject
// sinyal di sini (itu endpoint keputusan, prinsip yg sama seperti di atas).
// Dimuat SETELAH loading=false (bukan di Promise.all bareng data lain) krn
// <svg ref> baru ada di DOM stlh v-else kartu-kartu di-render.
const CHART_VISIBLE = 60
const CHART_PADDING = 220
const chartAssets = ref([])
const chartInstrument = ref('')
const chartEl = ref(null)
const chartMeta = ref('')
async function loadChart() {
  if (!chartInstrument.value) return
  const [rows, zones, sigs] = await Promise.all([
    get('/api/asset_ohlcv', { instrument: chartInstrument.value, limit: CHART_VISIBLE + CHART_PADDING }),
    get('/api/sr_zones', { instrument: chartInstrument.value }),
    get('/api/signals', { instrument: chartInstrument.value }),
  ])
  await nextTick()
  chartMeta.value = drawCandleChart(chartEl.value, rows, zones, sigs, CHART_VISIBLE)
}
watch(chartInstrument, loadChart)

async function loadAll() {
  loading.value = true
  await Promise.all([loadLatest(), loadDue(), loadHighNews(), loadActiveThreads(), loadOngoing(), loadHoldings()])
  loading.value = false
  await nextTick()
  chartAssets.value = await get('/api/assets')
  if (chartAssets.value.includes('BTC')) chartInstrument.value = 'BTC'
  else if (chartAssets.value.length) chartInstrument.value = chartAssets.value[0]
}
onMounted(loadAll)

// ---------- Tab (6 Agustus 2026) -- Giel lapor scroll kepanjangan begitu
// Chart/Thread/Portofolio ditambah (6 kartu ditumpuk 1 layar). Pecah jadi
// tab spt ThreadDetailView.vue/UniverseView.vue (pola sama, activeTab +
// TABS computed) -- Utama gabung WAJIB+INTI (ritual harian, harus tetap
// jadi 1 langkah bukan 2 tab terpisah), sisanya 1 tab per kartu.
const activeTab = ref('utama')
const TABS = computed(() => [
  { id: 'utama', label: 'Utama' },
  { id: 'chart', label: 'Chart' },
  { id: 'thread', label: `Thread${activeThreads.value.length ? ` (${activeThreads.value.length})` : ''}` },
  { id: 'posisi', label: `Posisi${holdings.value.length + ongoing.value.length ? ` (${holdings.value.length + ongoing.value.length})` : ''}` },
])

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

    <div class="mobile-quick-actions">
      <button class="btn small secondary" :disabled="newsFetching" @click="fetchNewsNow">
        {{ newsFetching ? 'Mengambil berita...' : '📰 Get News' }}
      </button>
      <button class="btn small secondary" :disabled="priceFetching" @click="fetchPriceNow">
        {{ priceFetching ? 'Mengambil harga...' : '💹 Get Price' }}
      </button>
    </div>

    <p v-if="loading" class="src" style="padding:16px">Memuat...</p>

    <template v-else>
      <div class="tab-bar">
        <button
          v-for="t in TABS" :key="t.id" class="tab-btn" :class="{ active: activeTab === t.id }"
          @click="activeTab = t.id"
        >{{ t.label }}</button>
      </div>

      <template v-if="activeTab === 'utama'">
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
        <div class="mobile-card-title" style="display:flex; justify-content:space-between; align-items:center">
          <span>INTI · {{ showAllNews ? 'Semua Berita' : 'Berita HIGH' }}</span>
          <button class="btn small secondary" @click="toggleShowAllNews">{{ showAllNews ? 'Cuma HIGH' : 'Semua berita' }}</button>
        </div>
        <p v-if="!highNews.length" class="src">tidak ada berita {{ showAllNews ? '' : 'HIGH ' }}hari ini/kemarin</p>
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
      </template>

      <template v-if="activeTab === 'chart'">
      <section class="mobile-card">
        <div class="mobile-card-title">Chart</div>
        <select v-if="chartAssets.length" v-model="chartInstrument" style="width:auto; margin-bottom:8px">
          <option v-for="a in chartAssets" :key="a" :value="a">{{ a }}</option>
        </select>
        <svg viewBox="0 0 800 400" preserveAspectRatio="none" ref="chartEl" class="mobile-chart-svg"></svg>
        <p v-if="chartMeta" class="src" style="margin-top:6px">{{ chartMeta }}</p>
      </section>
      </template>

      <template v-if="activeTab === 'thread'">
      <section class="mobile-card">
        <div class="mobile-card-title">BONUS · Thread Aktif</div>
        <p v-if="!activeThreads.length" class="src">tidak ada thread ACTIVE</p>
        <div v-for="t in activeThreads" :key="t.thread_id" class="mobile-thread-block">
          <RouterLink :to="`/threads/${t.thread_id}`" class="mobile-thread-row">
            <span>{{ t.title }}<span v-if="t.shift_warning" class="badge HIGH" style="margin-left:6px">⚠ shift</span></span>
            <span class="src">🟢{{ t.composition?.MENDUKUNG || 0 }} / 🔴{{ t.composition?.KONTRA || 0 }} / ⚪{{ t.composition?.NETRAL || 0 }}<template v-if="t.pending_suggested"> · {{ t.pending_suggested }} saran baru</template></span>
          </RouterLink>
          <div class="src" style="margin-top:2px">
            30 hari: 🟢{{ t.trend_30d?.MENDUKUNG || 0 }} / 🔴{{ t.trend_30d?.KONTRA || 0 }} / ⚪{{ t.trend_30d?.NETRAL || 0 }}
            <template v-if="t.milestone_count"> · ★{{ t.milestone_count }}</template>
            <template v-if="t.opinions?.total"> · {{ t.opinions.total }} opini ({{ t.opinions.sejalan }} sejalan/{{ t.opinions.menantang }} menantang)</template>
          </div>
          <button class="btn small secondary" style="margin-top:6px" @click="openOpinionDialog(t)">+ Opini Sekunder</button>
        </div>
      </section>
      </template>

      <template v-if="activeTab === 'posisi'">
      <section class="mobile-card">
        <div class="mobile-card-title">Portofolio</div>
        <div v-if="allocation" class="src" style="margin-bottom:8px">
          Total (est. IDR): {{ fmt(allocation.total_idr) }}
          <template v-if="allocation.excluded?.length"> · {{ allocation.excluded.length }} holding belum terhitung (avg_price/kategori kosong)</template>
        </div>
        <div class="mobile-btn-row">
          <button class="btn mobile-btn-big" @click="showHoldingForm = !showHoldingForm">+ Tambah Holding</button>
        </div>
        <div v-if="showHoldingForm" class="mobile-form">
          <input v-model="holdingForm.instrument" type="text" placeholder="Instrumen, mis. BBCA / BTC">
          <input v-model="holdingForm.provider" type="text" placeholder="Provider, mis. Stockbit / Indodax">
          <select v-model="holdingForm.book">
            <option v-for="b in ALLOWED_BOOK" :key="b" :value="b">{{ b }}</option>
          </select>
          <input v-model="holdingForm.quantity" type="number" placeholder="Quantity">
          <input v-model="holdingForm.unit" type="text" placeholder="Unit, mis. lembar / BTC">
          <input v-model="holdingForm.avgPrice" type="number" placeholder="Avg price (opsional)">
          <select v-model="holdingForm.currency">
            <option v-for="c in ALLOWED_CURRENCY" :key="c" :value="c">{{ c }}</option>
          </select>
          <select v-model="holdingForm.sopCategory">
            <option v-for="c in ALLOWED_SOP_CATEGORY" :key="c" :value="c">{{ c }}</option>
          </select>
          <input v-model="holdingForm.openedAt" type="date">
          <textarea v-model="holdingForm.notes" placeholder="Catatan (opsional)"></textarea>
          <button class="btn mobile-btn-big" @click="saveHolding">Simpan Holding</button>
        </div>
        <p v-if="!holdings.length" class="src" style="margin-top:8px">belum ada holding tercatat</p>
        <div v-for="h in holdings" :key="h.id" class="mobile-ongoing-row">
          <span>{{ h.instrument }} <span class="src">({{ h.provider }})</span></span>
          <span class="src">{{ h.quantity }} {{ h.unit }} · {{ h.book }}</span>
        </div>
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

    <Dialog v-model:visible="opinionDialogOpen" modal header="Opini Sekunder" style="width:90vw; max-width:420px">
      <p v-if="opinionThread" class="src">Utk thread "<b>{{ opinionThread.title }}</b>"</p>
      <div class="mobile-form">
        <select v-model="opinionForm.source_type">
          <option v-for="s in ALLOWED_SOURCE_TYPE" :key="s" :value="s">{{ s }}</option>
        </select>
        <input v-model="opinionForm.source_ref" type="text" placeholder="Sumber (URL / judul buku / penerbit)">
        <input v-model="opinionForm.author" type="text" placeholder="Author (opsional)">
        <textarea v-model="opinionForm.my_summary" placeholder="Ringkasan versi kamu (wajib, bukan transkrip)"></textarea>
        <input v-model="opinionForm.core_claim" type="text" placeholder="Klaim inti, satu kalimat">
        <select v-model="opinionForm.testable">
          <option v-for="t in ALLOWED_TESTABLE" :key="t" :value="t">{{ t }}</option>
        </select>
        <textarea v-model="opinionForm.my_stance" placeholder="Sikap kamu -- setuju/tidak & kenapa (opsional)"></textarea>
        <input v-model="opinionForm.conflict_of_interest" type="text" placeholder="Conflict of interest (opsional)">
        <select v-model="opinionForm.relation_to_view">
          <option value="">-- belum diklasifikasi --</option>
          <option value="SEJALAN">SEJALAN</option>
          <option value="MENANTANG">MENANTANG</option>
        </select>
        <button class="btn mobile-btn-big" @click="saveOpinion">Simpan Opini</button>
      </div>
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
.mobile-quick-actions {
  display: flex;
  gap: 8px;
  padding: 10px 16px 0;
}
.mobile-quick-actions button {
  flex: 1;
}
.tab-bar {
  display: flex;
  gap: 2px;
  overflow-x: auto;
  padding: 12px 16px 0;
  border-bottom: 1px solid var(--border);
}
.tab-btn {
  flex-shrink: 0;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.tab-btn.active {
  color: var(--text);
  border-bottom-color: var(--accent);
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
  text-decoration: none;
  color: inherit;
}
.mobile-ongoing-row {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.mobile-ongoing-row:last-child {
  border-bottom: none;
}
.mobile-thread-block {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.mobile-thread-block:last-child {
  border-bottom: none;
}
.mobile-chart-svg {
  width: 100%;
  height: auto;
  aspect-ratio: 800 / 400;
  background: var(--bg);
  border-radius: 6px;
}
</style>
