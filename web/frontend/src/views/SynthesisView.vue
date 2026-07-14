<script setup>
import { ref, onMounted, watch } from 'vue'
import { get, post } from '../lib/api'
import { today, fmt } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Port dari web/static/js/panel6.js (lihat docs/migrationFE.md Fase 2).
const { toast } = useAppToast()

// ---------- Synthesis Harian + Outlook ----------
const synthDate = ref(today())
const synthText = ref('')
const outlookInstruments = ref([])
const outlookStance = ref({})

async function loadSynthesisForDate() {
  const date = synthDate.value || today()
  const [s, outlook] = await Promise.all([
    get('/api/synthesis', { date }), get('/api/outlook', { date }),
  ])
  synthText.value = s.text || ''
  const stance = {}
  outlookInstruments.value.forEach((inst) => { stance[inst] = outlook[inst] || 'Neutral' })
  outlookStance.value = stance
}

onMounted(async () => {
  outlookInstruments.value = await get('/api/outlook_instruments')
  await loadSynthesisForDate()
})
watch(synthDate, loadSynthesisForDate)

async function saveOutlook(inst) {
  await post('/api/outlook/save', { date: synthDate.value || today(), instrument: inst, stance: outlookStance.value[inst] })
  toast(`Outlook ${inst}: ${outlookStance.value[inst]}`)
}

async function saveSynthesis() {
  if (!synthText.value.trim()) { toast('Isi synthesis dulu'); return }
  await post('/api/synthesis/save', { date: synthDate.value || today(), text: synthText.value })
  toast('Synthesis tersimpan')
}

// ---------- Trading Journal ----------
const j = ref({
  instrument: 'BTC', setup: '', outcome: 'ONGOING', entry: '', sl: '', tp1: '',
  plannedSize: '', actualSize: '', skipReason: '', notes: '', lesson: '',
})
const sizingResult = ref('')

async function calcSizing() {
  if (!j.value.instrument.trim() || !j.value.entry || !j.value.sl) {
    toast('Instrument, Entry, SL wajib diisi dulu'); return
  }
  const result = await get('/api/sizing/suggest', { instrument: j.value.instrument, entry: j.value.entry, sl: j.value.sl })
  if (result.error) { sizingResult.value = result.error; return }
  if (result.skip) {
    sizingResult.value = `SKIP — ${result.skip_reason} (budget ${fmt(result.risk_budget)} tidak cukup utk 1 lot)`
    j.value.skipReason = result.skip_reason
    j.value.plannedSize = ''
  } else {
    const bufferNote = result.risk_per_unit !== result.nominal_risk_per_unit
      ? ` [buffer ARA/ARB 1.5x diterapkan: jarak nominal ${fmt(result.nominal_risk_per_unit)} → ${fmt(result.risk_per_unit)}]`
      : ''
    sizingResult.value = `Suggested: ${result.suggested_units} unit (risiko aktual ${fmt(result.actual_risk)} / budget ${fmt(result.risk_budget)})${bufferNote}`
    j.value.plannedSize = result.suggested_units
    j.value.skipReason = ''
  }
}

async function saveJournal() {
  await post('/api/journal/add', {
    date: today(), instrument: j.value.instrument, setup_type: j.value.setup,
    entry_price: j.value.entry || null, sl_price: j.value.sl || null, tp1_price: j.value.tp1 || null,
    outcome: j.value.outcome, personal_notes: j.value.notes, lesson_learned: j.value.lesson,
    planned_size: j.value.plannedSize || null, actual_size: j.value.actualSize || null,
    skip_reason: j.value.skipReason || null,
  })
  toast('Tersimpan ke trading journal')
  j.value = { instrument: j.value.instrument, setup: '', outcome: j.value.outcome, entry: '', sl: '', tp1: '', plannedSize: '', actualSize: '', skipReason: '', notes: '', lesson: '' }
  sizingResult.value = ''
}

// ---------- Prediction Log ----------
const p = ref({ horizon: '1w', confidence: '', targetDate: '', claim: '', basis: '' })
const duePredictions = ref([])

async function loadDuePredictions() {
  duePredictions.value = await get('/api/prediction/due')
}
onMounted(loadDuePredictions)

async function savePrediction() {
  if (!p.value.claim.trim() || !p.value.targetDate) { toast('Claim & target date wajib diisi'); return }
  await post('/api/prediction/add', {
    date_made: today(), horizon: p.value.horizon, claim: p.value.claim,
    confidence: p.value.confidence || null, basis: p.value.basis, target_date: p.value.targetDate,
  })
  toast('Prediksi tercatat')
  p.value = { horizon: p.value.horizon, confidence: '', targetDate: '', claim: '', basis: '' }
  loadDuePredictions()
}

async function scorePrediction(row, outcome) {
  await post('/api/prediction/score', { id: row.id, outcome })
  toast('Prediksi di-skor: ' + outcome)
  loadDuePredictions()
}

// ---------- Daily Briefing -> Telegram ----------
const briefingPreview = ref('')
async function sendBriefing() {
  const r = await post('/api/briefing/send', { date: today() })
  briefingPreview.value = r.text
  toast(r.sent ? 'Briefing terkirim ke Telegram' : 'Gagal kirim — cek TELEGRAM_BOT_TOKEN/CHAT_ID di .env')
}
</script>

