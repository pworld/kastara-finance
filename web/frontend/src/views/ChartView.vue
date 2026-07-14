<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import Column from 'primevue/column'
import DataTable from '../components/DataTable.vue'
import { get, post } from '../lib/api'
import { fmt, LANE_CLASS } from '../lib/format'
import { rollingMA } from '../lib/chartMath'
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

// ---------- drawCandleChart -- port nyaris verbatim dari panel5.js ----------
function drawCandleChart(allRows, zones, sigs, visibleCount) {
  const svg = chartEl.value
  if (!svg) return
  const W = 800, H = 400
  const padL = 6, padR = 50, padT = 10, priceBottom = 270, volTop = 292, volBottom = 370, axisY = 390

  const closesFull = allRows.map((r) => r.close)
  const volumesFull = allRows.map((r) => r.volume)
  const ma50Full = rollingMA(closesFull, 50)
  const ma100Full = rollingMA(closesFull, 100)
  const ma200Full = rollingMA(closesFull, 200)
  const volMaFull = rollingMA(volumesFull, 20)

  const startIdx = Math.max(0, allRows.length - visibleCount)
  const rows = allRows.slice(startIdx)
  const ma50 = ma50Full.slice(startIdx), ma100 = ma100Full.slice(startIdx), ma200 = ma200Full.slice(startIdx)
  const volMa = volMaFull.slice(startIdx)

  const valid = rows.filter((r) => r.close !== null)
  if (valid.length < 2) {
    svg.innerHTML = `<text x="400" y="140" fill="#8b949e" text-anchor="middle">data kurang</text>`
    chartMeta.value = ''
    return
  }

  let lo = Math.min(...valid.map((r) => r.low ?? r.close))
  let hi = Math.max(...valid.map((r) => r.high ?? r.close))
  ;[ma50, ma100, ma200].forEach((arr) => arr.forEach((v) => { if (v !== null) { lo = Math.min(lo, v); hi = Math.max(hi, v) } }))
  const priceMargin = (hi - lo) * 0.5 || hi * 0.5
  const relevantZones = zones.filter((z) => z.zone_upper >= lo - priceMargin && z.zone_lower <= hi + priceMargin)
  relevantZones.forEach((z) => { lo = Math.min(lo, z.zone_lower); hi = Math.max(hi, z.zone_upper) })
  const span = (hi - lo) || 1
  const n = rows.length
  const slot = (W - padL - padR) / n
  const x = (i) => padL + i * slot + slot / 2
  const y = (v) => priceBottom - ((v - lo) / span) * (priceBottom - padT)

  const maxVol = Math.max(1, ...rows.map((r) => r.volume || 0), ...volMa.filter((v) => v !== null))
  const yVol = (v) => volBottom - (v / maxVol) * (volBottom - volTop)

  let svgParts = []

  const priceTicks = 5
  for (let t = 0; t <= priceTicks; t++) {
    const v = lo + (span * t) / priceTicks
    const yy = y(v)
    svgParts.push(`<line x1="0" y1="${yy.toFixed(1)}" x2="${(W - padR + 4).toFixed(1)}" y2="${yy.toFixed(1)}" stroke="#2a313c" stroke-width="0.5"/>`)
    svgParts.push(`<text x="${(W - padR + 8).toFixed(1)}" y="${(yy + 3).toFixed(1)}" fill="#8b949e" font-size="10">${fmt(v)}</text>`)
  }

  relevantZones.forEach((z) => {
    const yTop = y(z.zone_upper), yBot = y(z.zone_lower)
    const col = z.zone_type === 'SUPPORT' ? '#3fb950' : '#f85149'
    svgParts.push(`<rect x="0" y="${yTop.toFixed(1)}" width="${W - padR}" height="${Math.max(1, yBot - yTop).toFixed(1)}" fill="${col}" opacity="0.08"/>`)
  })

  const bw = Math.max(1, slot * 0.6)
  rows.forEach((r, i) => {
    if (r.close === null) return
    const up = r.close >= r.open
    const col = up ? '#3fb950' : '#f85149'
    const cx = x(i)
    svgParts.push(`<line x1="${cx}" y1="${y(r.high).toFixed(1)}" x2="${cx}" y2="${y(r.low).toFixed(1)}" stroke="${col}" stroke-width="1"/>`)
    const bodyTop = y(Math.max(r.open, r.close)), bodyBot = y(Math.min(r.open, r.close))
    svgParts.push(`<rect x="${(cx - bw / 2).toFixed(1)}" y="${bodyTop.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1, bodyBot - bodyTop).toFixed(1)}" fill="${col}"/>`)
  })

  function maPath(arr, color) {
    let d = ''
    arr.forEach((v, i) => {
      if (v === null) return
      d += `${d === '' ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)} `
    })
    if (d) svgParts.push(`<path d="${d}" fill="none" stroke="${color}" stroke-width="1.4" opacity="0.9"/>`)
  }
  maPath(ma50, '#e3b341')
  maPath(ma100, '#a371f7')
  maPath(ma200, '#f778ba')

  const dateIndex = {}
  rows.forEach((r, i) => { dateIndex[r.date] = i })
  sigs.forEach((s) => {
    const i = dateIndex[s.date]
    if (i === undefined) return
    const cy = s.entry_price ? y(s.entry_price) : y(rows[i].close)
    const col = s.signal_type === 'BREAKOUT' ? '#3fb950' : '#4c9aff'
    const shape = s.signal_type === 'BREAKOUT'
      ? `<circle cx="${x(i).toFixed(1)}" cy="${cy.toFixed(1)}" r="4" fill="${col}"/>`
      : `<circle cx="${x(i).toFixed(1)}" cy="${cy.toFixed(1)}" r="4" fill="none" stroke="${col}" stroke-width="2"/>`
    svgParts.push(shape)
  })

  rows.forEach((r, i) => {
    if (r.volume === null || r.volume === undefined) return
    const up = r.close >= r.open
    const col = up ? '#3fb950' : '#f85149'
    const cx = x(i)
    const barTop = yVol(r.volume)
    svgParts.push(`<rect x="${(cx - bw / 2).toFixed(1)}" y="${barTop.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1, volBottom - barTop).toFixed(1)}" fill="${col}" opacity="0.6"/>`)
  })
  let volMaPath = ''
  volMa.forEach((v, i) => {
    if (v === null) return
    volMaPath += `${volMaPath === '' ? 'M' : 'L'}${x(i).toFixed(1)},${yVol(v).toFixed(1)} `
  })
  if (volMaPath) svgParts.push(`<path d="${volMaPath}" fill="none" stroke="#4c9aff" stroke-width="1.2"/>`)

  svgParts.push(`<line x1="0" y1="${volTop - 8}" x2="${W}" y2="${volTop - 8}" stroke="#2a313c" stroke-width="1"/>`)

  const monthBoundaries = []
  let lastMonth = null
  rows.forEach((r, i) => {
    if (!r.date) return
    const ym = r.date.slice(0, 7)
    if (ym !== lastMonth) { monthBoundaries.push(i); lastMonth = ym }
  })
  const maxLabels = 9
  const step = Math.max(1, Math.ceil(monthBoundaries.length / maxLabels))
  monthBoundaries.filter((_, idx) => idx % step === 0).forEach((i) => {
    const cx = x(i)
    const d = new Date(rows[i].date + 'T00:00:00Z')
    const label = d.toLocaleDateString('id-ID', { month: 'short', year: '2-digit', timeZone: 'UTC' })
    svgParts.push(`<line x1="${cx.toFixed(1)}" y1="${volBottom}" x2="${cx.toFixed(1)}" y2="${(volBottom + 4).toFixed(1)}" stroke="#484f58" stroke-width="1"/>`)
    svgParts.push(`<text x="${cx.toFixed(1)}" y="${axisY}" fill="#8b949e" font-size="10" text-anchor="middle">${label}</text>`)
  })

  svg.innerHTML = svgParts.join('')
  const last = valid[valid.length - 1]
  const first = valid[0]
  const pct = ((last.close - first.close) / first.close * 100).toFixed(2)
  chartMeta.value = `${first.date} → ${last.date} · close ${fmt(last.close)} · ${pct >= 0 ? '+' : ''}${pct}% (range) · ${relevantZones.length}/${zones.length} zona aktif (dekat harga saat ini)`
}

async function loadChart() {
  if (!instrument.value) return
  const [rows, zones, sigs] = await Promise.all([
    get('/api/asset_ohlcv', { instrument: instrument.value, limit: chartVisible.value + CHART_PADDING }),
    get('/api/sr_zones', { instrument: instrument.value }),
    get('/api/signals', { instrument: instrument.value }),
  ])
  signals.value = sigs
  await nextTick()
  drawCandleChart(rows, zones, sigs, chartVisible.value)
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
