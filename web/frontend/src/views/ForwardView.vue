<script setup>
import { ref, computed, onMounted } from 'vue'
import Column from 'primevue/column'
import DataTable from '../components/DataTable.vue'
import { get, post } from '../lib/api'
import { fmt, today } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'
import { preserveScroll } from '../composables/useScrollPreserve'

// Port dari web/static/js/panel3.js (lihat docs/migrationFE.md Fase 2).
const { toast } = useAppToast()

// ---------- Economic Calendar ----------
const econCalRaw = ref([])
const editingActualIds = ref(new Set())
const actualInputs = ref({}) // id -> nilai sedang diketik, per baris (BUKAN 1 ref bersama -- banyak baris bisa butuh input bersamaan)
const loadingCal = ref(true)
// Default HIGH saja ("bintang 3") -- window backend HIGH+MED, tapi MED bikin
// tabel penuh event kurang krusial. Toggle ke HIGH+MED kalau perlu lihat semua.
const impFilter = ref('HIGH')

const econCal = computed(() => {
  const todayStr = today()
  const filtered = impFilter.value === 'HIGH'
    ? econCalRaw.value.filter((r) => r.importance === 'HIGH')
    : econCalRaw.value
  // Prioritaskan hari ini & mendatang (ascending) di ATAS -- event yang
  // sudah lewat (cuma nunggu actual diisi manual) ditaruh di bawah, biar
  // yang relevan SEKARANG langsung kelihatan tanpa pindah halaman dulu.
  return [...filtered].sort((a, b) => {
    const aPast = a.event_date < todayStr ? 1 : 0
    const bPast = b.event_date < todayStr ? 1 : 0
    if (aPast !== bPast) return aPast - bPast
    return a.event_date.localeCompare(b.event_date)
  })
})

// preserveScroll: saveActual() panggil ulang loadEconCalendar() stlh POST --
// tanpa ini, ganti econCalRaw.value bikin DataTable re-render & scroll
// lompat ke atas. Aman dibungkus di definisi (cuma dipanggil onMounted +
// saveActual, tidak ada filter watch yang manggil fungsi load ini).
const loadEconCalendar = preserveScroll(async function loadEconCalendar() {
  loadingCal.value = true
  econCalRaw.value = await get('/api/econ_calendar')
  loadingCal.value = false
})
onMounted(loadEconCalendar)

function countdown(eventDate) {
  const days = Math.ceil((new Date(eventDate) - new Date()) / 86400000)
  return days <= 0 ? 'hari ini/lewat' : `H-${days}`
}
function startEditActual(row) {
  editingActualIds.value.add(row.id)
  actualInputs.value[row.id] = ''
}
async function saveActual(row) {
  const actual = (actualInputs.value[row.id] || '').trim()
  if (!actual) { toast('Actual wajib diisi'); return }
  await post('/api/econ_calendar/actual', { id: row.id, actual })
  toast('Actual tersimpan')
  editingActualIds.value.delete(row.id)
  loadEconCalendar()
}

// ---------- Earnings Emiten (READ-ONLY, kontrak §19.5) ----------
// earnings_calendar di-surface di sini ("gabung visual dgn econ_calendar" =
// section berdampingan, bukan 1 tabel dipaksakan). Warning = penegak rule
// no-hold-through-earnings saham AS (keputusan #3).
const earningsRaw = ref([])
const earningsWarnings = ref([])
const loadingEarnings = ref(true)

const earnings = computed(() => {
  const todayStr = today()
  // Upcoming/hari-ini di atas, yang sudah lewat (nunggu actual EPS) di bawah --
  // pola sama econCal.
  return [...earningsRaw.value].sort((a, b) => {
    const aPast = a.earnings_date < todayStr ? 1 : 0
    const bPast = b.earnings_date < todayStr ? 1 : 0
    if (aPast !== bPast) return aPast - bPast
    return a.earnings_date.localeCompare(b.earnings_date)
  })
})

async function loadEarnings() {
  loadingEarnings.value = true
  ;[earningsRaw.value, earningsWarnings.value] = await Promise.all([
    get('/api/earnings'), get('/api/earnings/warnings'),
  ])
  loadingEarnings.value = false
}
onMounted(loadEarnings)

// Surprise = actual - forecast (beat hijau / miss merah). null actual -> '-'.
function surprise(row) {
  if (row.eps_actual === null || row.eps_actual === undefined || row.eps_forecast === null) return null
  const diff = row.eps_actual - row.eps_forecast
  return { diff, beat: diff >= 0 }
}

// ---------- Expectations (Layer B) ----------
const expectations = ref([])
const exp = ref({ date: '', metric: 'cme_fedwatch_cut_prob', value: '', horizon: '' })

const loadExpectations = preserveScroll(async function loadExpectations() {
  expectations.value = await get('/api/expectations', { limit: 15 })
})
onMounted(loadExpectations)

