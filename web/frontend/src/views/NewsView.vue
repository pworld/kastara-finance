<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import DataTable from '../components/DataTable.vue'
import TagAutocomplete from '../components/TagAutocomplete.vue'
import { get, post } from '../lib/api'
import { today, daysAgo, LINK_STATUS_CLASS, FACET_COLOR, LENS_LABELS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'
import { preserveScroll } from '../composables/useScrollPreserve'

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

// ---------- Kirim ke Lensa (Addendum C §21.4, GELOMBANG C-2) -- jalur
// ke-3 konteks persona (di luar slice otomatis harian + thread digest):
// filter tag -> centang berita -> kirim TAMBAHAN ke satu lensa. Guard
// non-negotiable (tidak pernah ganti slice) hidup di compose_persona_context
// itu sendiri, bukan di sini -- checkbox ini murni kumpulkan id. ----------
const selectedNewsIds = ref(new Set())
function toggleSelectNews(row) {
  if (selectedNewsIds.value.has(row.id)) selectedNewsIds.value.delete(row.id)
  else selectedNewsIds.value.add(row.id)
}
const lensDialogOpen = ref(false)
const selectedLens = ref('GEMA')
async function sendToLens() {
  const result = await post('/api/persona/run', { lens: selectedLens.value, news_ids: [...selectedNewsIds.value] })
  if (result.error) { toast(result.error); return }
  toast(`${selectedNewsIds.value.size} berita dikirim ke lensa ${selectedLens.value} (tambahan, bukan pengganti slice)`)
  lensDialogOpen.value = false
  selectedNewsIds.value = new Set()
}

async function toggleForReading(row) {
  const now = !!row.for_reading
  await post('/api/news/for_reading', { id: row.id, for_reading: !now })
  toast(now ? 'Dilepas dari Reading' : 'Ditandai for Reading')
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
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
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
}

// ---------- Faceted Tagging C-1: pasang/lepas tag per baris berita
// (Addendum C §21.3). Tag = klasifikasi (objektif), BEDA dari for_reading di
// atas (kurasi, subjektif) -- 2 aksi terpisah, bukan 1 checkbox merangkap 2. ----------
async function onTagSelected(row, tag) {
  const result = await post('/api/content_tags', { ref_table: 'daily_news', ref_id: row.id, tag: tag.canonical })
  if (result.error) { toast(result.error); return }
  toast(`Tag ${tag.canonical} dipasang`)
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
}

async function removeTag(contentTagId) {
  await post(`/api/content_tags/${contentTagId}/remove`, {})
  toast('Tag dilepas')
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
}

async function confirmTag(contentTagId) {
  await post(`/api/content_tags/${contentTagId}/confirm`, {})
  toast('Tag diterima')
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
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
// Tolak. CONFIRMED -> chip solid + stance + Lepas. Ketemu 17 Jul 2026: dulu
// backend cuma kirim 1 thread_link 'pemenang' per berita -- Giel tidak bisa
// lihat/ubah/lepas thread LAIN yang juga match berita yang sama. Sekarang
// `data.thread_links` array, tiap chip punya aksi sendiri; reject endpoint
// dipakai baik utk "Tolak" (SUGGESTED) maupun "Lepas" (CONFIRMED) -- sama-sama
// set link_status=REJECTED, endpoint sudah terima link status apa pun.
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
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
}

async function rejectThreadLink(threadLink) {
  await post(`/api/threads/link/${threadLink.link_id}/reject`, {})
  toast('Tautan thread dilepas')
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
}

// ---------- + Tautkan Thread manual: pasang link CONFIRMED langsung (Giel
// sudah tahu stance-nya), tidak lewat SUGGESTED. Reuse POST /api/threads/
// <id>/links (add_thread_link_manual, sudah ada utk ThreadDetailView). ----------
const activeThreads = ref([])
async function loadActiveThreads() {
  activeThreads.value = await get('/api/threads', { status: 'ACTIVE' })
}
onMounted(loadActiveThreads)

const linkPickerIds = ref(new Set())
const linkPickerInputs = ref({})
function startAddThreadLink(row) {
  linkPickerIds.value.add(row.id)
  linkPickerInputs.value[row.id] = { threadId: '', stance: 'MENDUKUNG' }
}
function cancelAddThreadLink(row) {
  linkPickerIds.value.delete(row.id)
}
async function addThreadLink(row) {
  const input = linkPickerInputs.value[row.id]
  if (!input?.threadId) { toast('Pilih thread dulu'); return }
  const result = await post(`/api/threads/${input.threadId}/links`, {
    ref_table: 'daily_news', ref_id: row.id, stance: input.stance,
  })
  if (result.error) { toast(result.error); return }
  toast('Ditautkan ke thread')
  linkPickerIds.value.delete(row.id)
  preserveScroll(loadNews)() // lihat useScrollPreserve.js
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
      <div class="chart-head" style="margin-bottom:12px" v-if="selectedNewsIds.size">
        <span class="src">{{ selectedNewsIds.size }} berita dipilih</span>
        <button class="btn small" @click="lensDialogOpen = true">Kirim ke Lensa →</button>
        <button class="btn small secondary" @click="selectedNewsIds = new Set()">Batal pilih</button>
      </div>
      <p v-if="loading" class="src">Memuat...</p>
      <DataTable
        v-else :rows="filteredRows" :dataKey="'id'"
        :searchFields="['headline', 'source']"
        emptyMessage="tidak ada berita untuk tanggal/filter ini"
      >
        <Column header="">
          <template #body="{ data }">
            <input type="checkbox" :checked="selectedNewsIds.has(data.id)" @change="toggleSelectNews(data)">
          </template>
        </Column>
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
            <details v-if="data.rss_summary" class="collapsible" style="margin-top:2px">
              <summary class="src">ringkasan RSS</summary>
              <p class="src" style="margin:4px 0 0; max-width:320px">{{ data.rss_summary }}</p>
            </details>
          </template>
        </Column>
        <Column field="source" header="Sumber" sortable>
          <template #body="{ data }"><span class="src">{{ data.source }}</span></template>
        </Column>
        <Column header="Thread">
          <template #body="{ data }">
            <p v-if="!data.thread_links || !data.thread_links.length" class="src" style="margin:0 0 6px">—</p>
            <div v-for="tl in data.thread_links" :key="tl.link_id" style="margin-bottom:8px; padding-bottom:6px; border-bottom:1px solid var(--border)">
              <div class="src">Nama Thread</div>
              <div>
                <span class="badge" :class="tl.link_status === 'SUGGESTED' ? LINK_STATUS_CLASS.SUGGESTED : LINK_STATUS_CLASS.CONFIRMED">{{ tl.thread_title }}</span>
              </div>
              <div class="src" style="margin-top:2px">Opsi</div>
              <div>{{ tl.link_status === 'SUGGESTED' ? '(belum dikonfirmasi)' : tl.stance }}</div>
              <div style="margin-top:4px">
                <template v-if="tl.link_status === 'SUGGESTED'">
                  <button class="btn small secondary" @click="openStanceDialog(tl)">Konfirmasi</button>
                  <button class="btn small danger" @click="rejectThreadLink(tl)">Tolak</button>
                </template>
                <button v-else class="btn small danger" @click="rejectThreadLink(tl)">Lepas</button>
              </div>
            </div>
            <div v-if="linkPickerIds.has(data.id)">
              <div class="src">Nama Thread</div>
              <select v-model="linkPickerInputs[data.id].threadId" style="width:100%; margin-bottom:4px">
                <option value="">pilih thread...</option>
                <option v-for="t in activeThreads" :key="t.id" :value="t.id">{{ t.title }}</option>
              </select>
              <div class="src">Opsi</div>
              <select v-model="linkPickerInputs[data.id].stance" style="width:100%; margin-bottom:4px">
                <option value="MENDUKUNG">MENDUKUNG</option>
                <option value="KONTRA">KONTRA</option>
                <option value="NETRAL">NETRAL</option>
              </select>
              <div>
                <button class="btn small" @click="addThreadLink(data)">Tautkan</button>
                <button class="btn small secondary" @click="cancelAddThreadLink(data)">Batal</button>
              </div>
            </div>
            <a v-else href="#" @click.prevent="startAddThreadLink(data)">+ Tautkan Thread</a>
          </template>
        </Column>
        <Column header="Tag">
          <template #body="{ data }">
            <div v-for="t in data.tags" :key="t.id" style="margin-bottom:4px; display:flex; align-items:center; gap:4px">
              <input
                v-if="t.source === 'SUGGESTED'" type="checkbox"
                title="ceklis utk terima tag ini" @change="confirmTag(t.id)"
              >
              <span
                class="badge" :class="FACET_COLOR[t.facet]"
                :style="t.source === 'SUGGESTED' ? { border: '1px dashed currentColor', opacity: 0.75 } : {}"
                :title="t.source === 'SUGGESTED' ? 'auto-suggest, belum dikonfirmasi -- ceklis utk terima' : 'dipasang manual'"
              >{{ t.canonical }}<span v-if="t.source === 'SUGGESTED'">?</span></span>
              <a href="#" style="color:inherit" @click.prevent="removeTag(t.id)">&times;</a>
            </div>
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

  <Dialog v-model:visible="lensDialogOpen" modal header="Kirim ke Lensa" style="width:420px; max-width:90vw">
    <p class="src">
      {{ selectedNewsIds.size }} berita akan ditambahkan sebagai konteks TAMBAHAN
      (bukan pengganti slice otomatis) utk lensa terpilih -- Addendum C §21.4.
    </p>
    <div class="form-row">
      <label class="field">Lensa</label>
      <select v-model="selectedLens">
        <option v-for="code in ['GEMA', 'LEON', 'AKELA', 'RIVAN']" :key="code" :value="code">{{ code }} -- {{ LENS_LABELS[code] }}</option>
      </select>
    </div>
    <div class="form-row" style="margin-top:12px">
      <button class="btn" @click="sendToLens">Kirim</button>
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
