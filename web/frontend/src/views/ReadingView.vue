<script setup>
import { ref, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import { get, post } from '../lib/api'
import { today, LENS_LABELS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Port dari web/static/js/panel4.js (lihat docs/migrationFE.md Fase 2).
const { toast } = useAppToast()

// ---------- Berita Key Hari Ini ----------
const keyNews = ref([])
onMounted(async () => {
  keyNews.value = await get('/api/news', { date: today(), key_only: 1, limit: 50 })
})

// ---------- 4 Analisa (AI) ----------
const PERSONA_ORDER = ['GEMA', 'LEON', 'AKELA', 'RIVAN']
const personaStatus = ref({})
const personaTexts = ref({})
const runningLens = ref(null)
const modalOpen = ref(false)
const modalLens = ref(null)

async function loadPersonaAnalysis() {
  const [status, rows] = await Promise.all([
    get('/api/persona/status'), get('/api/reading', { date: today() }),
  ])
  personaStatus.value = status
  const texts = {}
  rows.forEach((r) => { if (PERSONA_ORDER.includes(r.lens)) texts[r.lens] = r.notes })
  personaTexts.value = texts
}
onMounted(loadPersonaAnalysis)

function preview(lens) {
  const text = personaTexts.value[lens]
  if (!text) return 'Belum ada analisa.'
  return text.slice(0, 140) + (text.length > 140 ? '…' : '')
}

function openPersonaModal(lens) {
  modalLens.value = lens
  modalOpen.value = true
}

async function runPersona(lens) {
  runningLens.value = lens
  const r = await post('/api/persona/run', { lens })
  runningLens.value = null
  if (r.error) { toast(r.error); return }
  personaTexts.value = { ...personaTexts.value, [lens]: r.text }
  toast(`Analisa ${LENS_LABELS[lens]} selesai`)
  openPersonaModal(lens)
}

// ---------- Catatan Tambahan ----------
const externalAi = ref('')
const conflict = ref('')
async function saveReading() {
  const r = await post('/api/reading/save', { date: today(), external_ai: externalAi.value, conflict: conflict.value })
  toast(`${r.ids.length} catatan tersimpan`)
}
</script>

<template>
  <section>
    <h2>Berita Key Hari Ini</h2>
    <div class="panel">
      <div v-if="!keyNews.length" class="empty-inline">belum ada berita yang di-flag key hari ini — flag di Panel 2 (News) dulu.</div>
      <table v-else>
        <thead><tr><th>Impact</th><th>Headline</th><th>Sumber</th></tr></thead>
        <tbody>
          <tr v-for="r in keyNews" :key="r.id">
            <td><span class="badge" :class="r.impact_level">{{ r.impact_level }}</span></td>
            <td>
              <a v-if="r.raw_url" :href="r.raw_url" target="_blank" rel="noopener">{{ r.headline }}</a>
              <span v-else>{{ r.headline }}</span>
            </td>
            <td class="src">{{ r.source }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="src" style="margin-top:6px">Berita yang kamu flag "key" di Panel 2 — bahan buat nulis 4 lensa di bawah.</div>
  </section>

  <section>
    <h2>4 Analisa (AI)</h2>
    <div class="panel">
      <div class="grid persona-grid">
        <div
          v-for="lens in PERSONA_ORDER" :key="lens"
          class="card persona-card" :class="[lens, { 'missing-prompt': !personaStatus[lens] }]"
        >
          <div class="label">{{ LENS_LABELS[lens] || lens }}</div>
          <div class="persona-preview">{{ preview(lens) }}</div>
          <div v-if="!personaStatus[lens]" class="src" style="color:var(--fail)">
            Prompt belum diisi — tulis di prompts/persona_{{ lens.toLowerCase() }}.txt
          </div>
          <div class="form-row" style="margin-top:8px">
            <button
              class="btn small secondary" :disabled="runningLens === lens"
              @click="runPersona(lens)"
            >{{ runningLens === lens ? 'Menjalankan…' : 'Jalankan Analisa' }}</button>
            <button class="btn small" :disabled="!personaTexts[lens]" @click="openPersonaModal(lens)">Lihat Detail</button>
          </div>
        </div>
      </div>
    </div>
    <div class="src" style="margin-top:6px">Analisa digenerate lewat OpenRouter berdasarkan snapshot pasar + berita key hari ini. Klik "Jalankan Analisa" per kartu, lalu "Lihat Detail" utk baca hasilnya.</div>
  </section>

  <section>
    <h2>Catatan Tambahan</h2>
    <div class="panel">
      <div class="form-row">
        <label class="field">External AI Check (opsional — paste hasil banding TradingAgents/qrak/dll, MANUAL)</label>
        <textarea v-model="externalAi"></textarea>
      </div>
      <div class="form-row">
        <label class="field">Conflict Notes (poin yang belum sepakat antar analisa)</label>
        <textarea v-model="conflict"></textarea>
      </div>
      <div class="form-row" style="margin-top:4px">
        <button class="btn" @click="saveReading">Simpan Catatan</button>
      </div>
    </div>
  </section>

  <Dialog v-model:visible="modalOpen" modal :header="LENS_LABELS[modalLens] || modalLens" style="width:640px; max-width:90vw">
    <div style="white-space:pre-wrap; line-height:1.6; font-size:13px">{{ personaTexts[modalLens] || '' }}</div>
  </Dialog>
</template>
