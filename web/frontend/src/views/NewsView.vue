<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import DataTable from '../components/DataTable.vue'
import TagAutocomplete from '../components/TagAutocomplete.vue'
import { get, post } from '../lib/api'
import { today, daysAgo, LINK_STATUS_CLASS, FACET_COLOR } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Port dari web/static/js/panel2.js (lihat docs/migrationFE.md Fase 2).
const { toast } = useAppToast()

const rows = ref([])
const loading = ref(true)
// Default kemarin s.d. hari ini (bukan hari ini saja) -- run_daily jalan
// 00:00 WIB, tapi RSS/scraper bisa telat masuk atau belum sempat dibuka
// pagi itu juga, jadi "hari ini saja" sering kosong. Rentang 2 hari
// jamin selalu ada data buat dibaca begitu panel dibuka.
const dateFrom = ref(daysAgo(1))
const dateTo = ref(today())
const impact = ref('')

async function loadNews() {
  loading.value = true
  const params = { limit: 200 }
  if (dateFrom.value) params.date_from = dateFrom.value
  if (dateTo.value) params.date_to = dateTo.value
  // Addendum C §21.2: key_only -> for_reading (rename fungsional).
  if (impact.value === '__KEY__') params.for_reading = '1'
  else if (impact.value) params.impact = impact.value
  rows.value = await get('/api/news', params)
  loading.value = false
}
watch([dateFrom, dateTo, impact], loadNews)
onMounted(loadNews)

// ---------- Filter bar tag (Addendum C §21.3: "cermin input" -- kosakata
// filter = kosakata tagging. AND/OR toggle: AND = berita harus punya SEMUA
// tag terpilih, OR = salah satu cukup.) ----------
const filterTags = ref([])
const filterMode = ref('AND')
function addFilterTag(tag) {
  if (!filterTags.value.includes(tag.canonical)) filterTags.value.push(tag.canonical)
}
function removeFilterTag(canonical) {
  filterTags.value = filterTags.value.filter((c) => c !== canonical)
}
const filteredRows = computed(() => {
  if (!filterTags.value.length) return rows.value
  return rows.value.filter((r) => {
    const have = (r.tags || []).map((t) => t.canonical)
    return filterMode.value === 'AND'
      ? filterTags.value.every((c) => have.includes(c))
      : filterTags.value.some((c) => have.includes(c))
  })
})

async function toggleForReading(row) {
  const now = !!row.for_reading
  await post('/api/news/for_reading', { id: row.id, for_reading: !now })
  toast(now ? 'Dilepas dari Reading' : 'Ditandai for Reading')
  loadNews()
}

// ---------- display_subtitle (Addendum C §21.2 poin d): judul/catatan Giel
// TERPISAH dari headline asli (tidak pernah ditimpa). Input inline pola sama
// ForwardView.vue's econ_calendar actual edit (Set id -> editing, dict id -> draft value). ----------
const editingSubtitleIds = ref(new Set())
const subtitleInputs = ref({})
function startEditSubtitle(row) {
  editingSubtitleIds.value.add(row.id)
  subtitleInputs.value[row.id] = row.display_subtitle || ''
}
async function saveSubtitle(row) {
  await post(`/api/news/${row.id}/display_subtitle`, { display_subtitle: subtitleInputs.value[row.id] || null })
  toast('Subtitle tersimpan')
  editingSubtitleIds.value.delete(row.id)
  loadNews()
}

// ---------- Faceted Tagging C-1: pasang/lepas tag per baris berita
// (Addendum C §21.3). Tag = klasifikasi (objektif), BEDA dari for_reading di
// atas (kurasi, subjektif) -- 2 aksi terpisah, bukan 1 checkbox merangkap 2. ----------
async function onTagSelected(row, tag) {
  const result = await post('/api/content_tags', { ref_table: 'daily_news', ref_id: row.id, tag: tag.canonical })
  if (result.error) { toast(result.error); return }
  toast(`Tag ${tag.canonical} dipasang`)
  loadNews()
}

async function removeTag(contentTagId) {
  await post(`/api/content_tags/${contentTagId}/remove`, {})
  toast('Tag dilepas')
  loadNews()
}

// "Telusuri Semua Tag" -- panel sekunder, jarang dibuka (§21.3), tapi
// dataset-nya kecil (vocab tumbuh pelan) jadi dimuat eager di mount, bukan
// lazy on-open -- lebih simpel, tidak perlu state loading-on-toggle.
const allTagsList = ref([])
const loadingTags = ref(true)
async function loadAllTags() {
  loadingTags.value = true
  allTagsList.value = await get('/api/tags')
  loadingTags.value = false
}
onMounted(loadAllTags)

