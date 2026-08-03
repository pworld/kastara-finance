<script setup>
import { ref, computed, onMounted } from 'vue'
import Column from 'primevue/column'
import Drawer from 'primevue/drawer'
import DataTable from '../components/DataTable.vue'
import { get, post } from '../lib/api'
import { fmt, LANE_CLASS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Port dari web/static/js/panel8.js (lihat docs/migrationFE.md Fase 2).
const { toast } = useAppToast()

// ---------- Restrukturisasi 4 tab (docs/universe_portfolio_restructure_v1.md
// Langkah 1, Agustus 2026) -- pengelompokan MURNI berdasarkan frekuensi
// pakai (harian/sesekali/kuartalan), TIDAK ADA isi section yang diubah di
// langkah ini. Ticker-scoped (Detail Emiten/Override, Validasi Lane, Rasio
// Bank) SEMENTARA tetap section biasa di tab Universe -- pindah ke drawer
// per-baris tabel itu Langkah 2/3, belum di sini. ----------
const activeTab = ref('universe')
const TABS = [
  { id: 'universe', label: 'Universe' },
  { id: 'portfolio', label: 'Portofolio' },
  { id: 'intake', label: 'Intake' },
  { id: 'log', label: 'Log & Audit' },
]

// ---------- Universe table ----------
const universe = ref([])
const loadingUniverse = ref(true)
async function loadUniverse() {
  loadingUniverse.value = true
  universe.value = await get('/api/universe')
  loadingUniverse.value = false
}
onMounted(loadUniverse)

function flagCount(row) {
  if (!row.integrity_flags) return 0
  try { return (JSON.parse(row.integrity_flags) || []).length } catch { return 0 }
}

// ---------- + Intake Kandidat (Gelombang 1) ----------
const intake = ref({
  ticker: '', market: 'IDX', sector: '', mcap: '', freeFloat: '', lotSize: '',
  lane: 'INVEST', financial: false, dailyLimit: false,
})

async function saveIntake() {
  const instrument = intake.value.ticker.trim()
  if (!instrument) { toast('Ticker wajib diisi'); return }
  const result = await post('/api/intake', {
    instrument, market: intake.value.market, sector: intake.value.sector || null,
    market_cap: intake.value.mcap ? Number(intake.value.mcap) : null,
    free_float: intake.value.freeFloat ? Number(intake.value.freeFloat) : null,
    lot_size: intake.value.lotSize ? Number(intake.value.lotSize) : null,
    lane: intake.value.lane, is_financial: intake.value.financial, has_daily_limit: intake.value.dailyLimit,
  })
  if (result.error) { toast(result.error); return }
  toast(`${instrument} tersimpan (lane ${result.lane})`)
  intake.value = { ticker: '', market: intake.value.market, sector: '', mcap: '', freeFloat: '', lotSize: '', lane: intake.value.lane, financial: false, dailyLimit: false }
  loadUniverse()
}

// ---------- Uji Kelayakan Kandidat (Gelombang 2) ----------
const uji = ref({ ticker: '', decision: 'UNIVERSE', reason: '' })
const ujiResult = ref('')
let lastGradeSnapshot = null

async function ujiIntegritas() {
  const instrument = uji.value.ticker.trim()
  if (!instrument) { toast('Ticker wajib diisi'); return }
  const result = await get('/api/intake/integrity_check', { instrument })
  const flagText = result.uma_active
    ? `<span class="badge lane-none" style="border-color:var(--high);color:var(--high)">UMA_ACTIVE</span>`
    : `<span class="badge LOW">bersih (tidak ada UMA baru-baru ini)</span>`
  ujiResult.value = `Cek Integritas ${instrument}: ${flagText} (${result.uma_history.length} riwayat UMA ditemukan di laman)`
}

async function ujiGrade() {
  const instrument = uji.value.ticker.trim()
  if (!instrument) { toast('Ticker wajib diisi'); return }
  const result = await post('/api/intake/grade', { instrument })
  if (result.error) { toast(result.error); return }
  lastGradeSnapshot = result
  ujiResult.value = `Grade ${instrument}: score=${result.fund_score}, kuadran=<b>${result.quadrant}</b>, flags=${JSON.stringify(result.integrity_flags)}`
  toast(`Grade ${instrument}: ${result.quadrant}`)
  loadUniverse()
}

async function ujiCatatKeputusan() {
  const instrument = uji.value.ticker.trim()
  const reason = uji.value.reason.trim()
  if (!instrument) { toast('Ticker wajib diisi'); return }
  if (!reason) { toast('Alasan wajib diisi'); return }
  const result = await post('/api/intake/decision', {
    instrument, decision: uji.value.decision, reason, grade_snapshot: lastGradeSnapshot,
  })
  if (result.error) { toast(result.error); return }
  toast(`Keputusan ${instrument} tercatat`)
  uji.value.reason = ''
  loadIntakeLog()
}

// ---------- Detail Emiten (Komponen B) + Override ----------
// Langkah 2+3 (docs/universe_portfolio_restructure_v1.md, 3 Aug 2026): jadi
// SATU DRAWER dibuka dari klik baris tabel Universe -- ticker terisi
// otomatis dari row yang diklik, tidak lagi diketik manual di mana pun.
// Drawer ini sekarang berisi: Ringkasan+Fundamental+Override (Langkah 2),
// Validasi Lane + Rasio Bank (Langkah 3, section standalone lama dihapus).
const detailTicker = ref('')
const detail = ref(null)
const detailError = ref('')
const override = ref({ quadrant: 'INVESTABLE', reason: '' })
const detailDrawerOpen = ref(false)

function openDetailDrawer(row) {
  detailTicker.value = row.instrument
  detailDrawerOpen.value = true
  bankRatios.value = null
  lane.value.evidence = ''
  loadDetail()
}

async function loadDetail() {
  const ticker = detailTicker.value.trim()
  if (!ticker) { toast('Ticker wajib diisi'); return }
  const result = await get(`/api/emiten/${encodeURIComponent(ticker)}`)
  if (result.error) { detailError.value = result.error; detail.value = null; return }
  detailError.value = ''
  detail.value = result
}

function fundamentalsHeader() {
  return detail.value?.metadata?.is_financial
    ? ['Kuartal', 'Net Income', 'CAR', 'NPL', 'NIM', 'LDR', 'Confidence']
    : ['Kuartal', 'Revenue', 'Net Income', 'OCF', 'FCF', 'Confidence']
}

async function saveOverride() {
  const ticker = detailTicker.value.trim()
  const reason = override.value.reason.trim()
  if (!ticker) { toast('Ticker tidak diketahui -- buka drawer dari tabel Universe dulu'); return }
  if (!reason) { toast('Alasan wajib diisi'); return }
  const result = await post(`/api/emiten/${encodeURIComponent(ticker)}/override`, {
    quadrant: override.value.quadrant, reason,
  })
  if (result.error) { toast(result.error); return }
  toast(`Override ${ticker} tersimpan`)
  override.value.reason = ''
  loadDetail()
  loadUniverse()
}

// ---------- Validasi Lane (Bar-Replay Sign-off) ----------
// Langkah 3 (docs/universe_portfolio_restructure_v1.md, 3 Aug 2026): pindah
// ke drawer yang sama dgn Detail Emiten -- ticker dari detailTicker (drawer),
// bukan field sendiri lagi.
const lane = ref({ newLane: 'TRADE', evidence: '' })
const laneLog = ref([])
const loadingLaneLog = ref(true)

async function loadLaneValidationLog() {
  loadingLaneLog.value = true
  laneLog.value = await get('/api/lane_validation_log')
  loadingLaneLog.value = false
}
onMounted(loadLaneValidationLog)

async function validateLane() {
  const ticker = detailTicker.value.trim()
  const evidence = lane.value.evidence.trim()
  if (!ticker) { toast('Ticker tidak diketahui -- buka drawer dari tabel Universe dulu'); return }
  if (!evidence) { toast('Evidence wajib diisi'); return }
  const result = await post(`/api/emiten/${encodeURIComponent(ticker)}/validate_lane`, {
    new_lane: lane.value.newLane, evidence,
  })
  if (result.error) { toast(result.error); return }
  toast(`${ticker}: lane ${result.old_lane || '-'} → ${result.new_lane}`)
  lane.value.evidence = ''
  loadUniverse()
  loadLaneValidationLog()
  loadDetail()
}

// ---------- Rasio Bank (Manual) ----------
// Langkah 3: sama seperti Validasi Lane, ticker dari detailTicker (drawer).
// Section ini cuma tampil di drawer kalau detail.metadata.is_financial
// (docs §3: "Rasio Bank -> form + riwayat (if bank)").
const bank = ref({ quarterEnd: '', car: '', npl: '', nim: '', ldr: '' })
const bankRatios = ref(null)

async function saveBankRatios() {
  const instrument = detailTicker.value.trim()
  if (!instrument || !bank.value.quarterEnd) { toast('Ticker & kuartal wajib diisi'); return }
  const num = (v) => (v === '' ? null : Number(v))
  await post('/api/fundamentals/bank_ratios', {
    instrument, quarter_end: bank.value.quarterEnd,
    car: num(bank.value.car), npl_gross: num(bank.value.npl), nim: num(bank.value.nim), ldr: num(bank.value.ldr),
  })
  toast(`Rasio bank ${instrument} ${bank.value.quarterEnd} tersimpan`)
  bank.value.car = ''; bank.value.npl = ''; bank.value.nim = ''; bank.value.ldr = ''
  loadBankRatios()
}

async function loadBankRatios() {
  const instrument = detailTicker.value.trim()
  if (!instrument) { toast('Ticker tidak diketahui -- buka drawer dari tabel Universe dulu'); return }
  bankRatios.value = await get('/api/fundamentals/bank_ratios', { instrument })
}

// ---------- Riwayat Keputusan Intake ----------
const intakeLog = ref([])
const loadingIntakeLog = ref(true)
async function loadIntakeLog() {
  loadingIntakeLog.value = true
  intakeLog.value = await get('/api/intake/log')
  loadingIntakeLog.value = false
}
onMounted(loadIntakeLog)

function decisionSeverity(d) {
  if (d === 'TOLAK') return 'HIGH'
  if (d === 'WATCHLIST') return 'MED'
  return 'LOW'
}

// ---------- Grader Log & Kalibrasi (Komponen D) ----------
const graderLog = ref([])
const loadingGraderLog = ref(true)
async function loadGraderLog() {
  loadingGraderLog.value = true
  graderLog.value = await get('/api/grader_log')
  loadingGraderLog.value = false
}
onMounted(loadGraderLog)

async function saveOutcome(row, field, value) {
  if (!value) return
  await post(`/api/grader_log/${row.id}/outcome`, { [field]: value })
  toast('Outcome tersimpan')
  loadGraderLog()
}

// ---------- Portofolio / Holdings (docs/universe_portfolio_restructure_v1.md
// §4, Langkah 4, 3 Aug 2026) -- form input minimal + view Per Provider.
// Langkah 5 (3 Aug 2026): Alokasi vs SOP + Per Mata Uang. `sopCategory` di
// form ini EKSPLISIT dipilih Giel (bukan ditebak dari instrument/currency --
// keputusan sadar, lihat ROADMAP) krn itu satu-satunya cara akurat 100%
// tanpa logic tebak-tebakan yang rawan salah utk kasus tak terduga. ----------
const SOP_CATEGORY_LABELS = {
  SAHAM_IHSG: 'Saham IHSG', EMAS: 'Emas', CRYPTO: 'Crypto',
  VALAS: 'Valas', GLOBAL_EQ: 'Global Eq', KAS_IDR: 'Kas IDR (idle)',
}
const holdings = ref([])
const loadingHoldings = ref(true)
const holdingForm = ref({
  instrument: '', provider: '', book: 'INVEST', quantity: '', unit: '',
  avgPrice: '', currency: 'IDR', openedAt: '', notes: '', sopCategory: 'SAHAM_IHSG',
})

async function loadHoldings() {
  loadingHoldings.value = true
  holdings.value = await get('/api/holdings')
  loadingHoldings.value = false
}
onMounted(loadHoldings)

async function saveHolding() {
  const result = await post('/api/holdings', {
    instrument: holdingForm.value.instrument, provider: holdingForm.value.provider,
    book: holdingForm.value.book, quantity: holdingForm.value.quantity ? Number(holdingForm.value.quantity) : null,
    unit: holdingForm.value.unit, avg_price: holdingForm.value.avgPrice ? Number(holdingForm.value.avgPrice) : null,
    currency: holdingForm.value.currency, opened_at: holdingForm.value.openedAt || null,
    notes: holdingForm.value.notes || null, sop_category: holdingForm.value.sopCategory,
  })
  if (result.error) { toast(result.error); return }
  toast(`${result.instrument} @ ${result.provider} tersimpan`)
  holdingForm.value = {
    instrument: '', provider: '', book: holdingForm.value.book, quantity: '', unit: '',
    avgPrice: '', currency: holdingForm.value.currency, openedAt: '', notes: '',
    sopCategory: holdingForm.value.sopCategory,
  }
  loadHoldings()
  loadAllocation()
}

// ---------- Alokasi vs SOP + Per Mata Uang (view, butuh Langkah 4 dulu) ----------
const allocation = ref(null)
const loadingAllocation = ref(true)
async function loadAllocation() {
  loadingAllocation.value = true
  allocation.value = await get('/api/portfolio/allocation')
  loadingAllocation.value = false
}
onMounted(loadAllocation)

const holdingsByProvider = computed(() => {
  const map = new Map()
  for (const h of holdings.value) {
    if (!map.has(h.provider)) map.set(h.provider, [])
    map.get(h.provider).push(h)
  }
  return [...map.entries()]
})

// ---------- Langkah 6: indikator basi + flag TRADE-tanpa-jurnal (computed,
// murni dari field yang sudah dikembalikan list_holdings -- tidak perlu
// endpoint baru) + drawer Konversi Book (satu-satunya jalur ubah book). ----------
const STALE_HOLDING_DAYS = 30
function isStale(h) {
  if (!h.last_updated) return false
  const days = (Date.now() - new Date(h.last_updated).getTime()) / 86400000
  return days > STALE_HOLDING_DAYS
}
function isTradeWithoutJournal(h) {
  return h.book === 'TRADE' && !h.linked_journal_id
}

const convertDrawerOpen = ref(false)
const convertTarget = ref(null)
const convertForm = ref({ newBook: 'INVEST', reason: '' })
function openConvertDrawer(h) {
  convertTarget.value = h
  convertForm.value = { newBook: h.book === 'TRADE' ? 'INVEST' : 'TRADE', reason: '' }
  convertDrawerOpen.value = true
}
async function submitConvertBook() {
  const result = await post(`/api/holdings/${convertTarget.value.id}/convert_book`, {
    new_book: convertForm.value.newBook, reason: convertForm.value.reason,
  })
  if (result.error) { toast(result.error); return }
  toast(`${result.instrument}: ${result.from_book} → ${result.to_book} (${result.pnl_check})`)
  convertDrawerOpen.value = false
  loadHoldings()
  loadAllocation()
  loadHoldingConversions()
}

// ---------- Riwayat Konversi Book (Log & Audit tab) ----------
const holdingConversions = ref([])
const loadingHoldingConversions = ref(true)
async function loadHoldingConversions() {
  loadingHoldingConversions.value = true
  holdingConversions.value = await get('/api/holdings/conversions')
  loadingHoldingConversions.value = false
}
onMounted(loadHoldingConversions)
</script>

<template>
  <div class="tab-bar">
    <button
      v-for="t in TABS" :key="t.id" class="tab-btn" :class="{ active: activeTab === t.id }"
      @click="activeTab = t.id"
    >{{ t.label }}</button>
  </div>

  <template v-if="activeTab === 'universe'">
  <section>
    <h2>Universe — Saham Individual</h2>
    <div class="panel">
      <p v-if="loadingUniverse" class="src">Memuat...</p>
      <DataTable
        v-else :rows="universe" :dataKey="'instrument'"
        :searchFields="['instrument', 'sector', 'market']"
        emptyMessage="belum ada instrumen di universe"
        class="clickable-rows"
        @row-click="openDetailDrawer($event.data)"
      >
        <Column field="instrument" header="Ticker" sortable />
        <Column field="sector" header="Sektor" sortable><template #body="{ data }"><span class="src">{{ data.sector || '-' }}</span></template></Column>
        <Column field="market" header="Market" sortable><template #body="{ data }"><span class="src">{{ data.market || '-' }}</span></template></Column>
        <Column field="lane" header="Lane" sortable>
          <template #body="{ data }"><span class="badge" :class="LANE_CLASS[data.lane] || 'lane-none'">{{ data.lane || '-' }}</span></template>
        </Column>
        <Column header="Divalidasi"><template #body="{ data }"><span class="src">{{ data.lane_validated_at || '-' }}</span></template></Column>
        <Column field="quadrant" header="Kuadran" sortable><template #body="{ data }"><span class="src">{{ data.quadrant || 'belum digrade' }}</span></template></Column>
        <Column field="fund_score" header="Score" sortable><template #body="{ data }"><span class="src">{{ data.fund_score ?? '-' }}</span></template></Column>
        <Column header="Flags"><template #body="{ data }"><span class="src">{{ flagCount(data) }}</span></template></Column>
      </DataTable>
      <p class="src" style="margin-top:8px">Klik baris utk buka detail, override, validasi lane &amp; rasio bank (drawer) -- ticker tidak perlu diketik manual di mana pun lagi.</p>
    </div>
  </section>

  <Drawer v-model:visible="detailDrawerOpen" position="right" style="width:32rem; max-width:92vw" :header="detailTicker || 'Detail Emiten'">
    <p v-if="detailError" class="src">{{ detailError }}</p>
    <template v-else-if="detail">
      <p>
        <b>{{ detail.metadata.instrument }}</b> — {{ detail.metadata.sector || '-' }} · {{ detail.metadata.market }} ·
        lane <span class="badge" :class="LANE_CLASS[detail.metadata.lane] || 'lane-none'">{{ detail.metadata.lane }}</span>
      </p>
      <template v-if="detail.grade">
        <p class="src">
          Grade terakhir ({{ detail.grade.graded_at }}): score={{ detail.grade.fund_score }}, kuadran mesin=<b>{{ detail.grade.quadrant }}</b>
          <span v-if="detail.grade.giel_override" class="badge MED">Override Giel: {{ detail.grade.giel_override.quadrant }} — {{ detail.grade.giel_override.reason }}</span>
        </p>
        <p class="src">Flags: {{ detail.grade.integrity_flags.length ? detail.grade.integrity_flags.join(', ') : 'tidak ada' }}</p>
      </template>
      <p v-else class="src">Belum pernah digrade — jalankan "Uji Kelayakan" di tab Intake dulu.</p>
      <div style="overflow-x:auto">
      <table style="margin-top:8px">
        <thead><tr><th v-for="h in fundamentalsHeader()" :key="h">{{ h }}</th></tr></thead>
        <tbody>
          <tr v-for="f in detail.fundamentals" :key="f.quarter_end">
            <td class="src">{{ f.quarter_end }}</td>
            <template v-if="detail.metadata.is_financial">
              <td>{{ fmt(f.net_income) ?? '-' }}</td><td>{{ f.car ?? '-' }}</td><td>{{ f.npl_gross ?? '-' }}</td><td>{{ f.nim ?? '-' }}</td><td>{{ f.ldr ?? '-' }}</td>
            </template>
            <template v-else>
              <td>{{ fmt(f.revenue) ?? '-' }}</td><td>{{ fmt(f.net_income) ?? '-' }}</td><td>{{ fmt(f.operating_cash_flow) ?? '-' }}</td><td>{{ fmt(f.free_cash_flow) ?? '-' }}</td>
            </template>
            <td class="src">{{ f.confidence }}</td>
          </tr>
          <tr v-if="!detail.fundamentals.length"><td colspan="7" class="src">belum ada fundamentals</td></tr>
        </tbody>
      </table>
      </div>
    </template>
    <div class="form-grid" style="margin-top:16px">
      <div>
        <label class="field">Override Kuadran</label>
        <select v-model="override.quadrant">
          <option value="INVESTABLE">INVESTABLE</option><option value="WATCH">WATCH</option>
          <option value="SPECULATIVE">SPECULATIVE</option><option value="AVOID">AVOID</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <label class="field">Alasan Override (wajib)</label>
      <textarea v-model="override.reason" placeholder="Kenapa kamu tidak setuju dgn kuadran mesin?"></textarea>
    </div>
    <div class="form-row" style="margin-top:8px">
      <button class="btn small secondary" @click="saveOverride">Simpan Override</button>
    </div>

    <hr style="margin:20px 0;border-color:var(--border)">

    <h4 style="margin:0 0 8px">Validasi Lane (Bar-Replay Sign-off)</h4>
    <p class="src">Kontrak §13.1 poin 5: "Engine teruji di BTC ≠ teruji di
      BBRI" — lane instrumen HANYA naik ke TRADE/BOTH setelah kamu
      benar-benar mereview chart historisnya sendiri (bar-replay manual, di
      luar dashboard ini, mis. Panel 5). Form ini CUMA MEREKAM keputusan
      itu — tidak ada validasi otomatis apa pun di baliknya.</p>
    <div class="form-row">
      <label class="field">Lane Baru</label>
      <select v-model="lane.newLane">
        <option value="TRADE">TRADE</option><option value="BOTH">BOTH</option>
        <option value="INVEST">INVEST</option><option value="NONE">NONE</option>
      </select>
    </div>
    <div class="form-row">
      <label class="field">Evidence (wajib) — apa yang dicek di bar-replay & kesimpulannya</label>
      <textarea v-model="lane.evidence" placeholder="mis. Cek 2 tahun candle historis BBCA di Panel 5, zona S&R konsisten dgn kalibrasi fraksi harga, pola breakout/retest valid, tidak ada gap tak wajar di luar ARA/ARB normal..."></textarea>
    </div>
    <div class="form-row" style="margin-top:8px">
      <button class="btn small secondary" @click="validateLane">Rekam Validasi Lane</button>
    </div>

    <template v-if="detail?.metadata?.is_financial">
      <hr style="margin:20px 0;border-color:var(--border)">

      <h4 style="margin:0 0 8px">Rasio Bank (Manual — Khusus Emiten Finansial)</h4>
      <p class="src">CAR/NPL/NIM/LDR TIDAK tersedia di yfinance (dikonfirmasi
        saat riset G3) — isi manual dari laporan resmi bank (OJK/laporan
        tahunan). Tidak akan pernah tertimpa oleh backfill fundamental
        otomatis.</p>
      <div class="form-row">
        <label class="field">Kuartal (akhir periode)</label>
        <input v-model="bank.quarterEnd" type="date">
      </div>
      <div class="form-grid">
        <div><label class="field">CAR (%)</label><input v-model="bank.car" type="number" step="any"></div>
        <div><label class="field">NPL Gross (%)</label><input v-model="bank.npl" type="number" step="any"></div>
        <div><label class="field">NIM (%)</label><input v-model="bank.nim" type="number" step="any"></div>
        <div><label class="field">LDR (%)</label><input v-model="bank.ldr" type="number" step="any"></div>
      </div>
      <div class="form-row" style="margin-top:8px">
        <button class="btn small secondary" @click="saveBankRatios">Simpan Rasio Bank</button>
        <button class="btn small secondary" @click="loadBankRatios">Lihat Riwayat Ticker Ini</button>
      </div>
      <div style="overflow-x:auto">
      <table style="margin-top:12px">
        <thead><tr><th>Kuartal</th><th>CAR</th><th>NPL</th><th>NIM</th><th>LDR</th><th>Sumber</th></tr></thead>
        <tbody v-if="!bankRatios"><tr><td colspan="6" class="src">klik "Lihat Riwayat" utk tampilkan</td></tr></tbody>
        <tbody v-else>
          <tr v-for="r in bankRatios" :key="r.quarter_end">
            <td class="src">{{ r.quarter_end }}</td><td>{{ r.car ?? '-' }}</td><td>{{ r.npl_gross ?? '-' }}</td>
            <td>{{ r.nim ?? '-' }}</td><td>{{ r.ldr ?? '-' }}</td><td class="src">{{ r.source }}</td>
          </tr>
          <tr v-if="!bankRatios.length"><td colspan="6" class="src">belum ada rasio bank utk {{ detailTicker }}</td></tr>
        </tbody>
      </table>
      </div>
    </template>
  </Drawer>
  </template>

  <template v-if="activeTab === 'portfolio'">
  <section>
    <h2>+ Holding Baru</h2>
    <div class="panel">
      <p class="src">Manual entry — tidak ada API broker (kontrak §15).
        Book adalah paspor uang: TRADE atau INVEST, wajib diisi.</p>
      <div class="form-grid">
        <div><label class="field">Instrument</label><input v-model="holdingForm.instrument" type="text" placeholder="mis. BBCA / BTC / XAU"></div>
        <div><label class="field">Provider</label><input v-model="holdingForm.provider" type="text" placeholder="mis. Stockbit / IBKR / Cold Wallet"></div>
        <div>
          <label class="field">Book</label>
          <select v-model="holdingForm.book"><option value="TRADE">TRADE</option><option value="INVEST">INVEST</option></select>
        </div>
      </div>
      <div class="form-grid">
        <div><label class="field">Quantity</label><input v-model="holdingForm.quantity" type="number" step="any"></div>
        <div><label class="field">Unit</label><input v-model="holdingForm.unit" type="text" placeholder="lot / share / gram / coin / nominal"></div>
        <div><label class="field">Avg Price (opsional)</label><input v-model="holdingForm.avgPrice" type="number" step="any"></div>
      </div>
      <div class="form-grid">
        <div>
          <label class="field">Currency</label>
          <select v-model="holdingForm.currency"><option value="IDR">IDR</option><option value="USD">USD</option><option value="SGD">SGD</option></select>
        </div>
        <div>
          <label class="field">Kategori SOP</label>
          <select v-model="holdingForm.sopCategory">
            <option v-for="(label, code) in SOP_CATEGORY_LABELS" :key="code" :value="code">{{ label }}</option>
          </select>
        </div>
        <div><label class="field">Opened At (opsional)</label><input v-model="holdingForm.openedAt" type="date"></div>
      </div>
      <div class="form-row">
        <label class="field">Notes (opsional)</label>
        <input v-model="holdingForm.notes" type="text">
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="saveHolding">Simpan Holding</button>
      </div>
    </div>
  </section>

  <section>
    <h2>Per Provider</h2>
    <div class="panel">
      <p class="src">🟡 baris = basi (&gt;30 hari sejak last_updated, alokasi dari data ini tidak bisa dipercaya).
        🔴 baris = TRADE tanpa jurnal (pelanggaran SOP -- lihat trading_journal).</p>
      <p v-if="loadingHoldings" class="src">Memuat...</p>
      <p v-else-if="!holdings.length" class="src">belum ada holding tercatat</p>
      <div v-else v-for="[provider, items] in holdingsByProvider" :key="provider" class="cat-group">
        <h4 class="cat-title">{{ provider }}</h4>
        <table>
          <thead><tr><th>Instrument</th><th>Book</th><th>Kategori SOP</th><th>Quantity</th><th>Avg Price</th><th>Currency</th><th>Notes</th><th></th></tr></thead>
          <tbody>
            <tr
              v-for="h in items" :key="h.id"
              :style="isTradeWithoutJournal(h) ? { background: 'rgba(220,80,80,.12)' } : isStale(h) ? { background: 'rgba(220,190,60,.12)' } : {}"
            >
              <td>{{ h.instrument }} <span v-if="isStale(h)" title="basi, >30 hari">🟡</span><span v-if="isTradeWithoutJournal(h)" title="TRADE tanpa jurnal">🔴</span></td>
              <td><span class="badge" :class="LANE_CLASS[h.book] || 'lane-none'">{{ h.book }}</span></td>
              <td class="src">{{ h.sop_category ? SOP_CATEGORY_LABELS[h.sop_category] : '—' }}</td>
              <td>{{ h.quantity }} {{ h.unit }}</td>
              <td class="src">{{ h.avg_price ?? '-' }}</td>
              <td class="src">{{ h.currency }}</td>
              <td class="src">{{ h.notes || '-' }}</td>
              <td><button class="btn small secondary" @click="openConvertDrawer(h)">Konversi Book</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <Drawer v-model:visible="convertDrawerOpen" position="right" style="width:28rem; max-width:92vw" :header="convertTarget ? `Konversi Book -- ${convertTarget.instrument}` : 'Konversi Book'">
    <p v-if="convertTarget" class="src">{{ convertTarget.instrument }} @ {{ convertTarget.provider }} -- saat ini
      <span class="badge" :class="LANE_CLASS[convertTarget.book] || 'lane-none'">{{ convertTarget.book }}</span></p>
    <p class="src">Diblokir otomatis kalau posisi ini SEDANG RUGI (dicek ke
      histori harga -- kalau instrumen tidak terlacak di sana, tidak bisa
      diverifikasi, tetap diizinkan). Konversi TETAP tercatat permanen di
      log, apa pun hasilnya.</p>
    <div class="form-row">
      <label class="field">Book Baru</label>
      <select v-model="convertForm.newBook">
        <option value="TRADE">TRADE</option>
        <option value="INVEST">INVEST</option>
      </select>
    </div>
    <div class="form-row">
      <label class="field">Alasan (wajib)</label>
      <textarea v-model="convertForm.reason" placeholder="Kenapa holding ini pindah book?"></textarea>
    </div>
    <div class="form-row" style="margin-top:12px">
      <button class="btn" @click="submitConvertBook">Konversi</button>
    </div>
  </Drawer>

  <section>
    <h2>Alokasi vs SOP</h2>
    <div class="panel">
      <p class="src">Target dari Investment SOP v4.1 (30/20/20/15/15, Kas IDR
        target 0% -- dry powder yang tidak ditempatkan sengaja diberi target
        0 biar langsung kelihatan sebagai penyimpangan, bukan kategori
        netral). Nilai dikonversi ke IDR-equivalent (USD pakai kurs
        usd_idr terbaru<span v-if="allocation?.usd_idr_rate"> · {{ allocation.usd_idr_rate }}</span>).</p>
      <p v-if="loadingAllocation" class="src">Memuat...</p>
      <template v-else-if="allocation">
        <table>
          <thead><tr><th>Kategori</th><th>Aktual</th><th>Target</th><th>Selisih</th></tr></thead>
          <tbody>
            <tr v-for="c in allocation.by_category" :key="c.category">
              <td>{{ SOP_CATEGORY_LABELS[c.category] }}</td>
              <td>{{ c.pct }}%</td>
              <td class="src">{{ c.target_pct }}%</td>
              <td :class="c.delta_pct > 0 ? 'up' : c.delta_pct < 0 ? 'down' : 'flat'">
                {{ c.delta_pct > 0 ? '▲' : c.delta_pct < 0 ? '▼' : '–' }} {{ c.delta_pct > 0 ? '+' : '' }}{{ c.delta_pct }}%
                <span v-if="c.category === 'KAS_IDR' && c.pct > 0">⚠ dry powder menganggur</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!allocation.total_idr" class="src" style="margin-top:8px">belum ada holding yang bisa dihitung nilainya (isi avg_price + kategori SOP dulu).</p>
        <details v-if="allocation.excluded.length" class="collapsible" style="margin-top:8px">
          <summary>{{ allocation.excluded.length }} holding dikecualikan dari hitungan</summary>
          <ul>
            <li v-for="(e, i) in allocation.excluded" :key="i" class="src">{{ e.instrument }} ({{ e.provider }}) -- {{ e.reason }}</li>
          </ul>
        </details>
      </template>
    </div>
  </section>

  <section>
    <h2>Per Mata Uang</h2>
    <div class="panel">
      <p v-if="loadingAllocation" class="src">Memuat...</p>
      <p v-else-if="!allocation?.by_currency?.length" class="src">belum ada holding yang bisa dihitung nilainya</p>
      <div v-else class="chart-head">
        <span v-for="c in allocation.by_currency" :key="c.currency" class="badge lane-none" style="margin-right:8px">
          {{ c.currency }} {{ c.pct }}%
        </span>
      </div>
    </div>
  </section>

  </template>

  <template v-if="activeTab === 'intake'">
  <section>
    <h2>+ Intake Kandidat (metadata)</h2>
    <div class="panel">
      <p class="src">Gelombang 1 — cuma metadata dasar. Lane dari jalur ini
        HANYA boleh INVEST/NONE (instrumen baru wajib divalidasi bar-replay
        dulu, kontrak §13.1). Fundamental, cek integritas, dan grade run
        menyusul di Gelombang 2.</p>
      <div class="form-grid">
        <div><label class="field">Ticker</label><input v-model="intake.ticker" type="text" placeholder="mis. BBRI"></div>
        <div>
          <label class="field">Market</label>
          <select v-model="intake.market"><option value="IDX">IDX</option><option value="US">US</option></select>
        </div>
        <div><label class="field">Sektor</label><input v-model="intake.sector" type="text" placeholder="mis. Financial Services"></div>
      </div>
      <div class="form-grid">
        <div><label class="field">Market Cap</label><input v-model="intake.mcap" type="number"></div>
        <div><label class="field">Free Float (%)</label><input v-model="intake.freeFloat" type="number"></div>
        <div><label class="field">Lot Size</label><input v-model="intake.lotSize" type="number" placeholder="IDX=100, US=1"></div>
      </div>
      <div class="form-grid">
        <div>
          <label class="field">Lane</label>
          <select v-model="intake.lane"><option value="INVEST">INVEST</option><option value="NONE">NONE</option></select>
        </div>
        <div style="align-self:end"><label class="field"><input v-model="intake.financial" type="checkbox"> Emiten finansial (bank/dll)</label></div>
        <div style="align-self:end"><label class="field"><input v-model="intake.dailyLimit" type="checkbox"> Ada batas harian (ARA/ARB)</label></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="saveIntake">Simpan Kandidat</button>
      </div>
    </div>
  </section>

  <section>
    <h2>Uji Kelayakan Kandidat (Gelombang 2)</h2>
    <div class="panel">
      <p class="src">Rubrik SAMA dengan universe existing — tidak ada jalur
        istimewa. Ticker harus sudah tersimpan (Gelombang 1 di atas, atau
        sudah ada di Universe) sebelum diuji di sini.</p>
      <div class="form-grid">
        <div><label class="field">Ticker</label><input v-model="uji.ticker" type="text" placeholder="mis. BBRI"></div>
        <div style="align-self:end"><button class="btn secondary" @click="ujiIntegritas">1. Cek Integritas (UMA)</button></div>
        <div style="align-self:end"><button class="btn secondary" @click="ujiGrade">2. Jalankan Grade</button></div>
      </div>
      <div class="src" style="margin-top:8px" v-html="ujiResult"></div>

      <div class="form-row" style="margin-top:16px">
        <label class="field">3. Keputusan</label>
        <select v-model="uji.decision">
          <option value="UNIVERSE">Masuk Universe</option>
          <option value="WATCHLIST">Watchlist</option>
          <option value="TOLAK">Tolak</option>
        </select>
      </div>
      <div class="form-row">
        <label class="field">Alasan (wajib)</label>
        <textarea v-model="uji.reason" placeholder="Kenapa keputusan ini diambil?"></textarea>
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="ujiCatatKeputusan">Catat Keputusan</button>
      </div>
    </div>
  </section>

  <section>
    <h2>Riwayat Keputusan Intake</h2>
    <div class="panel">
      <p v-if="loadingIntakeLog" class="src">Memuat...</p>
      <DataTable v-else :rows="intakeLog" :searchFields="['instrument', 'decision', 'reason']" emptyMessage="belum ada keputusan intake">
        <Column field="decided_at" header="Tanggal" sortable><template #body="{ data }"><span class="src">{{ data.decided_at }}</span></template></Column>
        <Column field="instrument" header="Ticker" sortable />
        <Column field="decision" header="Keputusan" sortable>
          <template #body="{ data }"><span class="badge" :class="decisionSeverity(data.decision)">{{ data.decision }}</span></template>
        </Column>
        <Column field="reason" header="Alasan" />
      </DataTable>
    </div>
  </section>
  </template>

  <template v-if="activeTab === 'log'">
  <section>
    <h2>Riwayat Validasi Lane</h2>
    <div class="panel">
      <p v-if="loadingLaneLog" class="src">Memuat...</p>
      <DataTable v-else :rows="laneLog" :searchFields="['instrument', 'evidence']" emptyMessage="belum ada validasi lane">
        <Column field="validated_at" header="Tanggal" sortable><template #body="{ data }"><span class="src">{{ data.validated_at }}</span></template></Column>
        <Column field="instrument" header="Ticker" sortable />
        <Column header="Lane Lama → Baru">
          <template #body="{ data }">
            <span class="src">{{ data.old_lane || '-' }} → </span>
            <span class="badge" :class="LANE_CLASS[data.new_lane] || 'lane-none'">{{ data.new_lane }}</span>
          </template>
        </Column>
        <Column field="evidence" header="Evidence" />
      </DataTable>
    </div>
  </section>

  <section>
    <h2>Riwayat Konversi Book</h2>
    <div class="panel">
      <p class="src">Satu-satunya jalur ubah book (TRADE↔INVEST) -- alasan
        wajib, dan `pnl_check` catat apakah posisi terverifikasi untung
        atau tidak bisa diverifikasi saat konversi terjadi (§4.4).</p>
      <p v-if="loadingHoldingConversions" class="src">Memuat...</p>
      <DataTable v-else :rows="holdingConversions" :searchFields="['instrument', 'reason']" emptyMessage="belum ada konversi book">
        <Column field="converted_at" header="Tanggal" sortable><template #body="{ data }"><span class="src">{{ data.converted_at }}</span></template></Column>
        <Column field="instrument" header="Ticker" sortable />
        <Column header="Book Lama → Baru">
          <template #body="{ data }">
            <span class="src">{{ data.from_book }} → </span>
            <span class="badge" :class="LANE_CLASS[data.to_book] || 'lane-none'">{{ data.to_book }}</span>
          </template>
        </Column>
        <Column field="reason" header="Alasan" />
        <Column field="pnl_check" header="P&amp;L saat konversi"><template #body="{ data }"><span class="src">{{ data.pnl_check }}</span></template></Column>
      </DataTable>
    </div>
  </section>

  <section>
    <h2>Grader Log &amp; Kalibrasi (Komponen D)</h2>
    <div class="panel">
      <p class="src">Revisi bobot rubrik grader HANYA lewat log ini (bukan
        per kasus) — widget "Nilai Outcome" utk grade yang sudah berumur
        3/6 bulan, pola sama Skor Prediksi Panel 6.</p>
      <p v-if="loadingGraderLog" class="src">Memuat...</p>
      <DataTable v-else :rows="graderLog" :searchFields="['instrument', 'reason']" emptyMessage="belum ada grader log">
        <Column field="date" header="Tanggal" sortable><template #body="{ data }"><span class="src">{{ data.date }}</span></template></Column>
        <Column field="instrument" header="Ticker" sortable />
        <Column header="Grade Lama → Baru"><template #body="{ data }"><span class="src">{{ data.old_grade || '-' }} → {{ data.new_grade }}</span></template></Column>
        <Column field="reason" header="Alasan"><template #body="{ data }">{{ data.reason || '-' }}</template></Column>
        <Column header="Outcome 3bln">
          <template #body="{ data }">
            <span v-if="data.outcome_3m">{{ data.outcome_3m }}</span>
            <select v-else @change="saveOutcome(data, 'outcome_3m', $event.target.value)">
              <option value="">-</option><option value="BENAR">BENAR</option><option value="SALAH">SALAH</option><option value="PARTIAL">PARTIAL</option>
            </select>
          </template>
        </Column>
        <Column header="Outcome 6bln">
          <template #body="{ data }">
            <span v-if="data.outcome_6m">{{ data.outcome_6m }}</span>
            <select v-else @change="saveOutcome(data, 'outcome_6m', $event.target.value)">
              <option value="">-</option><option value="BENAR">BENAR</option><option value="SALAH">SALAH</option><option value="PARTIAL">PARTIAL</option>
            </select>
          </template>
        </Column>
      </DataTable>
    </div>
  </section>
  </template>
</template>

<style scoped>
.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}
.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.tab-btn:hover {
  color: var(--text);
}
.tab-btn.active {
  color: var(--text);
  border-bottom-color: var(--accent);
}
.clickable-rows :deep(tbody tr) {
  cursor: pointer;
}
</style>
