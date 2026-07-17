<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { get, post } from '../lib/api'
import { fmt } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Port dari web/static/js/panel1.js (lihat docs/migrationFE.md Fase 2).
const { toast } = useAppToast()

// ---------- Snapshot cards ----------
const data = ref(null)
const period = ref('day')
const asOf = ref('memuat…')

const byCategory = computed(() => {
  if (!data.value?.snapshot) return []
  const map = new Map()
  for (const s of data.value.snapshot) {
    if (!map.has(s.category)) map.set(s.category, [])
    map.get(s.category).push(s)
  }
  return [...map.entries()]
})

function cardValue(s) {
  let val = fmt(s.value)
  if (s.column === 'fear_greed_value' && data.value.fear_greed_label && val !== null) {
    val = val + ' · ' + data.value.fear_greed_label
  }
  return val
}

function cardDelta(s) {
  const comp = s.compare && s.compare[period.value]
  if (!comp) return { cls: 'na', text: 'n/a' }
  const arrow = comp.delta > 0 ? '▲' : comp.delta < 0 ? '▼' : '–'
  const cls = comp.delta > 0 ? 'up' : comp.delta < 0 ? 'down' : 'flat'
  const deltaStr = fmt(Math.abs(comp.delta))
  const pctStr = comp.pct !== null && comp.pct !== undefined
    ? ` (${comp.pct >= 0 ? '+' : '-'}${Math.abs(comp.pct).toFixed(2)}%)` : ''
  return { cls, text: `${arrow} ${comp.delta >= 0 ? '+' : '-'}${deltaStr}${pctStr}` }
}

const sortedFlags = computed(() => {
  if (!data.value?.source_flags) return []
  // 'stale' = fetch sukses tapi observasi lebih tua dari batas wajar
  // (scrapers/macro_fred.py) -- ranking di antara skip & ok, biar kelihatan
  // tapi tidak sepanik 'fail'.
  const order = { fail: 0, skip: 1, stale: 2, ok: 3 }
  return Object.entries(data.value.source_flags)
    .sort((a, b) => (order[a[1]] - order[b[1]]) || a[0].localeCompare(b[0]))
})

async function loadLatest() {
  const d = await get('/api/latest')
  if (d.empty) { asOf.value = 'kosong'; data.value = null; return }
  asOf.value = `per ${d.date} · ${d.news_today} berita hari itu`
  data.value = d
}
onMounted(loadLatest)

// ---------- Manual Backfill (1 instrument) ----------
const MACRO_INSTRUMENTS = ['BTC', 'SP500', 'IHSG', 'GOLD', 'USDIDR', 'USDJPY', 'DXY', 'US10Y', 'VIX', 'WALCL', 'RRP', 'TGA', 'HY']
const bfInstrument = ref('BTC')
const bfFrom = ref('')
const bfTo = ref('')
const bfGapInfo = ref('Memuat info data...')
const bfResult = ref('')
const bfPreviewData = ref(null)
const bfShowCommit = ref(false)

async function loadDataGaps() {
  bfGapInfo.value = 'Memuat info data...'
  const g = await get('/api/data_gaps', { instrument: bfInstrument.value })
  if (!g.total_rows) { bfGapInfo.value = 'Belum ada data untuk instrument ini.'; return }
  const range = `${g.total_rows.toLocaleString('id-ID')} baris · ${g.date_from} s.d. ${g.date_to}`
  if (g.calendar === 'WEEKLY_WED') {
    bfGapInfo.value = `${range} (rilis mingguan tiap Rabu — jeda antar-Rabu wajar, bukan gap)`
    return
  }
  if (g.gaps_total_count === 0) {
    bfGapInfo.value = `${range} · tidak ada gap terdeteksi`
    return
  }
  const shown = g.gaps.slice(0, 5).map((gap) => `${gap.from} s.d. ${gap.to} (${gap.days} hari)`).join(', ')
  const more = g.gaps_total_count > 5 ? ` · +${g.gaps_total_count - 5} gap lain` : ''
  bfGapInfo.value = `${range} · ${g.gaps_total_count} gap terdeteksi: ${shown}${more}`
}
onMounted(loadDataGaps)
watch(bfInstrument, loadDataGaps)

async function bfPreview() {
  if (!bfFrom.value || !bfTo.value) { toast('Isi rentang tanggal dulu'); return }
  const body = { instrument: bfInstrument.value, from: bfFrom.value, to: bfTo.value }
  const r = await post('/api/backfill/preview', body)
  bfPreviewData.value = body
  bfResult.value = `Fetched ${r.fetched}, baru ${r.new}, duplikat ${r.dup}` + (r.sample_from ? ` (contoh ${r.sample_from} .. ${r.sample_to})` : '')
  bfShowCommit.value = r.new > 0
}
async function bfCommit() {
  if (!bfPreviewData.value) return
  const r = await post('/api/backfill/commit', bfPreviewData.value)
  bfResult.value = `OK — ${r.new} baris baru ditulis (${r.dup} duplikat di-skip).`
  bfShowCommit.value = false
  toast('Backfill selesai')
}

