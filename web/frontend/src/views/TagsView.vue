<script setup>
import { ref, onMounted } from 'vue'
import Column from 'primevue/column'
import DataTable from '../components/DataTable.vue'
import { get, post } from '../lib/api'
import { FACET_COLOR } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Tags -> kurasi lambat/reflektif kamus tag (Addendum C §21.11). BEDA dari
// command-palette CEPAT di News/Reading (prinsip "capture cepat, curate
// lambat"). 17 Jul 2026: eks "Settings" dipecah jadi 2 menu berdiri sendiri
// (Tags + Threads) -- Giel tidak mau tab, tiap satu menu sendiri.
const { toast } = useAppToast()

const tags = ref([])
const loadingTags = ref(true)
const orphansOnly = ref(false)

async function loadTags() {
  loadingTags.value = true
  try {
    tags.value = await get(orphansOnly.value ? '/api/tags/orphans' : '/api/tags')
  } catch (err) {
    // Tanpa try/finally, fetch gagal bikin loadingTags nyangkut true selamanya
    // -- "Memuat..." tampil terus, tabel TIDAK PERNAH muncul.
    toast(err.message || 'Gagal memuat tag')
  } finally {
    loadingTags.value = false
  }
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

// + Tag baru -- form penuh (canonical + aliases + description sekaligus),
// beda dari TagAutocomplete's "+ buat tag baru" (canonical-only, jalur cepat
// News/Reading) -- di sini Giel biasanya sudah tahu alias/deskripsi dari
// awal, tidak perlu edit 2 langkah.
const newTag = ref({ canonical: '', aliasesCsv: '', description: '' })
async function createTagForm() {
  if (!newTag.value.canonical.trim()) { toast('Canonical wajib diisi (format facet:value)'); return }
  const aliases = newTag.value.aliasesCsv.split(',').map((a) => a.trim().toLowerCase()).filter(Boolean)
  const result = await post('/api/tags', {
    canonical: newTag.value.canonical.trim().toLowerCase(),
    aliases, description: newTag.value.description || null,
  })
  if (result.error) { toast(result.error); return }
  toast(`Tag "${result.canonical}" dibuat`)
  newTag.value = { canonical: '', aliasesCsv: '', description: '' }
  loadTags()
}
</script>

<template>
  <section>
    <h2>Tags</h2>
    <div class="panel">
      <p class="src">
        Kurasi lambat/reflektif kamus tag (Addendum C §21.11) -- BEDA dari
        News/Reading yang cepat sehari-hari. Buat/edit/gabung/hapus tag di sini.
      </p>
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
      <h2 style="font-size:14px">+ Tag Baru</h2>
      <div class="form-grid">
        <div><label class="field">Canonical (facet:value)</label><input v-model="newTag.canonical" type="text" placeholder="mis. who:warsh"></div>
        <div><label class="field">Aliases (comma-separated, opsional)</label><input v-model="newTag.aliasesCsv" type="text" placeholder="mis. fed-warsh, warsh"></div>
      </div>
      <div class="form-row">
        <label class="field">Description (opsional)</label>
        <input v-model="newTag.description" type="text">
      </div>
      <div class="form-row" style="margin-top:8px">
        <button class="btn small" @click="createTagForm">Buat Tag</button>
      </div>
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
</template>
