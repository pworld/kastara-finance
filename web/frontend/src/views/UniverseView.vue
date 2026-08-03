<script setup>
import { ref, onMounted } from 'vue'
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
// Langkah 2 (docs/universe_portfolio_restructure_v1.md, 3 Aug 2026): jadi
// DRAWER dibuka dari klik baris tabel Universe -- ticker terisi otomatis
// dari row yang diklik, tidak lagi diketik manual. Override TETAP nempel di
// section ini apa adanya (sudah begitu sebelum restrukturisasi) -- Validasi
// Lane & Rasio Bank masih section standalone terpisah, baru pindah ke
// drawer ini di Langkah 3.
const detailTicker = ref('')
const detail = ref(null)
const detailError = ref('')
const override = ref({ quadrant: 'INVESTABLE', reason: '' })
const detailDrawerOpen = ref(false)

function openDetailDrawer(row) {
  detailTicker.value = row.instrument
  detailDrawerOpen.value = true
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
const lane = ref({ ticker: '', newLane: 'TRADE', evidence: '' })
const laneLog = ref([])
const loadingLaneLog = ref(true)

async function loadLaneValidationLog() {
  loadingLaneLog.value = true
  laneLog.value = await get('/api/lane_validation_log')
  loadingLaneLog.value = false
}
onMounted(loadLaneValidationLog)

async function validateLane() {
  const ticker = lane.value.ticker.trim()
  const evidence = lane.value.evidence.trim()
  if (!ticker) { toast('Ticker wajib diisi'); return }
  if (!evidence) { toast('Evidence wajib diisi'); return }
  const result = await post(`/api/emiten/${encodeURIComponent(ticker)}/validate_lane`, {
    new_lane: lane.value.newLane, evidence,
  })
  if (result.error) { toast(result.error); return }
  toast(`${ticker}: lane ${result.old_lane || '-'} → ${result.new_lane}`)
  lane.value.evidence = ''
  loadUniverse()
  loadLaneValidationLog()
}

// ---------- Rasio Bank (Manual) ----------
const bank = ref({ ticker: '', quarterEnd: '', car: '', npl: '', nim: '', ldr: '' })
const bankRatios = ref(null)

async function saveBankRatios() {
  const instrument = bank.value.ticker.trim()
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
  const instrument = bank.value.ticker.trim()
  if (!instrument) { toast('Isi ticker dulu'); return }
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
      <p class="src" style="margin-top:8px">Klik baris utk buka detail + override (drawer). Validasi Lane &amp; Rasio Bank di bawah masih section standalone -- pindah ke drawer ini di Langkah 3.</p>
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
  </Drawer>

  <section>
    <h2>Validasi Lane (Bar-Replay Sign-off)</h2>
    <div class="panel">
      <p class="src">Kontrak §13.1 poin 5: "Engine teruji di BTC ≠ teruji di
        BBRI" — lane instrumen HANYA naik ke TRADE/BOTH setelah kamu
        benar-benar mereview chart historisnya sendiri (bar-replay manual, di
        luar dashboard ini, mis. Panel 5). Form ini CUMA MEREKAM keputusan
        itu — tidak ada validasi otomatis apa pun di baliknya.</p>
      <div class="form-grid">
        <div><label class="field">Ticker</label><input v-model="lane.ticker" type="text" placeholder="mis. BBCA"></div>
        <div>
          <label class="field">Lane Baru</label>
          <select v-model="lane.newLane">
            <option value="TRADE">TRADE</option><option value="BOTH">BOTH</option>
            <option value="INVEST">INVEST</option><option value="NONE">NONE</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <label class="field">Evidence (wajib) — apa yang dicek di bar-replay & kesimpulannya</label>
        <textarea v-model="lane.evidence" placeholder="mis. Cek 2 tahun candle historis BBCA di Panel 5, zona S&R konsisten dgn kalibrasi fraksi harga, pola breakout/retest valid, tidak ada gap tak wajar di luar ARA/ARB normal..."></textarea>
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="validateLane">Rekam Validasi Lane</button>
      </div>
    </div>
  </section>

  <section>
    <h2>Rasio Bank (Manual — Khusus Emiten Finansial)</h2>
    <div class="panel">
      <p class="src">CAR/NPL/NIM/LDR TIDAK tersedia di yfinance (dikonfirmasi
        saat riset G3) — isi manual dari laporan resmi bank (OJK/laporan
        tahunan). Tidak akan pernah tertimpa oleh backfill fundamental
        otomatis.</p>
      <div class="form-grid">
        <div><label class="field">Ticker</label><input v-model="bank.ticker" type="text" placeholder="mis. BBCA"></div>
        <div><label class="field">Kuartal (akhir periode)</label><input v-model="bank.quarterEnd" type="date"></div>
      </div>
      <div class="form-grid" style="margin-top:12px">
        <div><label class="field">CAR (%)</label><input v-model="bank.car" type="number" step="any"></div>
        <div><label class="field">NPL Gross (%)</label><input v-model="bank.npl" type="number" step="any"></div>
        <div><label class="field">NIM (%)</label><input v-model="bank.nim" type="number" step="any"></div>
        <div><label class="field">LDR (%)</label><input v-model="bank.ldr" type="number" step="any"></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="saveBankRatios">Simpan Rasio Bank</button>
        <button class="btn small secondary" @click="loadBankRatios">Lihat Riwayat Ticker Ini</button>
      </div>
      <table style="margin-top:12px">
        <thead><tr><th>Kuartal</th><th>CAR</th><th>NPL</th><th>NIM</th><th>LDR</th><th>Sumber</th></tr></thead>
        <tbody v-if="!bankRatios"><tr><td colspan="6" class="src">klik "Lihat Riwayat" utk tampilkan</td></tr></tbody>
        <tbody v-else>
          <tr v-for="r in bankRatios" :key="r.quarter_end">
            <td class="src">{{ r.quarter_end }}</td><td>{{ r.car ?? '-' }}</td><td>{{ r.npl_gross ?? '-' }}</td>
            <td>{{ r.nim ?? '-' }}</td><td>{{ r.ldr ?? '-' }}</td><td class="src">{{ r.source }}</td>
          </tr>
          <tr v-if="!bankRatios.length"><td colspan="6" class="src">belum ada rasio bank utk {{ bank.ticker }}</td></tr>
        </tbody>
      </table>
    </div>
  </section>
  </template>

  <template v-if="activeTab === 'portfolio'">
  <section>
    <h2>Portofolio / Holdings</h2>
    <div class="panel">
      <p class="src">Belum dibangun — komponen baru (docs/universe_portfolio_restructure_v1.md
        §4), menunggu Langkah 4-6: tabel `holdings` universal (saham/emas/
        kripto/reksadana/valas satu tabel), form input minimal, view Per
        Provider/Per Book/Alokasi vs SOP/Per Mata Uang, + guard (book wajib,
        konversi TRADE↔INVEST terkunci, indikator basi, flag TRADE tanpa
        `linked_journal_id`). Tab ini disiapkan lebih dulu supaya navigasi
        sudah siap begitu komponennya jadi.</p>
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