<template>
  <section>
    <h2>Synthesis Harian</h2>
    <div class="panel">
      <div class="chart-head" style="margin-bottom:12px">
        <label class="src">Tanggal</label>
        <input v-model="synthDate" type="date">
        <span class="src">ganti tanggal untuk lihat/edit synthesis &amp; outlook hari lain</span>
      </div>
      <div class="form-row">
        <label class="field">Kesimpulan hari ini (tulis ulang sendiri, bukan auto-generate)</label>
        <textarea v-model="synthText" style="min-height:120px"></textarea>
      </div>
      <div class="form-row">
        <button class="btn" @click="saveSynthesis">Simpan Synthesis</button>
      </div>
    </div>
  </section>

  <section>
    <h2>Outlook per Instrumen</h2>
    <div class="panel">
      <div class="grid cards">
        <div v-for="inst in outlookInstruments" :key="inst" class="card">
          <div class="label">{{ inst }}</div>
          <select v-model="outlookStance[inst]" style="margin-top:6px" @change="saveOutlook(inst)">
            <option>Neutral</option><option>Bullish</option><option>Bearish</option>
          </select>
        </div>
      </div>
    </div>
  </section>

  <section>
    <h2>Trading Journal — Catat Trade</h2>
    <div class="panel">
      <div class="form-grid">
        <div><label class="field">Instrument</label><input v-model="j.instrument" type="text"></div>
        <div><label class="field">Setup type</label><input v-model="j.setup" type="text" placeholder="breakout/retest"></div>
        <div>
          <label class="field">Outcome</label>
          <select v-model="j.outcome"><option>ONGOING</option><option>WIN</option><option>LOSS</option></select>
        </div>
      </div>
      <div class="form-grid" style="margin-top:12px">
        <div><label class="field">Entry</label><input v-model="j.entry" type="number" step="any"></div>
        <div><label class="field">SL</label><input v-model="j.sl" type="number" step="any"></div>
        <div><label class="field">TP1</label><input v-model="j.tp1" type="number" step="any"></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn small secondary" @click="calcSizing">Hitung Ukuran (sizing engine, khusus universe Phase J+)</button>
        <span class="src">{{ sizingResult }}</span>
      </div>
      <div class="form-grid" style="margin-top:12px">
        <div><label class="field">Planned Size</label><input v-model="j.plannedSize" type="number" step="any" placeholder="dari sizing engine, atau isi manual"></div>
        <div><label class="field">Actual Size</label><input v-model="j.actualSize" type="number" step="any" placeholder="yang beneran dieksekusi"></div>
        <div><label class="field">Skip Reason</label><input v-model="j.skipReason" type="text" placeholder="mis. RISK_CAPACITY_EXCEEDED"></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <label class="field">Catatan pribadi</label>
        <textarea v-model="j.notes"></textarea>
      </div>
      <div class="form-row">
        <label class="field">Lesson learned (opsional)</label>
        <textarea v-model="j.lesson"></textarea>
      </div>
      <div class="form-row"><button class="btn" @click="saveJournal">Simpan ke Trading Journal</button></div>
    </div>
  </section>

  <section>
    <h2>Prediction Log — Catat Prediksi Baru</h2>
    <div class="panel">
      <div class="form-grid">
        <div>
          <label class="field">Horizon</label>
          <select v-model="p.horizon"><option>1w</option><option>2w</option><option>1m</option></select>
        </div>
        <div><label class="field">Confidence (%)</label><input v-model="p.confidence" type="number" min="0" max="100"></div>
        <div><label class="field">Target date (jatuh tempo)</label><input v-model="p.targetDate" type="date"></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <label class="field">Claim</label>
        <input v-model="p.claim" type="text" placeholder="mis. BTC tembus $70K sebelum FOMC">
      </div>
      <div class="form-row">
        <label class="field">Basis (data/lensa apa yang dipakai)</label>
        <textarea v-model="p.basis"></textarea>
      </div>
      <div class="form-row"><button class="btn" @click="savePrediction">Catat Prediksi</button></div>
    </div>
  </section>

  <section>
    <h2>Skor Prediksi — Jatuh Tempo</h2>
    <div class="panel">
      <table>
        <thead><tr><th>Dibuat</th><th>Target</th><th>Claim</th><th>Confidence</th><th>Skor</th></tr></thead>
        <tbody>
          <tr v-for="r in duePredictions" :key="r.id">
            <td class="src">{{ r.date_made }}</td><td class="src">{{ r.target_date }}</td>
            <td>{{ r.claim }}</td><td>{{ r.confidence ?? '-' }}%</td>
            <td>
              <button class="btn small secondary" @click="scorePrediction(r, 'BENAR')">Benar</button>
              <button class="btn small danger" @click="scorePrediction(r, 'SALAH')">Salah</button>
              <button class="btn small secondary" @click="scorePrediction(r, 'PARTIAL')">Partial</button>
            </td>
          </tr>
          <tr v-if="!duePredictions.length"><td colspan="5" class="src">tidak ada prediksi jatuh tempo</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Daily Briefing — Kirim ke Telegram</h2>
    <div class="panel">
      <div class="form-row"><button class="btn" @click="sendBriefing">Kirim ke Telegram</button></div>
      <pre v-if="briefingPreview" class="src" style="white-space:pre-wrap;margin-top:12px">{{ briefingPreview }}</pre>
    </div>
    <div class="src" style="margin-top:6px">Jalankan setelah Panel 4-6 terisi (4 lensa + signal approved) — bukan otomatis. Butuh TELEGRAM_BOT_TOKEN &amp; TELEGRAM_CHAT_ID di .env (lihat README §Setup).</div>
  </section>
</template>
