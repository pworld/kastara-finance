<script setup>
import { ref, computed, onMounted } from 'vue'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import DataTable from '../components/DataTable.vue'
import TagAutocomplete from '../components/TagAutocomplete.vue'
import { get, post } from '../lib/api'
import { FACET_COLOR, THREAD_STATUS_CLASS, LENS_LABELS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Settings -> Tag & Thread Management (Addendum C §21.11). Ini C-1 gap yang
// ketinggalan di pass pertama (§21.8 daftar ini di bawah GELOMBANG C-1, bukan
// C-2) -- kurasi LAMBAT/reflektif (merge/delete/composition/age), terpisah
// dari command-palette CEPAT di News/Reading yang sudah ada (prinsip "capture
// cepat, curate lambat", §21.11).
const { toast } = useAppToast()
const activeTab = ref('tags')

// ---------- Tab Tags ----------
const tags = ref([])
const loadingTags = ref(true)
const orphansOnly = ref(false)

async function loadTags() {
  loadingTags.value = true
  tags.value = await get(orphansOnly.value ? '/api/tags/orphans' : '/api/tags')
  loadingTags.value = false
}
onMounted(loadTags)

const editingTagIds = ref(new Set())
const tagEditInputs = ref({})
function startEditTag(row) {
  editingTagIds.value.add(row.id)
  tagEditInputs.value[row.id] = { description: row.description || '', facet: row.facet }
}
function cancelEditTag(row) {
  editingTagIds.value.delete(row.id)
}
async function saveEditTag(row) {
  const input = tagEditInputs.value[row.id]
  const result = await post(`/api/tags/${row.id}`, input)
  if (result.error) { toast(result.error); return }
  toast('Tag diperbarui')
  editingTagIds.value.delete(row.id)
  loadTags()
}

const deleteForceIds = ref(new Set())
async function deleteTag(row) {
  const force = deleteForceIds.value.has(row.id)
  const result = await post(`/api/tags/${row.id}/delete`, { force })
  if (result.error) { toast(result.error); return }
  toast(`Tag "${row.canonical}" dihapus`)
  loadTags()
}

// Merge -- operasi yang mustahil dilakukan inline di News (§21.11).
const mergeFrom = ref('')
const mergeInto = ref('')
async function mergeTags() {
  if (!mergeFrom.value || !mergeInto.value) { toast('Pilih tag from dan into'); return }
  if (mergeFrom.value === mergeInto.value) { toast('Tidak bisa merge tag ke dirinya sendiri'); return }
  const result = await post('/api/tags/merge', { from_id: Number(mergeFrom.value), into_id: Number(mergeInto.value) })
  if (result.error) { toast(result.error); return }
  toast(`Digabung ke "${result.canonical}"`)
  mergeFrom.value = ''
  mergeInto.value = ''
  loadTags()
}

// ---------- Tab Threads ----------
const threads = ref([])
const loadingThreads = ref(true)
async function loadThreads() {
  loadingThreads.value = true
  threads.value = await get('/api/threads/stats')
  loadingThreads.value = false
}
onMounted(loadThreads)
const activeCount = computed(() => threads.value[0]?.active_count ?? 0)

// Dialog "Kelola Thread" -- edit penuh (status/current_read/verdict/
// persona_tags/facet tags) di modal, TABEL sendiri tetap ringkas (title/
// status/komposisi/umur) supaya tidak sesak.
const manageOpen = ref(false)
const manageThread = ref(null)
const manageForm = ref({ status: '', currentRead: '', verdict: '', personaTags: [] })

function openManage(row) {
  manageThread.value = row
  manageForm.value = {
    status: row.status, currentRead: row.current_read || '', verdict: row.verdict || '',
    personaTags: [...(row.persona_tags || [])],
  }
  manageOpen.value = true
}
async function saveManage() {
  const body = {
    status: manageForm.value.status, current_read: manageForm.value.currentRead,
    persona_tags: manageForm.value.personaTags,
  }
  if (manageForm.value.status === 'CLOSED') body.verdict = manageForm.value.verdict
  const result = await post(`/api/threads/${manageThread.value.id}`, body)
  if (result.error) { toast(result.error); return }
  toast('Thread diperbarui')
  manageOpen.value = false
  loadThreads()
}
async function addThreadTag(tag) {
  const result = await post('/api/content_tags', { ref_table: 'news_threads', ref_id: manageThread.value.id, tag: tag.canonical })
  if (result.error) { toast(result.error); return }
  manageThread.value.tags = [...(manageThread.value.tags || []), { id: result.id, canonical: tag.canonical, facet: tag.facet }]
  loadThreads()
}
async function removeThreadTag(contentTagId) {
  await post(`/api/content_tags/${contentTagId}/remove`, {})
  manageThread.value.tags = (manageThread.value.tags || []).filter((t) => t.id !== contentTagId)
  loadThreads()
}
</script>

<template>
  <section>
    <h2>Settings</h2>
    <div class="panel">
      <p class="src">
        Kurasi lambat/reflektif untuk kamus tag &amp; thread (Addendum C §21.11)
        -- BEDA dari News/Reading yang cepat sehari-hari. Merge/hapus tag dan
        kelola komposisi thread di sini.
      </p>
      <div class="chart-head" style="margin:12px 0">
        <button class="btn small" :class="activeTab === 'tags' ? '' : 'secondary'" @click="activeTab = 'tags'">Tags</button>
        <button class="btn small" :class="activeTab === 'threads' ? '' : 'secondary'" @click="activeTab = 'threads'">Threads</button>
      </div>
    </div>
  </section>

  <section v-if="activeTab === 'tags'">
    <div class="panel">
      <div class="chart-head" style="margin-bottom:12px">
        <label class="field"><input v-model="orphansOnly" type="checkbox" @change="loadTags"> Tampilkan tag yatim saja (usage_count=0)</label>
      </div>
      <p v-if="loadingTags" class="src">Memuat...</p>
      <DataTable v-else :rows="tags" :dataKey="'id'" :searchFields="['canonical', 'description']" emptyMessage="kamus tag kosong">
        <Column field="canonical" header="Tag" sortable>
          <template #body="{ data }"><span class="badge" :class="FACET_COLOR[data.facet]">{{ data.canonical }}</span></template>
        </Column>
        <Column field="facet" header="Facet" sortable>
          <template #body="{ data }">
            <select v-if="editingTagIds.has(data.id)" v-model="tagEditInputs[data.id].facet" style="width:auto">
              <option v-for="f in ['geo','org','who','sym','theme','sec']" :key="f" :value="f">{{ f }}</option>
            </select>
            <span v-else class="src">{{ data.facet }}</span>
          </template>
        </Column>
        <Column field="usage_count" header="Dipakai" sortable />
        <Column header="Description">
          <template #body="{ data }">
            <input v-if="editingTagIds.has(data.id)" v-model="tagEditInputs[data.id].description" type="text" style="width:180px">
            <span v-else class="src">{{ data.description || '-' }}</span>
          </template>
        </Column>
        <Column header="Aliases"><template #body="{ data }"><span class="src">{{ (data.aliases || []).join(', ') || '-' }}</span></template></Column>
        <Column header="">
          <template #body="{ data }">
            <template v-if="editingTagIds.has(data.id)">
              <button class="btn small" @click="saveEditTag(data)">Simpan</button>
              <button class="btn small secondary" @click="cancelEditTag(data)">Batal</button>
            </template>
            <template v-else>
              <button class="btn small secondary" @click="startEditTag(data)">Edit</button>
              <label v-if="data.usage_count > 0" class="src" style="margin:0 4px">
                <input type="checkbox" :checked="deleteForceIds.has(data.id)" @change="$event.target.checked ? deleteForceIds.add(data.id) : deleteForceIds.delete(data.id)"> force
              </label>
              <button class="btn small danger" @click="deleteTag(data)">Hapus</button>
            </template>
          </template>
        </Column>
      </DataTable>
    </div>

    <div class="panel" style="margin-top:16px">
      <h2 style="font-size:14px">Gabung Tag Duplikat</h2>
      <p class="src">"From" jadi alias "into", semua konten yang ditag "from" dipindah ke "into".</p>
      <div class="form-grid">
        <div>
          <label class="field">From (dihapus, jadi alias)</label>
          <select v-model="mergeFrom" style="width:100%">
            <option value="">pilih tag...</option>
            <option v-for="t in tags" :key="t.id" :value="t.id">{{ t.canonical }}</option>
          </select>
        </div>
        <div>
          <label class="field">Into (tetap)</label>
          <select v-model="mergeInto" style="width:100%">
            <option value="">pilih tag...</option>
            <option v-for="t in tags" :key="t.id" :value="t.id">{{ t.canonical }}</option>
          </select>
        </div>
      </div>
      <div class="form-row" style="margin-top:8px">
        <button class="btn small" @click="mergeTags">Gabung</button>
      </div>
    </div>
  </section>

  <section v-if="activeTab === 'threads'">
    <div class="panel">
      <p class="src" style="margin-bottom:12px">{{ activeCount }}/7 thread ACTIVE.</p>
      <p v-if="loadingThreads" class="src">Memuat...</p>
      <DataTable v-else :rows="threads" :dataKey="'id'" :searchFields="['title']" emptyMessage="belum ada thread">
        <Column field="title" header="Title" sortable />
        <Column field="status" header="Status" sortable>
          <template #body="{ data }"><span class="badge" :class="THREAD_STATUS_CLASS[data.status]">{{ data.status }}</span></template>
        </Column>
        <Column header="Komposisi">
          <template #body="{ data }">
            <span class="src">🟢{{ data.composition.MENDUKUNG }} 🔴{{ data.composition.KONTRA }} ⚪{{ data.composition.NETRAL }} · {{ data.pending_suggested }} pending</span>
          </template>
        </Column>
        <Column field="age_days" header="Umur (hari)" sortable />
        <Column header="Facet Tags">
          <template #body="{ data }">
            <span v-for="t in data.tags" :key="t.id" class="badge" :class="FACET_COLOR[t.facet]" style="margin-right:4px">{{ t.canonical }}</span>
          </template>
        </Column>
        <Column header="">
          <template #body="{ data }"><button class="btn small secondary" @click="openManage(data)">Kelola</button></template>
        </Column>
      </DataTable>
    </div>
  </section>

  <Dialog v-model:visible="manageOpen" modal header="Kelola Thread" style="width:480px; max-width:90vw">
    <template v-if="manageThread">
      <h3 style="margin-top:0">{{ manageThread.title }}</h3>
      <div class="form-row">
        <label class="field">Status</label>
        <select v-model="manageForm.status" style="width:auto">
          <option value="ACTIVE">ACTIVE</option>
          <option value="DORMANT">DORMANT</option>
          <option value="CLOSED">CLOSED</option>
        </select>
      </div>
      <div class="form-row">
        <label class="field">Bacaan Terkini</label>
        <input v-model="manageForm.currentRead" type="text">
      </div>
      <div class="form-row" v-if="manageForm.status === 'CLOSED'">
        <label class="field">Verdict (wajib saat CLOSED)</label>
        <textarea v-model="manageForm.verdict"></textarea>
      </div>
      <div class="form-row">
        <label class="field">Persona Tags (lensa yang relevan)</label>
        <label v-for="code in ['GEMA', 'LEON', 'AKELA', 'RIVAN']" :key="code" class="src" style="margin-right:10px">
          <input type="checkbox" :value="code" v-model="manageForm.personaTags"> {{ code }}
        </label>
      </div>
      <div class="form-row">
        <label class="field">Facet Tags Thread (dipakai tag-match auto-suggest §21.5)</label>
        <span v-for="t in manageThread.tags" :key="t.id" class="badge" :class="FACET_COLOR[t.facet]" style="margin-right:4px">
          {{ t.canonical }} <a href="#" style="color:inherit" @click.prevent="removeThreadTag(t.id)">&times;</a>
        </span>
        <TagAutocomplete :excludeCanonicals="(manageThread.tags || []).map(t => t.canonical)" @select="addThreadTag" />
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="saveManage">Simpan</button>
      </div>
    </template>
  </Dialog>
</template>