async function saveExpectation() {
  if (exp.value.value === '') { toast('Value wajib diisi'); return }
  await post('/api/expectations/add', {
    date: exp.value.date || today(), metric: exp.value.metric,
    value: Number(exp.value.value), horizon: exp.value.horizon || null, source: 'manual',
  })
  toast('Expectation tersimpan')
  exp.value.value = ''
  exp.value.horizon = ''
  loadExpectations()
}

// ---------- Positioning (Layer C) ----------
const positioning = ref([])
const loadingPos = ref(true)
const pos = ref({ date: '', instrument: 'SBN', metric: '', value: '' })

const loadPositioning = preserveScroll(async function loadPositioning() {
  loadingPos.value = true
  positioning.value = await get('/api/positioning', { limit: 200 })
  loadingPos.value = false
})
onMounted(loadPositioning)

async function savePositioning() {
  if (pos.value.value === '' || !pos.value.metric.trim()) { toast('Metric dan value wajib diisi'); return }
  await post('/api/positioning/add', {
    date: pos.value.date || today(), instrument: pos.value.instrument,
    metric: pos.value.metric, value: Number(pos.value.value), source: 'manual',
  })
  toast('Positioning tersimpan')
  pos.value.metric = ''
  pos.value.value = ''
  loadPositioning()
}

// ---------- Policy Tracker (Layer A) ----------
const policy = ref([])
const loadingPolicy = ref(true)
const pol = ref({
  date: '', speaker: '', institution: '', url: '', literal: '',
  stance: '', flag: 'TESTABLE', inference: '', drift: '',
})

const loadPolicyNotes = preserveScroll(async function loadPolicyNotes() {
  loadingPolicy.value = true
  policy.value = await get('/api/policy', { limit: 100 })
  loadingPolicy.value = false
})
onMounted(loadPolicyNotes)

async function savePolicyNote() {
  if (!pol.value.literal.trim()) { toast('Literal statement wajib diisi'); return }
  await post('/api/policy/add', {
    date: pol.value.date || today(), speaker: pol.value.speaker,
    institution: pol.value.institution, source_url: pol.value.url,
    literal_statement: pol.value.literal,
    stance_score: pol.value.stance !== '' ? Number(pol.value.stance) : null,
    inference: pol.value.inference, inference_flag: pol.value.flag,
    drift_note: pol.value.drift,
  })
  toast('Policy note tersimpan')
  pol.value = { date: pol.value.date, speaker: '', institution: '', url: '', literal: '', stance: '', flag: pol.value.flag, inference: '', drift: '' }
  loadPolicyNotes()
}

// ---------- Disonansi Flag ----------
const disonansi = ref(null)
onMounted(async () => { disonansi.value = await get('/api/disonansi') })
</script>

