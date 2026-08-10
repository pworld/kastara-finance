<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import Column from 'primevue/column'
import DataTable from '../components/DataTable.vue'
import { get, post } from '../lib/api'
import { fmt, LANE_CLASS } from '../lib/format'
import { drawCandleChart } from '../lib/candleChart'
import { useAppToast } from '../composables/useAppToast'

// Port dari web/static/js/panel5.js (lihat docs/migrationFE.md Fase 2 poin
// 4 -- chart SVG dibungkus APA ADANYA, tidak ditulis ulang/diganti lib).
const { toast } = useAppToast()

const CHART_PADDING = 220 // >= MA200 period, biar MA200 valid sejak candle pertama yang tampil
const chartVisible = ref(90)

const assets = ref([])
const instrument = ref('')
const laneBadge = ref(null)
const chartMeta = ref('')
const chartEl = ref(null)
const signals = ref([])

async function loadChart() {
  if (!instrument.value) return
  const [rows, zones, sigs] = await Promise.all([
    get('/api/asset_ohlcv', { instrument: instrument.value, limit: chartVisible.value + CHART_PADDING }),
    get('/api/sr_zones', { instrument: instrument.value }),
    get('/api/signals', { instrument: instrument.value }),
  ])
  signals.value = sigs
  await nextTick()
  chartMeta.value = drawCandleChart(chartEl.value, rows, zones, sigs, chartVisible.value)
  loadInstrumentLaneBadge(instrument.value)
}

async function loadInstrumentLaneBadge(inst) {
  const meta = await get('/api/instrument_meta', { instrument: inst })
  laneBadge.value = meta.lane || null
}

// ---------- Sinyal (Breakout/Retest) ----------
function signalStatus(s) {
  if (s.approved) return 'APPROVED'
  if (s.notes) return 'REJECTED'
  return 'pending'
}
function signalBadgeClass(status) {
  if (status === 'APPROVED') return 'LOW'
  if (status === 'REJECTED') return 'HIGH'
  return 'MED'
}
async function reviewSignal(s, approved) {
  let notes = null
  if (!approved) notes = window.prompt('Alasan reject (opsional):') || ''
  await post('/api/signals/review', { id: s.id, approved, notes })
  toast(approved ? 'Sinyal di-approve' : 'Sinyal di-reject')
  loadChart()
}

// ---------- Context mini-charts (30 hari, independen instrument) ----------
const ctxFields = [
  { key: 'dxy_close', label: 'DXY' },
  { key: 'sp500_close', label: 'S&P 500' },
  { key: 'us10y_yield', label: 'US10Y' },
  { key: 'fear_greed_value', label: 'Fear & Greed' },
]
const ctxRefs = ref({})
function setCtxRef(key, el) { if (el) ctxRefs.value[key] = el }

function drawMiniLine(svg, values) {
  const W = 300, H = 100, pad = 6
  const points = values.map((v, i) => ({ v, i })).filter((o) => o.v !== null && o.v !== undefined)
  if (points.length < 2) {
    svg.innerHTML = `<text x="150" y="50" fill="#8b949e" text-anchor="middle" font-size="11">data kurang</text>`
    return
  }
  const vals = points.map((o) => o.v)
  const lo = Math.min(...vals), hi = Math.max(...vals)
  const span = (hi - lo) || 1
  const n = values.length
  const x = (i) => pad + (n === 1 ? 0 : (i / (n - 1)) * (W - 2 * pad))
  const y = (v) => H - pad - ((v - lo) / span) * (H - 2 * pad)
  let d = ''
  points.forEach(({ v, i }) => { d += `${d === '' ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)} ` })
  const up = vals[vals.length - 1] >= vals[0]
  svg.innerHTML = `<path d="${d}" fill="none" stroke="${up ? '#3fb950' : '#f85149'}" stroke-width="1.6"/>`
}

