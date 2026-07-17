<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Column from 'primevue/column'
import DataTable from '../components/DataTable.vue'
import { get, post } from '../lib/api'
import { THREAD_STATUS_CLASS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// News Threads N-1 (Addendum B §20) -- halaman indeks. "Sesi pagi" (§20.6)
// konfirmasi SUGGESTED terjadi di NewsView; halaman ini utk kelola thread
// itu sendiri (buat baru, lihat status, masuk ke timeline).
const { toast } = useAppToast()
const router = useRouter()

const threads = ref([])
const loading = ref(true)
const statusFilter = ref('')

async function loadThreads() {
  loading.value = true
  const params = {}
  if (statusFilter.value) params.status = statusFilter.value
  threads.value = await get('/api/threads', params)
  loading.value = false
}
onMounted(loadThreads)

function openThread(row) {
  router.push(`/threads/${row.id}`)
}

// ---------- Inline edit title/status/keywords/bacaan terkini langsung dari
// index (Giel tidak mau selalu buka detail page cuma utk ubah field basic).
// Verdict TETAP di detail page saja (jarang dipakai, cuma wajib saat CLOSED)
// -- kalau Giel set status=CLOSED di sini tanpa verdict, patch_thread()
// nolak (ValueError), toast arahkan ke detail page. Pola sama subtitleInputs
// di NewsView.vue (Set id -> editing, dict id -> draft value). ----------
const editingIds = ref(new Set())
const editInputs = ref({})

function startEdit(row) {
  editingIds.value.add(row.id)
  editInputs.value[row.id] = {
    title: row.title, status: row.status,
    keywordsCsv: (row.keywords || []).join(', '), currentRead: row.current_read || '',
  }
}
function cancelEdit(row) {
  editingIds.value.delete(row.id)
}
async function saveEdit(row) {
  const input = editInputs.value[row.id]
  if (!input.title.trim()) { toast('Title wajib diisi'); return }
  const body = {
    title: input.title, status: input.status, current_read: input.currentRead,
    keywords: input.keywordsCsv.split(',').map((k) => k.trim().toLowerCase()).filter(Boolean),
  }
  const result = await post(`/api/threads/${row.id}`, body)
  if (result.error) { toast(result.error); return }
  toast('Thread diperbarui')
  editingIds.value.delete(row.id)
  loadThreads()
}

// + Thread baru
const form = ref({ title: '', description: '', keywordsCsv: '', currentRead: '' })

async function createThread() {
  if (!form.value.title.trim()) { toast('Title wajib diisi'); return }
  const keywords = form.value.keywordsCsv.split(',').map((k) => k.trim().toLowerCase()).filter(Boolean)
  const result = await post('/api/threads', {
    title: form.value.title, description: form.value.description || null,
    keywords, current_read: form.value.currentRead || null,
  })
  if (result.error) { toast(result.error); return }
  toast(`Thread "${result.title}" dibuat`)
  form.value = { title: '', description: '', keywordsCsv: '', currentRead: '' }
  loadThreads()
}
</script>

<template>
  <section>
    <h2>News Threads</h2>
    <div class="panel">
      <p class="src">
        Benang narasi lintas waktu (Addendum B §20) -- unit penautan adalah
        THREAD, bukan artikel-ke-artikel. Auto-suggest jalan tiap run_daily
        (rule-based keyword match), konfirmasi/tolak saran di halaman News.
        Maksimal 7 thread ACTIVE bersamaan.
      </p>
      <div class="chart-head" style="margin:12px 0">
        <label class="src">Status</label>
        <select v-model="statusFilter" style="width:auto" @change="loadThreads">
          <option value="">Semua</option>
          <option value="ACTIVE">ACTIVE</option>
          <option value="DORMANT">DORMANT</option>
          <option value="CLOSED">CLOSED</option>
        </select>
      </div>
      <p v-if="loading" class="src">Memuat...</p>
      <DataTable
        v-else :rows="threads" :dataKey="'id'"
        :searchFields="['title', 'current_read']" emptyMessage="belum ada thread"
      >
        <Column field="title" header="Title" sortable>
          <template #body="{ data }">
            <input v-if="editingIds.has(data.id)" v-model="editInputs[data.id].title" type="text" style="width:160px">
            <a v-else href="#" @click.prevent="openThread(data)">{{ data.title }}</a>
          </template>
        </Column>
        <Column field="status" header="Status" sortable>
          <template #body="{ data }">
            <select v-if="editingIds.has(data.id)" v-model="editInputs[data.id].status" style="width:auto">
              <option value="ACTIVE">ACTIVE</option>
              <option value="DORMANT">DORMANT</option>
              <option value="CLOSED">CLOSED</option>
            </select>
            <span v-else class="badge" :class="THREAD_STATUS_CLASS[data.status]">{{ data.status }}</span>
          </template>
        </Column>
        <Column field="current_read" header="Bacaan Terkini">
          <template #body="{ data }">
            <input v-if="editingIds.has(data.id)" v-model="editInputs[data.id].currentRead" type="text" style="width:160px">
            <span v-else class="src">{{ data.current_read || '-' }}</span>
          </template>
        </Column>
        <Column header="Keywords">
          <template #body="{ data }">
            <input v-if="editingIds.has(data.id)" v-model="editInputs[data.id].keywordsCsv" type="text" style="width:160px">
            <span v-else class="src">{{ (data.keywords || []).join(', ') || '-' }}</span>
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
              <button class="btn small secondary" @click="openThread(data)">Buka</button>
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
        <input v-model="form.title" type="text" placeholder="mis. Rezim Warsh Hawkish">
      </div>
      <div class="form-row">
        <label class="field">Description (opsional)</label>
        <textarea v-model="form.description"></textarea>
      </div>
      <div class="form-row">
        <label class="field">Keywords (comma-separated, dipakai auto-suggest)</label>
        <input v-model="form.keywordsCsv" type="text" placeholder="mis. warsh, hawkish, fed">
      </div>
      <div class="form-row">
        <label class="field">Bacaan Terkini (opsional, 1 kalimat)</label>
        <input v-model="form.currentRead" type="text">
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="createThread">Buat Thread</button>
      </div>
    </div>
  </section>
</template>