<template>
  <section>
    <h2>Economic Calendar</h2>
    <div class="panel">
      <div class="chart-head" style="margin-bottom:12px">
        <label class="src">Importance</label>
        <select v-model="impFilter" style="width:auto">
          <option value="HIGH">HIGH saja (bintang 3)</option>
          <option value="ALL">HIGH + MED</option>
        </select>
      </div>
      <p v-if="loadingCal" class="src">Memuat...</p>
      <DataTable
        v-else :rows="econCal" :dataKey="'id'"
        :searchFields="['event_name', 'country']" emptyMessage="tidak ada event mendatang"
      >
        <Column field="event_date" header="Tanggal" sortable />
        <Column header="Countdown"><template #body="{ data }"><span class="src">{{ countdown(data.event_date) }}</span></template></Column>
        <Column field="event_name" header="Event" sortable />
        <Column field="country" header="Negara" sortable><template #body="{ data }"><span class="src">{{ data.country || '-' }}</span></template></Column>
        <Column field="importance" header="Importance" sortable>
          <template #body="{ data }"><span class="badge" :class="data.importance">{{ data.importance }}</span></template>
        </Column>
        <Column header="Forecast"><template #body="{ data }"><span class="src">{{ data.forecast || '-' }}</span></template></Column>
        <Column header="Previous"><template #body="{ data }"><span class="src">{{ data.previous || '-' }}</span></template></Column>
        <Column header="Actual">
          <template #body="{ data }">
            <template v-if="data.actual && !editingActualIds.has(data.id)">
              {{ data.actual }} <button class="btn small secondary" @click="startEditActual(data)">Ubah</button>
            </template>
            <template v-else>
              <input
                :value="actualInputs[data.id] || ''" @input="actualInputs[data.id] = $event.target.value"
                type="text" placeholder="isi setelah rilis" style="width:80px;display:inline-block"
              >
              <button class="btn small secondary" @click="saveActual(data)">Simpan</button>
            </template>
          </template>
        </Column>
      </DataTable>
    </div>
  </section>

  <section>
    <h2>Earnings Emiten (Universe)</h2>
    <div class="panel">
      <div v-if="earningsWarnings.length" style="margin-bottom:12px">
        <div v-for="w in earningsWarnings" :key="w.instrument" class="empty-inline" style="margin-bottom:6px">
          <span class="badge" :class="w.hard_rule ? 'HIGH' : 'MED'">{{ w.hard_rule ? '⚠ TUTUP PENUH' : 'WASPADA' }}</span>
          <span style="margin-left:8px">
            <b>{{ w.instrument }}</b> earnings H-{{ w.days_until }} ({{ w.earnings_date }}) — posisi ONGOING.
            <template v-if="w.hard_rule">Saham AS: WAJIB tutup penuh sebelum tanggal earnings (kontrak §18 keputusan #3).</template>
            <template v-else>IDX tidak punya aturan tutup-penuh, tapi gap earnings tetap risiko — cek ulang premis posisi.</template>
          </span>
        </div>
      </div>
      <p v-if="loadingEarnings" class="src">Memuat...</p>
      <DataTable
        v-else :rows="earnings" :dataKey="'earnings_date'"
        :searchFields="['instrument']" emptyMessage="belum ada data earnings"
      >
        <Column field="earnings_date" header="Tanggal" sortable />
        <Column header="Countdown"><template #body="{ data }"><span class="src">{{ countdown(data.earnings_date) }}</span></template></Column>
        <Column field="instrument" header="Ticker" sortable />
        <Column field="market" header="Market" sortable><template #body="{ data }"><span class="src">{{ data.market || '-' }}</span></template></Column>
        <Column header="EPS Forecast"><template #body="{ data }"><span class="src">{{ data.eps_forecast ?? '-' }}</span></template></Column>
        <Column header="EPS Actual"><template #body="{ data }">{{ data.eps_actual ?? '—' }}</template></Column>
        <Column header="Surprise">
          <template #body="{ data }">
            <span v-if="surprise(data)" :style="{ color: surprise(data).beat ? 'var(--ok)' : 'var(--fail)' }">
              {{ surprise(data).beat ? '▲' : '▼' }} {{ (surprise(data).diff >= 0 ? '+' : '') + fmt(surprise(data).diff) }}
            </span>
            <span v-else class="src">—</span>
          </template>
        </Column>
        <Column field="event_type" header="Tipe" sortable><template #body="{ data }"><span class="src">{{ data.event_type }}</span></template></Column>
      </DataTable>
    </div>
    <div class="src" style="margin-top:6px">Data yfinance (J-7), diisi otomatis — bukan input manual. Earnings = event risk terjadwal (sama kelas dgn FOMC untuk AKELA). Posisi terbuka + earnings dekat → lihat warning di atas.</div>
  </section>

  <section>
    <h2>Expectations (Layer B)</h2>
    <div class="panel">
      <div class="form-grid">
        <div><label class="field">Tanggal</label><input v-model="exp.date" type="date"></div>
        <div>
          <label class="field">Metric</label>
          <select v-model="exp.metric">
            <option value="cme_fedwatch_cut_prob">CME FedWatch cut probability</option>
            <option value="dot_plot_median">Fed Dot Plot median</option>
          </select>
        </div>
        <div><label class="field">Value</label><input v-model="exp.value" type="number" step="any" placeholder="mis. 0.72"></div>
        <div><label class="field">Horizon</label><input v-model="exp.horizon" type="text" placeholder="mis. next_meeting / EOY2026"></div>
      </div>
      <div class="form-row" style="margin-top:4px">
        <button class="btn" @click="saveExpectation">+ Add Expectation</button>
      </div>
      <table style="margin-top:12px">
        <thead><tr><th>Tgl</th><th>Metric</th><th>Value</th><th>Horizon</th></tr></thead>
        <tbody>
          <tr v-for="(r, i) in expectations" :key="i">
            <td class="src">{{ r.date }}</td><td>{{ r.metric }}</td><td>{{ r.value }}</td><td class="src">{{ r.horizon || '-' }}</td>
          </tr>
          <tr v-if="!expectations.length"><td colspan="4" class="src">belum ada entri</td></tr>
        </tbody>
      </table>
    </div>
    <div class="src" style="margin-top:6px">Manual — CME FedWatch API resmi berbayar, Fed Dot Plot rilis PDF kuartalan (tidak ada sumber gratis yang scrape-able).</div>
  </section>

  <section>
    <h2>Positioning (Layer C)</h2>
    <div class="panel">
      <p v-if="loadingPos" class="src">Memuat...</p>
      <DataTable v-else :rows="positioning" :searchFields="['instrument', 'metric', 'source']" emptyMessage="belum ada data">
        <Column field="date" header="Tgl" sortable><template #body="{ data }"><span class="src">{{ data.date }}</span></template></Column>
        <Column field="instrument" header="Instrument" sortable />
        <Column field="metric" header="Metric" sortable />
        <Column field="value" header="Value" sortable><template #body="{ data }">{{ fmt(data.value) ?? data.value }}</template></Column>
        <Column field="source" header="Source" sortable><template #body="{ data }"><span class="src">{{ data.source || '-' }}</span></template></Column>
      </DataTable>
      <div class="form-grid" style="margin-top:12px">
        <div><label class="field">Tanggal</label><input v-model="pos.date" type="date"></div>
        <div>
          <label class="field">Instrument</label>
          <select v-model="pos.instrument">
            <option>SBN</option><option>BTC</option><option>DXY</option><option>GOLD</option><option>SP500</option>
          </select>
        </div>
        <div><label class="field">Metric</label><input v-model="pos.metric" type="text" placeholder="mis. sbn_foreign_flow / etf_net_flow"></div>
        <div><label class="field">Value</label><input v-model="pos.value" type="number" step="any"></div>
      </div>
      <div class="form-row" style="margin-top:4px">
        <button class="btn" @click="savePositioning">+ Add/Override Positioning</button>
      </div>
    </div>
    <div class="src" style="margin-top:6px">COT (CFTC) &amp; BTC ETF flow terisi otomatis tiap run_daily. Form ini utk SBN foreign flow (manual — sumber DJPPR tidak scrape-able) dan koreksi manual kalau perlu.</div>
  </section>

  <section>
    <h2>Policy Tracker (Layer A)</h2>
    <div class="panel">
      <div class="form-grid">
        <div><label class="field">Tanggal</label><input v-model="pol.date" type="date"></div>
        <div><label class="field">Speaker</label><input v-model="pol.speaker" type="text" placeholder="mis. Powell"></div>
        <div><label class="field">Institusi</label><input v-model="pol.institution" type="text" placeholder="mis. Fed"></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <label class="field">Literal statement (apa yang BENAR-BENAR dikatakan)</label>
        <textarea v-model="pol.literal"></textarea>
      </div>
      <div class="form-grid">
        <div>
          <label class="field">Stance score (-2 dovish .. +2 hawkish)</label>
          <input v-model="pol.stance" type="number" min="-2" max="2" step="1">
        </div>
        <div>
          <label class="field">Inference flag</label>
          <select v-model="pol.flag"><option>TESTABLE</option><option>SPEKULATIF</option></select>
        </div>
        <div><label class="field">Source URL (opsional)</label><input v-model="pol.url" type="url"></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <label class="field">Inference (pembacaan arah/intent — subjektif)</label>
        <textarea v-model="pol.inference"></textarea>
      </div>
      <div class="form-row">
        <label class="field">Drift note (opsional — berubah dari pernyataan sebelumnya?)</label>
        <textarea v-model="pol.drift"></textarea>
      </div>
      <div class="form-row" style="margin-top:4px">
        <button class="btn" @click="savePolicyNote">+ Add Policy Note</button>
      </div>
    </div>
  </section>

  <section>
    <h2>Entri Policy Tracker Terbaru</h2>
    <div class="panel">
      <p v-if="loadingPolicy" class="src">Memuat...</p>
      <DataTable v-else :rows="policy" :searchFields="['speaker', 'literal_statement', 'inference']" emptyMessage="belum ada entri">
        <Column field="date" header="Tgl" sortable><template #body="{ data }"><span class="src">{{ data.date }}</span></template></Column>
        <Column field="speaker" header="Speaker" sortable><template #body="{ data }">{{ data.speaker || '-' }}</template></Column>
        <Column header="Literal"><template #body="{ data }">{{ (data.literal_statement || '').slice(0, 80) }}</template></Column>
        <Column header="Inference"><template #body="{ data }">{{ (data.inference || '').slice(0, 80) }}</template></Column>
        <Column field="inference_flag" header="Flag" sortable>
          <template #body="{ data }"><span class="badge" :class="data.inference_flag === 'SPEKULATIF' ? 'MED' : 'LOW'">{{ data.inference_flag || '-' }}</span></template>
        </Column>
      </DataTable>
    </div>
  </section>

  <section>
    <h2>Disonansi Flag</h2>
    <div v-if="!disonansi" class="empty-inline">Memuat...</div>
    <div v-else-if="!disonansi.available" class="empty-inline">
      Belum cukup data untuk dibandingkan (butuh stance_score Policy Tracker + minimal 2 baris COT DXY).
    </div>
    <div v-else>
      <span class="badge" :class="disonansi.flagged ? 'HIGH' : 'LOW'">{{ disonansi.flagged ? 'DISONANSI' : 'SEARAH' }}</span>
      <span class="src" style="margin-left:8px">{{ disonansi.note }}</span>
    </div>
  </section>
</template>