async function loadContextCharts() {
  const rows = await get('/api/daily_market', { limit: 30 })
  const ordered = [...rows].reverse()
  await nextTick()
  for (const f of ctxFields) {
    const el = ctxRefs.value[f.key]
    if (el) drawMiniLine(el, ordered.map((r) => r[f.key]))
  }
}

onMounted(async () => {
  assets.value = await get('/api/assets')
  if (assets.value.includes('BTC')) instrument.value = 'BTC'
  else if (assets.value.length) instrument.value = assets.value[0]
  if (assets.value.length) await loadChart()
  loadContextCharts()
})
watch(instrument, loadChart)
watch(chartVisible, loadChart)
</script>

<template>
  <section>
    <h2>Chart Harga + S&amp;R + Sinyal</h2>
    <div class="panel">
      <div class="chart-head">
        <label class="src">Instrument</label>
        <select v-model="instrument">
          <option v-for="i in assets" :key="i">{{ i }}</option>
        </select>
        <span v-if="laneBadge"><span class="badge" :class="LANE_CLASS[laneBadge] || 'lane-none'">LANE {{ laneBadge }}</span></span>
        <span class="ma-legend">
          <span class="ma-swatch" style="background:#e3b341"></span>MA50
          <span class="ma-swatch" style="background:#a371f7"></span>MA100
          <span class="ma-swatch" style="background:#f778ba"></span>MA200
        </span>
      </div>
      <div class="chart-head">
        <label class="src">Rentang</label>
        <select v-model.number="chartVisible" style="width:auto">
          <option :value="30">1 Bulan</option>
          <option :value="90">3 Bulan</option>
          <option :value="180">6 Bulan</option>
          <option :value="365">1 Tahun</option>
          <option :value="9999">Semua</option>
        </select>
        <span id="chartMeta">{{ chartMeta }}</span>
      </div>
      <svg id="chart" ref="chartEl" viewBox="0 0 800 400" preserveAspectRatio="none"></svg>
    </div>
  </section>

  <section>
    <h2>Sinyal (Breakout/Retest)</h2>
    <div class="panel">
      <DataTable :rows="signals" :dataKey="'id'" :searchFields="['date', 'signal_type']" emptyMessage="belum ada sinyal untuk instrument ini">
        <Column field="date" header="Tgl" sortable><template #body="{ data }"><span class="src">{{ data.date }}</span></template></Column>
        <Column field="signal_type" header="Tipe" sortable>
          <template #body="{ data }"><span class="badge" :class="data.signal_type">{{ data.signal_type }}</span></template>
        </Column>
        <Column header="Entry/SL/TP1">
          <template #body="{ data }">{{ data.entry_price ? `${fmt(data.entry_price)} / ${fmt(data.sl_price)} / ${fmt(data.tp1_price)}` : '-' }}</template>
        </Column>
        <Column field="rr_ratio" header="R:R" sortable><template #body="{ data }">{{ data.rr_ratio ? data.rr_ratio.toFixed(2) : '-' }}</template></Column>
        <Column header="Status">
          <template #body="{ data }">
            <span v-if="signalStatus(data) === 'pending'" class="badge" :class="signalBadgeClass('pending')">pending</span>
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <template v-if="signalStatus(data) === 'pending'">
              <button class="btn small secondary" @click="reviewSignal(data, true)">Approve</button>
              <button class="btn small danger" @click="reviewSignal(data, false)">Reject</button>
            </template>
            <span v-else class="badge" :class="signalBadgeClass(signalStatus(data))">{{ signalStatus(data) }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
  </section>

  <section>
    <h2>Context Charts (30 hari)</h2>
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));">
      <div v-for="f in ctxFields" :key="f.key" class="panel">
        <h3>{{ f.label }}</h3>
        <svg class="ctx-chart" :ref="(el) => setCtxRef(f.key, el)" viewBox="0 0 300 100" preserveAspectRatio="none"></svg>
      </div>
    </div>
  </section>
</template>
