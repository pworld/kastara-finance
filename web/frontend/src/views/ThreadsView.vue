<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import DataTable from '../components/DataTable.vue'
import TagAutocomplete from '../components/TagAutocomplete.vue'
import { get, post } from '../lib/api'
import { FACET_COLOR, THREAD_STATUS_CLASS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Threads -> kelola News Threads (Addendum B §20 + Addendum C §21.11
// komposisi/umur/facet tags). 17 Jul 2026: menu berdiri sendiri (BUKAN tab
// di dalam Settings/Tags) -- Giel eksplisit tidak mau tab. `/threads/:id`
// (timeline, konfirmasi/tolak SUGGESTED) TETAP terpisah -- fungsi beda
// (baca hasil), bukan kurasi.
const { toast } = useAppToast()
const router = useRouter()

const allThreads = ref([])
const loadingThreads = ref(true)
const statusFilter = ref('')
async function loadThreads() {
  loadingThreads.value = true
  try {
    allThreads.value = await get('/api/threads/stats')
  } catch (err) {
    // Tanpa try/finally, fetch gagal bikin loadingThreads nyangkut true
    // selamanya -- "Memuat..." tampil terus, tabel TIDAK PERNAH muncul.
    toast(err.message || 'Gagal memuat thread')
  } finally {
    loadingThreads.value = false
  }
}
onMounted(loadThreads)
// Filter client-side (dataset kecil, tidak ada batas jumlah lagi) --
// activeCount dihitung dari allThreads (BUKAN hasil filter), supaya
// jumlah ACTIVE tetap benar meski Giel lagi filter status=CLOSED mis.-nya.
const threads = computed(() => statusFilter.value ? allThreads.value.filter((t) => t.status === statusFilter.value) : allThreads.value)
const activeCount = computed(() => allThreads.value[0]?.active_count ?? 0)

function openTimeline(row) {
  router.push(`/threads/${row.id}`)
}

// Inline edit title/status/bacaan-terkini/keywords langsung dari tabel
// (Giel tidak mau selalu buka dialog cuma utk ubah field basic) -- pola
// sama subtitleInputs di NewsView.vue. Verdict/persona_tags/facet tags tetap
// lewat Dialog "Kelola" (butuh UI lebih dari 1 baris).
const editingIds = ref(new Set())
const editInputs = ref({})
function startEdit(row) {
  editingIds.value.add(row.id)
  editInputs.value[row.id] = {
    title: row.title, status: row.status, verdict: row.verdict || '',
    keywordsCsv: (row.keywords || []).join(', '), currentRead: row.current_read || '',
  }
}
function cancelEdit(row) {
  editingIds.value.delete(row.id)
}
async function saveEdit(row) {
  const input = editInputs.value[row.id]
  if (!input.title.trim()) { toast('Title wajib diisi'); return }
  // 6 Agustus 2026: Giel lapor "tidak bisa save status inactive, tidak
  // bisa klik simpan" -- root cause: backend WAJIB verdict saat status
  // CLOSED (patch_thread guard, §20.1 vonis auditable), tapi form quick-
  // edit ini dulu TIDAK PUNYA field verdict sama sekali -- klik Simpan
  // selalu gagal diam2 (toast error gampang kelewat) begitu status
  // diganti CLOSED. Sekarang verdict wajib diisi DI SINI JUGA sebelum
  // kirim, bukan cuma diserahkan ke backend utk gagal.
  if (input.status === 'CLOSED' && !input.verdict.trim()) {
    toast('Verdict wajib diisi saat menutup thread (status=CLOSED)'); return
  }
  const body = {
    title: input.title, status: input.status, current_read: input.currentRead,
    keywords: input.keywordsCsv.split(',').map((k) => k.trim().toLowerCase()).filter(Boolean),
  }
  if (input.status === 'CLOSED') body.verdict = input.verdict
  const result = await post(`/api/threads/${row.id}`, body)
  if (result.error) { toast(result.error); return }
  toast('Thread diperbarui')
  editingIds.value.delete(row.id)
  loadThreads()
}

// Dialog "Kelola Thread" -- verdict/persona_tags/facet tags, field yang
// butuh lebih dari 1 baris input.
const manageOpen = ref(false)
const manageThread = ref(null)
const manageForm = ref({ status: '', verdict: '', personaTags: [] })

function openManage(row) {
  manageThread.value = row
  manageForm.value = { status: row.status, verdict: row.verdict || '', personaTags: [...(row.persona_tags || [])] }
  manageOpen.value = true
}
async function saveManage() {
  const body = { status: manageForm.value.status, persona_tags: manageForm.value.personaTags }
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

// + Thread baru.
const newThreadForm = ref({ title: '', description: '', keywordsCsv: '', currentRead: '' })
async function createThread() {
  if (!newThreadForm.value.title.trim()) { toast('Title wajib diisi'); return }
  const keywords = newThreadForm.value.keywordsCsv.split(',').map((k) => k.trim().toLowerCase()).filter(Boolean)
  const result = await post('/api/threads', {
    title: newThreadForm.value.title, description: newThreadForm.value.description || null,
    keywords, current_read: newThreadForm.value.currentRead || null,
  })
  if (result.error) { toast(result.error); return }
  toast(`Thread "${result.title}" dibuat`)
  newThreadForm.value = { title: '', description: '', keywordsCsv: '', currentRead: '' }
  loadThreads()
}

// Gabung thread duplikat (24 Jul 2026) -- Giel: dua thread ternyata narasi
// sama (mis. kandidat seed vs thread real), TIDAK mau cuma close/dormant-kan
// salah satu (itu diam-diam buang data) -- gabung beneran: link+facet tags
// dari "from" pindah ke "into", keywords/persona_tags di-union. "from" hilang
// setelahnya. current_read TIDAK auto-digabung (bisa berlawanan arah, mis.
// Hawkish vs Dovish) -- toast tampilkan current_read lama "from" biar Giel
// bisa copy manual kalau perlu.
const mergeFrom = ref('')
const mergeInto = ref('')
async function mergeThreads() {
  if (!mergeFrom.value || !mergeInto.value) { toast('Pilih thread from dan into'); return }
  if (mergeFrom.value === mergeInto.value) { toast('Tidak bisa merge thread ke dirinya sendiri'); return }
  const result = await post('/api/threads/merge', { from_id: Number(mergeFrom.value), into_id: Number(mergeInto.value) })
  if (result.error) { toast(result.error); return }
  let msg = `Digabung ke "${result.title}"`
  if (result.merged_from_current_read) msg += ` -- bacaan lama thread yang digabung: "${result.merged_from_current_read}"`
  toast(msg)
  mergeFrom.value = ''
  mergeInto.value = ''
  loadThreads()
}
</script>

<template>
  <section>
    <h2>News Threads</h2>
    <div class="panel">
      <p class="src" style="margin-bottom:12px">
        Benang narasi lintas waktu (Addendum B §20) -- unit penautan adalah
        THREAD, bukan artikel-ke-artikel. Auto-suggest jalan tiap run_daily
        (keyword + tag-match), konfirmasi/tolak saran di halaman News. Tidak
        ada batas jumlah thread ACTIVE -- kamu yang tentukan lewat status.
      </p>
      <p class="src" style="margin-bottom:12px">{{ activeCount }} thread ACTIVE.</p>
      <div class="chart-head" style="margin-bottom:12px">
        <label class="src">Status</label>
        <select v-model="statusFilter" style="width:auto">
          <option value="">Semua</option>
          <option value="ACTIVE">ACTIVE</option>
          <option value="DORMANT">DORMANT</option>
          <option value="CLOSED">CLOSED</option>
        </select>
      </div>
      <p v-if="loadingThreads" class="src">Memuat...</p>
      <DataTable v-else :rows="threads" :dataKey="'id'" :searchFields="['title', 'current_read']" emptyMessage="belum ada thread">
        <Column field="title" header="Title" sortable>
          <template #body="{ data }">
            <input v-if="editingIds.has(data.id)" v-model="editInputs[data.id].title" type="text" style="width:140px">
            <a v-else href="#" @click.prevent="openTimeline(data)">{{ data.title }}</a>
          </template>
        </Column>
        <Column field="status" header="Status" sortable>
          <template #body="{ data }">
            <template v-if="editingIds.has(data.id)">
              <select v-model="editInputs[data.id].status" style="width:auto">
                <option value="ACTIVE">ACTIVE</option>
                <option value="DORMANT">DORMANT</option>
                <option value="CLOSED">CLOSED</option>
              </select>
              <input
                v-if="editInputs[data.id].status === 'CLOSED'"
                v-model="editInputs[data.id].verdict" type="text" placeholder="Verdict (wajib)"
                style="width:140px; margin-top:4px; display:block"
              >
            </template>
            <span v-else class="badge" :class="THREAD_STATUS_CLASS[data.status]">{{ data.status }}</span>
          </template>
        </Column>
        <Column field="current_read" header="Bacaan Terkini">
          <template #body="{ data }">
            <input v-if="editingIds.has(data.id)" v-model="editInputs[data.id].currentRead" type="text" style="width:140px">
            <span v-else class="src">{{ data.current_read || '-' }}</span>
          </template>
        </Column>
        <Column header="Keywords">
          <template #body="{ data }">
            <input v-if="editingIds.has(data.id)" v-model="editInputs[data.id].keywordsCsv" type="text" style="width:140px">
            <span v-else class="src">{{ (data.keywords || []).join(', ') || '-' }}</span>
          </template>
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
          <template #body="{ data }">
            <template v-if="editingIds.has(data.id)">
              <button class="btn small" @click="saveEdit(data)">Simpan</button>
              <button class="btn small secondary" @click="cancelEdit(data)">Batal</button>
            </template>
            <template v-else>
              <button class="btn small secondary" @click="startEdit(data)">Edit</button>
              <button class="btn small secondary" @click="openManage(data)">Kelola</button>
              <button class="btn small secondary" @click="openTimeline(data)">Timeline</button>
            </template>
          </template>
        </Column>
      </DataTable>
    </div>
  </section>

  <section>
    <h2>+ Thread Baru</h2>
    <div class="panel">
      <div class="form-row">
        <label class="field">Title</label>
        <input v-model="newThreadForm.title" type="text" placeholder="mis. Rezim Warsh Hawkish">
      </div>
      <div class="form-row">
        <label class="field">Description (opsional)</label>
        <textarea v-model="newThreadForm.description"></textarea>
      </div>
      <div class="form-row">
        <label class="field">Keywords (comma-separated, dipakai auto-suggest)</label>
        <input v-model="newThreadForm.keywordsCsv" type="text" placeholder="mis. warsh, hawkish, fed">
      </div>
      <div class="form-row">
        <label class="field">Bacaan Terkini (opsional, 1 kalimat)</label>
        <input v-model="newThreadForm.currentRead" type="text">
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="createThread">Buat Thread</button>
      </div>
    </div>
  </section>

  <section>
    <h2>Gabung Thread Duplikat</h2>
    <div class="panel">
      <p class="src">
        Untuk thread yang ternyata narasi sama/tumpang tindih (mis. kandidat
        seed vs thread real). "From" hilang, semua link + facet tags pindah
        ke "into", keywords digabung (union). Bacaan Terkini TIDAK
        auto-digabung (bisa berlawanan arah) -- toast tampilkan punya "from"
        biar bisa disalin manual kalau perlu.
      </p>
      <div class="form-grid">
        <div>
          <label class="field">From (hilang setelah digabung)</label>
          <select v-model="mergeFrom" style="width:100%">
            <option value="">pilih thread...</option>
            <option v-for="t in allThreads" :key="t.id" :value="t.id">{{ t.title }} ({{ t.status }})</option>
          </select>
        </div>
        <div>
          <label class="field">Into (tetap)</label>
          <select v-model="mergeInto" style="width:100%">
            <option value="">pilih thread...</option>
            <option v-for="t in allThreads" :key="t.id" :value="t.id">{{ t.title }} ({{ t.status }})</option>
          </select>
        </div>
      </div>
      <div class="form-row" style="margin-top:8px">
        <button class="btn small" @click="mergeThreads">Gabung</button>
      </div>
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