// ---------- News Threads N-1: chip "Saran: <thread>?" + konfirmasi stance ----------
// (Addendum B §20.5). SUGGESTED -> Konfirmasi (buka dialog pilih stance) /
// Tolak. CONFIRMED -> chip solid + stance, tidak ada aksi lagi di sini.
const stanceDialogOpen = ref(false)
const stanceDialogLink = ref(null)
const selectedStance = ref('MENDUKUNG')
const alsoForReading = ref(false)

function openStanceDialog(threadLink) {
  stanceDialogLink.value = threadLink
  selectedStance.value = 'MENDUKUNG'
  alsoForReading.value = false
  stanceDialogOpen.value = true
}

async function confirmThreadLink() {
  await post(`/api/threads/link/${stanceDialogLink.value.link_id}/confirm`, {
    stance: selectedStance.value, also_for_reading: alsoForReading.value,
  })
  toast(`Ditautkan ke "${stanceDialogLink.value.thread_title}" (${selectedStance.value})`)
  stanceDialogOpen.value = false
  loadNews()
}

async function rejectThreadLink(threadLink) {
  await post(`/api/threads/link/${threadLink.link_id}/reject`, {})
  toast('Saran thread ditolak')
  loadNews()
}

// + Add Manual Article
const art = ref({ date: today(), source: '', url: '', headline: '', notes: '', tags: '', keyEvent: false })

async function saveArticle() {
  if (!art.value.headline.trim()) { toast('Headline wajib diisi'); return }
  await post('/api/articles/add', {
    date: art.value.date || today(), source: art.value.source, url: art.value.url,
    headline: art.value.headline, notes: art.value.notes, tags: art.value.tags,
    key_event: art.value.keyEvent,
  })
  toast('Artikel tersimpan')
  art.value = { date: today(), source: '', url: '', headline: '', notes: '', tags: '', keyEvent: false }
}
</script>