// ---------- Backfill semua instrument sekaligus ----------
const bfAllChecking = ref(false)
const bfAllResults = ref(null)
const bfAllDone = ref('')

async function bfAllPreview() {
  bfAllChecking.value = true
  bfAllResults.value = null
  bfAllDone.value = ''
  const { results } = await post('/api/backfill/all/preview', {})
  bfAllChecking.value = false
  bfAllResults.value = results
}

async function bfAllCommit() {
  const items = bfAllResults.value.filter((x) => !x.error).map((x) => ({ instrument: x.instrument, from: x.from, to: x.to }))
  const cr = await post('/api/backfill/all/commit', { items })
  const totalNew = cr.results.reduce((s, x) => s + (x.new || 0), 0)
  bfAllDone.value = `Selesai — ${totalNew} baris baru ditulis di ${cr.results.length} instrument.`
  toast(`Backfill semua selesai — ${totalNew} baris baru`)
  bfAllResults.value = null
  loadDataGaps()
}
</script>

<template>
  <section>
    <h2>Snapshot Pasar</h2>
    <div class="chart-head" style="margin-bottom:12px">
      <label class="src">Bandingkan vs</label>
      <select v-model="period" style="width:auto">
        <option value="day">Hari</option>
        <option value="week">Minggu</option>
        <option value="month">Bulan</option>
        <option value="year">Tahun</option>
      </select>
    </div>
    <p v-if="!data" class="src">{{ asOf }}</p>
    <div v-else id="cards">
      <div v-for="[cat, items] in byCategory" :key="cat" class="cat-group">
        <h4 class="cat-title">{{ cat }}</h4>
        <div class="grid cards">
          <div v-for="s in items" :key="s.column" class="card">
            <div class="label">{{ s.label }}</div>
            <div class="value" :class="{ na: cardValue(s) === null }">{{ cardValue(s) === null ? 'n/a' : cardValue(s) }}</div>
            <div class="delta" :class="cardDelta(s).cls">{{ cardDelta(s).text }}</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section>
    <details class="collapsible">
      <summary>Status Sumber Data (source_flags)</summary>
      <div class="panel">
        <div class="flags">
          <span v-for="[k, v] in sortedFlags" :key="k" class="flag"><span class="dot" :class="v"></span>{{ k }}</span>
          <span v-if="!sortedFlags.length" class="src">tidak ada flag</span>
        </div>
      </div>
    </details>
  </section>

  <section>
    <h2>Manual Backfill</h2>
    <div class="panel">
      <div class="form-grid">
        <div>
          <label class="field">Instrument</label>
          <select v-model="bfInstrument">
            <option v-for="i in MACRO_INSTRUMENTS" :key="i">{{ i }}</option>
          </select>
        </div>
        <div><label class="field">Dari tanggal</label><input v-model="bfFrom" type="date"></div>
        <div><label class="field">Sampai tanggal</label><input v-model="bfTo" type="date"></div>
      </div>
      <div class="src" style="margin-top:8px">{{ bfGapInfo }}</div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn secondary" @click="bfPreview">Preview</button>
        <button v-if="bfShowCommit" class="btn" @click="bfCommit">Confirm &amp; Commit</button>
      </div>
      <div class="src">{{ bfResult }}</div>

      <hr style="margin:16px 0;border-color:var(--border)">
      <p class="src">Sistem sudah tahu gap tiap instrument (lihat info di atas
        tiap kali ganti dropdown) — tombol ini cek SEMUA instrument sekaligus
        dan langsung fetch range gap-nya masing-masing, tanpa perlu pilih satu
        per satu.</p>
      <div class="form-row">
        <button class="btn secondary" @click="bfAllPreview">Cek &amp; Preview Semua Gap</button>
      </div>
      <div style="margin-top:8px">
        <p v-if="bfAllChecking" class="src">Mengecek semua instrument (bisa beberapa detik)...</p>
        <p v-if="bfAllDone" class="src">{{ bfAllDone }}</p>
        <template v-if="bfAllResults">
          <p v-if="!bfAllResults.length" class="src">Tidak ada gap dgn data baru ditemukan di semua instrument.</p>
          <template v-else>
            <table style="margin-top:8px">
              <thead><tr><th>Instrument</th><th>Range Gap</th><th>Baru</th><th>Duplikat</th></tr></thead>
              <tbody>
                <tr v-for="x in bfAllResults" :key="x.instrument">
                  <td>{{ x.instrument }}</td>
                  <td v-if="x.error" colspan="3" style="color:var(--fail)">Error: {{ x.error }}</td>
                  <template v-else>
                    <td class="src">{{ x.from }} s.d. {{ x.to }}</td>
                    <td>{{ x.new }}</td>
                    <td class="src">{{ x.dup }}</td>
                  </template>
                </tr>
              </tbody>
            </table>
            <div class="form-row" style="margin-top:8px">
              <button class="btn" @click="bfAllCommit">Commit Semua ({{ bfAllResults.filter(x => !x.error).length }} instrument)</button>
            </div>
          </template>
        </template>
      </div>
    </div>
  </section>
</template>
