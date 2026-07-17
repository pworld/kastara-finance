<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Dialog from 'primevue/dialog'
import { get, post } from '../lib/api'
import { THREAD_STATUS_CLASS, LINK_STATUS_CLASS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// News Threads N-1 (Addendum B §20.5) -- timeline VERTIKAL (bukan graph),
// link CONFIRMED urut waktu, campur daily_news/manual_articles/policy_tracker.
const { toast } = useAppToast()
const route = useRoute()
const router = useRouter()
const threadId = route.params.id

const thread = ref(null)
const loading = ref(true)

// Header editable (title/current_read/status/keywords/verdict) -- refs
// di-sinkron ulang tiap loadThread() (bukan trigger event DOM) supaya
// selalu cocok dgn data server terbaru, termasuk setelah save.
const editTitle = ref('')
const editCurrentRead = ref('')
const editStatus = ref('')
const editKeywordsCsv = ref('')
const editVerdict = ref('')

async function loadThread() {
  loading.value = true
  const result = await get(`/api/threads/${threadId}`)
  if (result.error) { toast(result.error); router.push('/threads'); return }
  thread.value = result
  editTitle.value = result.title
  editCurrentRead.value = result.current_read || ''
  editStatus.value = result.status
  editKeywordsCsv.value = (result.keywords || []).join(', ')
  editVerdict.value = result.verdict || ''
  loading.value = false
}
onMounted(loadThread)

const confirmedLinks = computed(() => (thread.value?.links || []).filter((l) => l.link_status === 'CONFIRMED'))
const suggestedLinks = computed(() => (thread.value?.links || []).filter((l) => l.link_status === 'SUGGESTED'))

async function saveThreadEdit() {
  const body = {
    title: editTitle.value, current_read: editCurrentRead.value, status: editStatus.value,
    keywords: editKeywordsCsv.value.split(',').map((k) => k.trim().toLowerCase()).filter(Boolean),
  }
  if (editStatus.value === 'CLOSED') body.verdict = editVerdict.value
  const result = await post(`/api/threads/${threadId}`, body)
  if (result.error) { toast(result.error); return }
  toast('Thread diperbarui — kata kunci baru langsung di-catch-up scan ke berita 7 hari terakhir')
  loadThread()
}

// ---------- Konfirmasi/tolak SUGGESTED (sama pola NewsView, buat yang match tapi belum dikonfirmasi) ----------
const stanceDialogOpen = ref(false)
const stanceDialogLink = ref(null)
const selectedStance = ref('MENDUKUNG')

function openStanceDialog(link) {
  stanceDialogLink.value = link
  selectedStance.value = 'MENDUKUNG'
  stanceDialogOpen.value = true
}

async function confirmLink() {
  await post(`/api/threads/link/${stanceDialogLink.value.id}/confirm`, { stance: selectedStance.value })
  toast('Link dikonfirmasi')
  stanceDialogOpen.value = false
  loadThread()
}

async function rejectLink(link) {
  await post(`/api/threads/link/${link.id}/reject`, {})
  toast('Link ditolak')
  loadThread()
}

// ---------- Tautkan manual (mis. policy_tracker/manual_articles) ----------
const manual = ref({ refTable: 'manual_articles', refId: '', stance: 'MENDUKUNG', note: '' })

async function addManualLink() {
  if (!manual.value.refId) { toast('ref_id wajib diisi'); return }
  const result = await post(`/api/threads/${threadId}/links`, {
    ref_table: manual.value.refTable, ref_id: Number(manual.value.refId),
    stance: manual.value.stance, note: manual.value.note || null,
  })
  if (result.error) { toast(result.error); return }
  toast('Link manual ditambahkan')
  manual.value.refId = ''
  manual.value.note = ''
  loadThread()
}
</script>

<template>
  <section v-if="loading"><p class="src">Memuat...</p></section>
  <template v-else-if="thread">
    <section>
      <div class="chart-head" style="margin-bottom:8px">
        <button class="btn small secondary" @click="router.push('/threads')">&larr; Indeks Thread</button>
      </div>
      <h2>{{ thread.title }}</h2>
      <div class="panel">
        <p v-if="thread.description" class="src">{{ thread.description }}</p>
        <p>
          <span class="badge" :class="THREAD_STATUS_CLASS[thread.status]">{{ thread.status }}</span>
          <span v-if="thread.current_read" style="margin-left:8px">{{ thread.current_read }}</span>
        </p>
        <p v-if="thread.status === 'CLOSED' && thread.verdict" class="src">Verdict: {{ thread.verdict }}</p>
        <p class="src">Keywords: {{ (thread.keywords || []).join(', ') || '-' }}</p>

        <details class="collapsible" style="margin-top:12px">
          <summary>Edit thread</summary>
          <div class="form-row" style="margin-top:8px">
            <label class="field">Title</label>
            <input v-model="editTitle" type="text">
          </div>
          <div class="form-row">
            <label class="field">Keywords (comma-separated, dipakai auto-suggest)</label>
            <input v-model="editKeywordsCsv" type="text" placeholder="mis. warsh, fed, powell">
          </div>
          <div class="form-row">
            <label class="field">Bacaan Terkini</label>
            <input v-model="editCurrentRead" type="text">
          </div>
          <div class="form-row">
            <label class="field">Status</label>
            <select v-model="editStatus">
              <option value="ACTIVE">ACTIVE</option>
              <option value="DORMANT">DORMANT</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </div>
          <div class="form-row" v-if="editStatus === 'CLOSED'">
            <label class="field">Verdict (wajib saat menutup thread)</label>
            <textarea v-model="editVerdict"></textarea>
          </div>
          <div class="form-row" style="margin-top:8px">
            <button class="btn small" @click="saveThreadEdit">Simpan</button>
          </div>
        </details>
      </div>
    </section>

    <section v-if="suggestedLinks.length">
      <h2>Saran Belum Dikonfirmasi</h2>
      <div class="panel">
        <div v-for="l in suggestedLinks" :key="l.id" class="empty-inline" style="margin-bottom:6px">
          <span class="badge" :class="LINK_STATUS_CLASS.SUGGESTED">SUGGESTED</span>
          <span style="margin-left:8px">{{ l.source_info?.date }} · {{ l.source_info?.headline }}</span>
          <button class="btn small secondary" @click="openStanceDialog(l)">Konfirmasi</button>
          <button class="btn small danger" @click="rejectLink(l)">Tolak</button>
        </div>
      </div>
    </section>

    <section>
      <h2>Timeline (link CONFIRMED)</h2>
      <div class="panel">
        <p v-if="!confirmedLinks.length" class="src">belum ada link CONFIRMED</p>
        <div v-for="l in confirmedLinks" :key="l.id" style="padding:10px 0;border-bottom:1px solid var(--border)">
          <span class="src">{{ l.source_info?.date }} · {{ l.ref_table }} · {{ l.source_info?.source || '-' }}</span>
          <span class="badge" :class="LINK_STATUS_CLASS.CONFIRMED" style="margin-left:8px">{{ l.stance }}</span>
          <div style="margin-top:4px">
            <a v-if="l.source_info?.url" :href="l.source_info.url" target="_blank" rel="noopener">{{ l.source_info?.headline }}</a>
            <span v-else>{{ l.source_info?.headline }}</span>
          </div>
          <div v-if="l.note" class="src" style="margin-top:2px">{{ l.note }}</div>
        </div>
      </div>
    </section>

    <section>
      <h2>Tautkan Manual</h2>
      <div class="panel">
        <p class="src">Untuk sumber yang tak ter-auto-suggest (mis. entri Policy Tracker atau artikel manual) -- langsung CONFIRMED, stance sudah diketahui.</p>
        <div class="form-grid">
          <div>
            <label class="field">Sumber</label>
            <select v-model="manual.refTable">
              <option value="manual_articles">Manual Article</option>
              <option value="policy_tracker">Policy Tracker</option>
              <option value="daily_news">Daily News</option>
            </select>
          </div>
          <div><label class="field">ID (dari tabel sumber)</label><input v-model="manual.refId" type="number"></div>
          <div>
            <label class="field">Stance</label>
            <select v-model="manual.stance">
              <option value="MENDUKUNG">MENDUKUNG</option>
              <option value="KONTRA">KONTRA</option>
              <option value="NETRAL">NETRAL</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <label class="field">Note (opsional)</label>
          <input v-model="manual.note" type="text">
        </div>
        <div class="form-row" style="margin-top:8px">
          <button class="btn small" @click="addManualLink">Tautkan</button>
        </div>
      </div>
    </section>

    <Dialog v-model:visible="stanceDialogOpen" modal header="Konfirmasi Tautan" style="width:420px; max-width:90vw">
      <div class="form-row">
        <label class="field">Stance</label>
        <select v-model="selectedStance">
          <option value="MENDUKUNG">MENDUKUNG</option>
          <option value="KONTRA">KONTRA</option>
          <option value="NETRAL">NETRAL</option>
        </select>
      </div>
      <div class="form-row" style="margin-top:12px">
        <button class="btn" @click="confirmLink">Konfirmasi</button>
      </div>
    </Dialog>
  </template>
</template>