<template>
  <section>
    <h2>Berita &amp; Impact</h2>
    <div class="panel">
      <div class="chart-head" style="margin-bottom:12px">
        <label class="src">Dari</label>
        <input v-model="dateFrom" type="date" style="width:auto">
        <label class="src">Sampai</label>
        <input v-model="dateTo" type="date" style="width:auto">
        <label class="src">Impact</label>
        <select v-model="impact" style="width:auto">
          <option value="">Semua</option>
          <option value="HIGH">HIGH</option>
          <option value="MED">MED</option>
          <option value="LOW">LOW</option>
          <option value="__KEY__">📖 for Reading saja</option>
        </select>
      </div>
      <div class="chart-head" style="margin-bottom:12px">
        <label class="src">Filter tag</label>
        <span v-for="c in filterTags" :key="c" class="badge" :class="FACET_COLOR[c.split(':')[0]]" style="margin-right:4px">
          {{ c }} <a href="#" style="color:inherit" @click.prevent="removeFilterTag(c)">&times;</a>
        </span>
        <TagAutocomplete :excludeCanonicals="filterTags" placeholder="filter by tag..." @select="addFilterTag" />
        <select v-if="filterTags.length" v-model="filterMode" style="width:auto">
          <option value="AND">AND (semua tag)</option>
          <option value="OR">OR (salah satu)</option>
        </select>
      </div>
      <p v-if="loading" class="src">Memuat...</p>
      <DataTable
        v-else :rows="filteredRows" :dataKey="'id'"
        :searchFields="['headline', 'source']"
        emptyMessage="tidak ada berita untuk tanggal/filter ini"
      >
        <Column field="date" header="Tanggal" sortable>
          <template #body="{ data }"><span class="src">{{ data.date }}</span></template>
        </Column>
        <Column field="impact_level" header="Impact" sortable>
          <template #body="{ data }"><span class="badge" :class="data.impact_level">{{ data.impact_level }}</span></template>
        </Column>
        <Column field="headline" header="Headline" sortable>
          <template #body="{ data }">
            <a v-if="data.raw_url" :href="data.raw_url" target="_blank" rel="noopener">{{ data.headline }}</a>
            <span v-else>{{ data.headline }}</span>
            <div v-if="!editingSubtitleIds.has(data.id)" class="src">
              <template v-if="data.display_subtitle">✎ {{ data.display_subtitle }} </template>
              <a href="#" @click.prevent="startEditSubtitle(data)">{{ data.display_subtitle ? '(ubah)' : '+ subtitle' }}</a>
            </div>
            <div v-else>
              <input
                :value="subtitleInputs[data.id] || ''" @input="subtitleInputs[data.id] = $event.target.value"
                type="text" placeholder="catatan/subtitle kamu" style="width:200px;display:inline-block"
              >
              <button class="btn small secondary" @click="saveSubtitle(data)">Simpan</button>
            </div>
          </template>
        </Column>
        <Column field="source" header="Sumber" sortable>
          <template #body="{ data }"><span class="src">{{ data.source }}</span></template>
        </Column>
        <Column header="Thread">
          <template #body="{ data }">
            <template v-if="!data.thread_link"><span class="src">—</span></template>
            <template v-else-if="data.thread_link.link_status === 'SUGGESTED'">
              <span class="badge" :class="LINK_STATUS_CLASS.SUGGESTED">Saran: {{ data.thread_link.thread_title }}?</span>
              <button class="btn small secondary" @click="openStanceDialog(data.thread_link)">Konfirmasi</button>
              <button class="btn small danger" @click="rejectThreadLink(data.thread_link)">Tolak</button>
            </template>
            <template v-else>
              <span class="badge" :class="LINK_STATUS_CLASS.CONFIRMED">{{ data.thread_link.thread_title }}</span>
              <span class="src">({{ data.thread_link.stance }})</span>
            </template>
          </template>
        </Column>
        <Column header="Tag">
          <template #body="{ data }">
            <span v-for="t in data.tags" :key="t.id" class="badge" :class="FACET_COLOR[t.facet]" style="margin-right:4px">
              {{ t.canonical }} <a href="#" style="color:inherit" @click.prevent="removeTag(t.id)">&times;</a>
            </span>
            <TagAutocomplete
              :excludeCanonicals="(data.tags || []).map(t => t.canonical)"
              @select="(tag) => onTagSelected(data, tag)"
            />
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <button
              class="btn small" :class="data.for_reading ? 'key-on' : 'secondary'"
              @click="toggleForReading(data)"
            >{{ data.for_reading ? '★ Reading' : '📖 baca' }}</button>
          </template>
        </Column>
      </DataTable>
    </div>
  </section>

  <Dialog v-model:visible="stanceDialogOpen" modal header="Konfirmasi Tautan Thread" style="width:420px; max-width:90vw">
    <p v-if="stanceDialogLink" class="src">
      Tautkan berita ini ke thread "<b>{{ stanceDialogLink.thread_title }}</b>" -- pilih stance
      (WAJIB, anti-confirmation-funnel): apakah berita ini MENDUKUNG, KONTRA, atau NETRAL
      terhadap bacaan thread saat ini?
    </p>
    <div class="form-row">
      <label class="field">Stance</label>
      <select v-model="selectedStance">
        <option value="MENDUKUNG">MENDUKUNG</option>
        <option value="KONTRA">KONTRA</option>
        <option value="NETRAL">NETRAL</option>
      </select>
    </div>
    <div class="form-row">
      <label class="field"><input v-model="alsoForReading" type="checkbox"> Sekalian tandai for Reading</label>
    </div>
    <div class="form-row" style="margin-top:12px">
      <button class="btn" @click="confirmThreadLink">Konfirmasi</button>
    </div>
  </Dialog>

  <section>
    <details class="collapsible">
      <summary>Telusuri Semua Tag (Addendum C §21.3)</summary>
      <div class="panel">
        <p v-if="loadingTags" class="src">Memuat...</p>
        <DataTable v-else :rows="allTagsList" :dataKey="'id'" :searchFields="['canonical']" emptyMessage="kamus tag masih kosong">
          <Column field="canonical" header="Tag" sortable>
            <template #body="{ data }"><span class="badge" :class="FACET_COLOR[data.facet]">{{ data.canonical }}</span></template>
          </Column>
          <Column field="facet" header="Facet" sortable />
          <Column field="usage_count" header="Dipakai" sortable />
          <Column header="Aliases"><template #body="{ data }"><span class="src">{{ (data.aliases || []).join(', ') || '-' }}</span></template></Column>
        </DataTable>
      </div>
    </details>
  </section>

  <section>
    <h2>+ Add Manual Article</h2>
    <div class="panel">
      <div class="form-grid">
        <div><label class="field">Tanggal</label><input v-model="art.date" type="date"></div>
        <div><label class="field">Sumber</label><input v-model="art.source" type="text" placeholder="mis. CNBC"></div>
        <div><label class="field">URL (opsional)</label><input v-model="art.url" type="url"></div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <label class="field">Headline</label>
        <input v-model="art.headline" type="text">
      </div>
      <div class="form-row">
        <label class="field">Catatan pribadi</label>
        <textarea v-model="art.notes"></textarea>
      </div>
      <div class="form-grid">
        <div><label class="field">Tags (comma-separated)</label><input v-model="art.tags" type="text"></div>
        <div style="align-self:end">
          <label class="field"><input v-model="art.keyEvent" type="checkbox"> Flag sebagai key event</label>
        </div>
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="saveArticle">Simpan Artikel</button>
      </div>
    </div>
  </section>
</template>
