<script setup>
import { ref, computed, onMounted } from 'vue'
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

// ---------- Trigger Berita (jalankan pipeline hari ini sekarang) ----------
// Terpisah dari Backfill di bawah: News tidak bisa diisi utk tanggal lampau
// (RSS cuma sajikan yang live), jadi ini trigger ke-1 (hari ini, sekarang),
// Backfill trigger ke-2 (rentang tanggal lampau, data market saja).
const newsRunning = ref(false)
const newsResult = ref('')
async function triggerNewsRun() {
  newsRunning.value = true
  newsResult.value = ''
  const r = await post('/api/run_daily_now', {})
  newsRunning.value = false
  if (r.error) { toast(`Gagal: ${r.error}`); newsResult.value = `Error: ${r.error}`; return }
  const deadStr = r.rss_dead && r.rss_dead.length ? `, feed mati: ${r.rss_dead.join(', ')}` : ''
  newsResult.value = `Selesai (${r.date}) — ${r.news_inserted} berita baru, ${r.asset_rows} baris market, RSS ${r.rss_ok} ok${deadStr}.`
  toast(`Trigger Berita selesai — ${r.news_inserted} berita baru`)
  loadLatest()
}

// ---------- Backfill semua instrument sekaligus ----------
const bfAllChecking = ref(false)
const bfAllResults = ref(null)
const bfAllDone = ref('')
const bfAllSelected = ref(new Set())

async function bfAllPreview() {
  bfAllChecking.value = true
  bfAllResults.value = null
  bfAllDone.value = ''
  const { results } = await post('/api/backfill/all/preview', {})
  bfAllChecking.value = false
  bfAllResults.value = results
  // Default: semua instrument tanpa error tercentang -- Giel tinggal
  // uncheck yang tidak mau di-commit, bukan mulai dari kosong.
  bfAllSelected.value = new Set(results.filter((x) => !x.error).map((x) => x.instrument))
}

function toggleBfAllSelected(instrument) {
  if (bfAllSelected.value.has(instrument)) bfAllSelected.value.delete(instrument)
  else bfAllSelected.value.add(instrument)
}

async function bfAllCommit() {
  const items = bfAllResults.value
    .filter((x) => !x.error && bfAllSelected.value.has(x.instrument))
    .map((x) => ({ instrument: x.instrument, from: x.from, to: x.to }))
  if (!items.length) { toast('Tidak ada instrument yang dicentang'); return }
  const cr = await post('/api/backfill/all/commit', { items })
  const totalNew = cr.results.reduce((s, x) => s + (x.new || 0), 0)
  bfAllDone.value = `Selesai — ${totalNew} baris baru ditulis di ${cr.results.length} instrument.`
  toast(`Backfill selesai — ${totalNew} baris baru`)
  bfAllResults.value = null
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
    <h2>Trigger Data</h2>
    <div class="panel">
      <p class="src">2 trigger terpisah, tujuan beda: <b>Berita</b> jalankan
        HARI INI sekarang (dipakai kalau cron WSL tidak jalan — berita tidak
        bisa diisi utk tanggal lampau, RSS cuma sajikan yang live).
        <b>Backfill</b> di bawah isi gap data MARKET utk rentang tanggal lampau.</p>
      <div class="form-row" style="margin-top:8px">
        <button class="btn" :disabled="newsRunning" @click="triggerNewsRun">
          {{ newsRunning ? 'Menjalankan...' : '▶ Trigger Berita (Sekarang)' }}
        </button>
      </div>
      <div v-if="newsResult" class="src" style="margin-top:6px">{{ newsResult }}</div>
    </div>
  </section>

  <section>
    <h2>Manual Backfill</h2>
    <div class="panel">
      <p class="src">Cek semua instrument sekaligus, sistem cari gap-nya
        masing-masing otomatis. Centang/uncentang baris utk pilih instrument
        mana yang mau di-commit.</p>
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
              <thead><tr><th></th><th>Instrument</th><th>Range Gap</th><th>Baru</th><th>Duplikat</th></tr></thead>
              <tbody>
                <tr v-for="x in bfAllResults" :key="x.instrument">
                  <td>
                    <input
                      v-if="!x.error" type="checkbox" :checked="bfAllSelected.has(x.instrument)"
                      @change="toggleBfAllSelected(x.instrument)"
                    >
                  </td>
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
              <button class="btn" @click="bfAllCommit">Commit Terpilih ({{ bfAllSelected.size }} instrument)</button>
            </div>
          </template>
        </template>
      </div>
    </div>
  </section>
</template>
