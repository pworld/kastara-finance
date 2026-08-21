<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Dialog from 'primevue/dialog'
import { get, post } from '../lib/api'
import { THREAD_STATUS_CLASS, LINK_STATUS_CLASS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'
import { preserveScroll } from '../composables/useScrollPreserve'

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

// preserveScroll: saveThreadEdit/confirmLink/rejectLink/toggleMilestone/
// addManualLink semua panggil ulang loadThread() stlh POST -- tanpa ini,
// timeline & ringkasan kepala thread re-render penuh & scroll lompat ke
// atas. Aman dibungkus di definisi (cuma dipanggil onMounted + handler
// save/aksi, tidak ada filter watch yang manggil fungsi load ini).
const loadThread = preserveScroll(async function loadThread() {
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
})
onMounted(loadThread)

const confirmedLinks = computed(() => (thread.value?.links || []).filter((l) => l.link_status === 'CONFIRMED'))
const suggestedLinks = computed(() => (thread.value?.links || []).filter((l) => l.link_status === 'SUGGESTED'))

// ---------- Tab, biar tidak satu halaman panjang -- pola sama UniverseView.vue
// (activeTab ref + array label), tapi computed krn label pakai hitungan
// yang berubah (jumlah saran/link/opini). ----------
const activeTab = ref('ringkasan')
const TABS = computed(() => [
  { id: 'ringkasan', label: 'Ringkasan' },
  { id: 'saran', label: `Saran${suggestedLinks.value.length ? ` (${suggestedLinks.value.length})` : ''}` },
  { id: 'timeline', label: `Timeline${confirmedLinks.value.length ? ` (${confirmedLinks.value.length})` : ''}` },
  { id: 'opini', label: `Opini Sekunder${opinions.value.length ? ` (${opinions.value.length})` : ''}` },
  { id: 'manual', label: 'Tautkan Manual' },
])

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

// ---------- Readability F-2 (§24.4): filter + milestone toggle + grup
// bulanan collapsible. Filter murni client-side (data sudah dimuat penuh
// lewat list_thread_links, jumlah link per thread masih kecil di praktik) --
// filter SEMENTARA (bukan kategori permanen), tidak mengubah data. ----------
const filterStance = ref('ALL')
const filterMilestoneOnly = ref(false)
const filterBackfillOnly = ref(false)
const filterTag = ref('ALL')

const availableTags = computed(() => {
  const set = new Set()
  for (const l of confirmedLinks.value) for (const t of (l.tags || [])) set.add(t)
  return Array.from(set).sort()
})

const filteredConfirmedLinks = computed(() => confirmedLinks.value.filter((l) => {
  if (filterStance.value !== 'ALL' && l.stance !== filterStance.value) return false
  if (filterMilestoneOnly.value && !l.is_milestone) return false
  if (filterBackfillOnly.value && !l.is_backfill) return false
  if (filterTag.value !== 'ALL' && !(l.tags || []).includes(filterTag.value)) return false
  return true
}))

function monthKeyOf(l) {
  const d = l.source_info?.date || l.linked_at || ''
  return d.slice(0, 7) || 'tanggal tidak diketahui'
}

// Grup bulanan (Lapis 3, §24.4) -- mempertahankan urutan waktu, memampatkan
// periode sepi. TIDAK ada judul naratif per bulan (butuh tulisan manual
// Giel per periode, sengaja belum dibangun -- lihat catatan ROADMAP).
const monthGroups = computed(() => {
  const groups = {}
  for (const l of filteredConfirmedLinks.value) {
    const key = monthKeyOf(l)
    ;(groups[key] ||= []).push(l)
  }
  return Object.keys(groups).sort().map((key) => {
    const links = groups[key]
    const composition = { MENDUKUNG: 0, KONTRA: 0, NETRAL: 0 }
    for (const l of links) if (composition[l.stance] !== undefined) composition[l.stance]++
    return { key, links, composition }
  })
})
const latestMonthKey = computed(() => {
  const groups = monthGroups.value
  return groups.length ? groups[groups.length - 1].key : null
})

async function toggleMilestone(link) {
  await post(`/api/threads/link/${link.id}/milestone`, { is_milestone: !link.is_milestone })
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

// ---------- Opini Sekunder (Addendum F §24, F-1) -- LAPISAN TERPISAH dari
// timeline (F1: tidak pernah dihitung ke komposisi stance thread) ----------
const opinions = ref([])
const opinionForm = ref({
  source_type: 'VIDEO', source_ref: '', author: '', my_summary: '', core_claim: '',
  testable: 'TESTABLE', my_stance: '', conflict_of_interest: '', relation_to_view: '',
})

const loadOpinions = preserveScroll(async function loadOpinions() {
  opinions.value = await get(`/api/secondary_opinions?thread_id=${threadId}`)
})
onMounted(loadOpinions)

async function addOpinion() {
  const body = { ...opinionForm.value, thread_id: Number(threadId) }
  const result = await post('/api/secondary_opinions', body)
  if (result.error) { toast(result.error); return }
  toast('Opini sekunder disimpan')
  opinionForm.value = {
    source_type: 'VIDEO', source_ref: '', author: '', my_summary: '', core_claim: '',
    testable: 'TESTABLE', my_stance: '', conflict_of_interest: '', relation_to_view: '',
  }
  loadOpinions()
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
    </section>

    <div class="tab-bar">
      <button
        v-for="t in TABS" :key="t.id" class="tab-btn" :class="{ active: activeTab === t.id }"
        @click="activeTab = t.id"
      >{{ t.label }}</button>
    </div>

    <template v-if="activeTab === 'ringkasan'">
    <section>
      <div class="panel">
        <p v-if="thread.description" class="src">{{ thread.description }}</p>
        <p>
          <span class="badge" :class="THREAD_STATUS_CLASS[thread.status]">{{ thread.status }}</span>
          <span v-if="thread.current_read" style="margin-left:8px">{{ thread.current_read }}</span>
        </p>
        <p v-if="thread.status === 'CLOSED' && thread.verdict" class="src">Verdict: {{ thread.verdict }}</p>
        <p class="src">Keywords: {{ (thread.keywords || []).join(', ') || '-' }}</p>

        <!-- Blok ringkasan kepala thread, F-2 §24.4 Lapis 1 -- paling
             berdampak, seringkali daftarnya tidak perlu dibaca sama sekali. -->
        <div class="panel" style="margin-top:12px;background:var(--bg-alt,rgba(255,255,255,.03))">
          <p>
            Bukti: {{ thread.composition?.MENDUKUNG || 0 }} MENDUKUNG ·
            {{ thread.composition?.KONTRA || 0 }} KONTRA ·
            {{ thread.composition?.NETRAL || 0 }} NETRAL
            <span v-if="thread.milestone_count"> · {{ thread.milestone_count }} milestone ★</span>
          </p>
          <p>
            Tren 30 hari: {{ thread.trend_30d?.MENDUKUNG || 0 }} MENDUKUNG ·
            {{ thread.trend_30d?.KONTRA || 0 }} KONTRA ·
            {{ thread.trend_30d?.NETRAL || 0 }} NETRAL
            <span v-if="thread.shift_warning" style="color:var(--danger,#e05252)"> ⚠ komposisi bergeser</span>
          </p>
          <p v-if="thread.opinions?.total">
            Opini sekunder: {{ thread.opinions.total }}
            ({{ thread.opinions.sejalan }} sejalan · {{ thread.opinions.menantang }} menantang<span v-if="thread.opinions.unclassified"> · {{ thread.opinions.unclassified }} belum diklasifikasi</span>)
            <span class="src">— terpisah, tidak masuk hitungan bukti</span>
          </p>
          <p v-if="thread.pending_suggested" class="src">{{ thread.pending_suggested }} saran belum dikonfirmasi</p>
          <p class="src">Umur thread: {{ thread.age_days }} hari · Terakhir diperbarui: {{ thread.updated_at }}</p>
        </div>

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
    </template>

    <template v-if="activeTab === 'saran'">
    <section>
      <h2>Saran Belum Dikonfirmasi</h2>
      <div class="panel">
        <p v-if="!suggestedLinks.length" class="src">belum ada saran</p>
        <div v-for="l in suggestedLinks" :key="l.id" class="empty-inline" style="margin-bottom:6px">
          <span class="badge" :class="LINK_STATUS_CLASS.SUGGESTED">SUGGESTED</span>
          <span style="margin-left:8px">
            {{ l.source_info?.date }} ·
            <a v-if="l.source_info?.url" :href="l.source_info.url" target="_blank" rel="noopener">{{ l.source_info?.headline }}</a>
            <span v-else>{{ l.source_info?.headline }}</span>
          </span>
          <button class="btn small secondary" @click="openStanceDialog(l)">Konfirmasi</button>
          <button class="btn small danger" @click="rejectLink(l)">Tolak</button>
        </div>
      </div>
    </section>
    </template>

    <template v-if="activeTab === 'timeline'">
    <section>
      <h2>Timeline (link CONFIRMED)</h2>
      <div class="panel">
        <!-- Filter, BUKAN kategori permanen (§24.4) -- sementara, tidak
             mengubah struktur data. -->
        <div class="form-grid" style="margin-bottom:12px">
          <div>
            <label class="field">Stance</label>
            <select v-model="filterStance">
              <option value="ALL">Semua</option>
              <option value="MENDUKUNG">MENDUKUNG</option>
              <option value="KONTRA">KONTRA</option>
              <option value="NETRAL">NETRAL</option>
            </select>
          </div>
          <div v-if="availableTags.length">
            <label class="field">Tag</label>
            <select v-model="filterTag">
              <option value="ALL">Semua</option>
              <option v-for="t in availableTags" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
          <div>
            <label class="field">&nbsp;</label>
            <label class="empty-inline"><input type="checkbox" v-model="filterMilestoneOnly"> Milestone saja</label>
          </div>
          <div>
            <label class="field">&nbsp;</label>
            <label class="empty-inline"><input type="checkbox" v-model="filterBackfillOnly"> Dari backfill saja</label>
          </div>
        </div>

        <p v-if="!filteredConfirmedLinks.length" class="src">belum ada link CONFIRMED yang cocok filter</p>

        <!-- Grup bulanan collapsible, Lapis 3 §24.4 -- urutan waktu
             dipertahankan, bulan lama terlipat, bulan terbaru terbuka. -->
        <details v-for="g in monthGroups" :key="g.key" class="collapsible" :open="g.key === latestMonthKey" style="margin-bottom:8px">
          <summary>
            {{ g.key }} — {{ g.links.length }} tautan ·
            {{ g.composition.MENDUKUNG }}🟢 {{ g.composition.KONTRA }}🔴 {{ g.composition.NETRAL }}⚪
          </summary>
          <div v-for="l in g.links" :key="l.id" style="padding:10px 0;border-bottom:1px solid var(--border)">
            <span class="src">{{ l.source_info?.date }} · {{ l.ref_table }} · {{ l.source_info?.source || '-' }}</span>
            <span class="badge" :class="LINK_STATUS_CLASS.CONFIRMED" style="margin-left:8px">{{ l.stance }}</span>
            <button class="btn small" :class="{ secondary: !l.is_milestone }" style="margin-left:8px" @click="toggleMilestone(l)" :title="l.is_milestone ? 'Lepas milestone' : 'Tandai milestone'">★</button>
            <div style="margin-top:4px">
              <a v-if="l.source_info?.url" :href="l.source_info.url" target="_blank" rel="noopener">{{ l.source_info?.headline }}</a>
              <span v-else>{{ l.source_info?.headline }}</span>
            </div>
            <div v-if="l.tags?.length" class="src" style="margin-top:2px">Tag: {{ l.tags.join(', ') }}</div>
            <div v-if="l.is_backfill" class="src" style="margin-top:2px">(dari backfill)</div>
            <div v-if="l.note" class="src" style="margin-top:2px">{{ l.note }}</div>
          </div>
        </details>
      </div>
    </section>
    </template>

    <template v-if="activeTab === 'opini'">
    <section>
      <h2>Opini Sekunder</h2>
      <div class="panel">
        <p class="src">Destilasi Giel dari sumber luar (video/buku/paper/podcast) -- lapisan terpisah, TIDAK PERNAH masuk hitungan komposisi stance thread di atas.</p>
        <p v-if="!opinions.length" class="src">belum ada opini sekunder untuk thread ini</p>
        <div v-for="o in opinions" :key="o.id" style="padding:10px 0;border-bottom:1px solid var(--border)">
          <span class="src">{{ o.created_at }} · {{ o.source_type }} · {{ o.source_ref }}<span v-if="o.author"> · {{ o.author }}</span></span>
          <span class="badge" style="margin-left:8px">{{ o.testable }}</span>
          <span v-if="o.relation_to_view" class="badge" style="margin-left:8px">{{ o.relation_to_view }}</span>
          <div style="margin-top:4px"><strong>{{ o.core_claim }}</strong></div>
          <div class="src" style="margin-top:2px">{{ o.my_summary }}</div>
          <div v-if="o.my_stance" class="src" style="margin-top:2px">Pandangan Giel: {{ o.my_stance }}</div>
          <div v-if="o.conflict_of_interest" class="src" style="margin-top:2px">Conflict of interest: {{ o.conflict_of_interest }}</div>
        </div>

        <details class="collapsible" style="margin-top:12px">
          <summary>Tambah opini sekunder</summary>
          <div class="form-grid" style="margin-top:8px">
            <div>
              <label class="field">Tipe Sumber</label>
              <select v-model="opinionForm.source_type">
                <option value="VIDEO">VIDEO</option>
                <option value="BOOK">BOOK</option>
                <option value="PAPER">PAPER</option>
                <option value="PODCAST">PODCAST</option>
                <option value="REPORT">REPORT</option>
                <option value="OTHER">OTHER</option>
              </select>
            </div>
            <div><label class="field">Sumber (URL/judul)</label><input v-model="opinionForm.source_ref" type="text"></div>
            <div><label class="field">Author (opsional)</label><input v-model="opinionForm.author" type="text"></div>
            <div>
              <label class="field">Testable</label>
              <select v-model="opinionForm.testable">
                <option value="TESTABLE">TESTABLE</option>
                <option value="SPEKULATIF">SPEKULATIF</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <label class="field">Klaim Inti (satu kalimat)</label>
            <input v-model="opinionForm.core_claim" type="text">
          </div>
          <div class="form-row">
            <label class="field">Ringkasan (destilasi sendiri, bukan transkrip)</label>
            <textarea v-model="opinionForm.my_summary"></textarea>
          </div>
          <div class="form-row">
            <label class="field">Pandangan Giel (setuju/tidak + kenapa, opsional)</label>
            <textarea v-model="opinionForm.my_stance"></textarea>
          </div>
          <div class="form-row">
            <label class="field">Conflict of Interest (opsional)</label>
            <input v-model="opinionForm.conflict_of_interest" type="text">
          </div>
          <div class="form-row">
            <label class="field">Relasi thd Pandangan Giel (opsional, dipakai ringkasan kepala thread)</label>
            <select v-model="opinionForm.relation_to_view">
              <option value="">Belum diklasifikasi</option>
              <option value="SEJALAN">SEJALAN</option>
              <option value="MENANTANG">MENANTANG</option>
            </select>
          </div>
          <div class="form-row" style="margin-top:8px">
            <button class="btn small" @click="addOpinion">Simpan</button>
          </div>
        </details>
      </div>
    </section>
    </template>

    <template v-if="activeTab === 'manual'">
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
    </template>

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

<style scoped>
.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--muted);
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.tab-btn:hover {
  color: var(--text);
}
.tab-btn.active {
  color: var(--text);
  border-bottom-color: var(--accent);
}
</style>
