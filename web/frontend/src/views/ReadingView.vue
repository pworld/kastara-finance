<script setup>
import { ref, computed, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import TagAutocomplete from '../components/TagAutocomplete.vue'
import { get, post } from '../lib/api'
import { today, LENS_LABELS, FACET_COLOR } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Port dari web/static/js/panel4.js (lihat docs/migrationFE.md Fase 2).
const { toast } = useAppToast()

// ---------- Berita for_reading Hari Ini (Addendum C §21.2/21.6: rename
// fungsional dari "key news" -- kurasi "penting utk dibaca", beda dari tag
// klasifikasi) + filter by tag (§21.3, "filterable by tag") ----------
const readingNews = ref([])
onMounted(async () => {
  readingNews.value = await get('/api/news', { date: today(), for_reading: 1, limit: 50 })
})

const filterTags = ref([])
function addFilterTag(tag) {
  if (!filterTags.value.includes(tag.canonical)) filterTags.value.push(tag.canonical)
}
function removeFilterTag(canonical) {
  filterTags.value = filterTags.value.filter((c) => c !== canonical)
}
// Kosmetik AND semantics: berita harus punya SEMUA tag terpilih -- cukup utk
// Reading Page (kontrak cuma minta "filterable by tag" di sini, AND/OR
// toggle penuh ada di News page).
const filteredReadingNews = computed(() => {
  if (!filterTags.value.length) return readingNews.value
  return readingNews.value.filter((r) =>
    filterTags.value.every((c) => (r.tags || []).some((t) => t.canonical === c))
  )
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
    <h2>Berita for Reading Hari Ini</h2>
    <div class="panel">
      <div class="chart-head" style="margin-bottom:12px">
        <label class="src">Filter tag</label>
        <span v-for="c in filterTags" :key="c" class="badge" :class="FACET_COLOR[c.split(':')[0]]" style="margin-right:4px">
          {{ c }} <a href="#" style="color:inherit" @click.prevent="removeFilterTag(c)">&times;</a>
        </span>
        <TagAutocomplete :excludeCanonicals="filterTags" placeholder="filter by tag..." @select="addFilterTag" />
      </div>
      <div v-if="!filteredReadingNews.length" class="empty-inline">belum ada berita for_reading hari ini (sesuai filter) — tandai di Panel News dulu.</div>
      <table v-else>
        <thead><tr><th>Impact</th><th>Headline</th><th>Sumber</th></tr></thead>
        <tbody>
          <tr v-for="r in filteredReadingNews" :key="r.id">
            <td><span class="badge" :class="r.impact_level">{{ r.impact_level }}</span></td>
            <td>
              <a v-if="r.raw_url" :href="r.raw_url" target="_blank" rel="noopener">{{ r.headline }}</a>
              <span v-else>{{ r.headline }}</span>
              <div v-if="r.display_subtitle" class="src">✎ {{ r.display_subtitle }}</div>
            </td>
            <td class="src">{{ r.source }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="src" style="margin-top:6px">Berita yang kamu tandai "for Reading" di Panel News — bahan buat nulis 4 lensa di bawah.</div>
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
