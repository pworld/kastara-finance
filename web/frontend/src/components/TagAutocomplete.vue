<script setup>
import { ref, onMounted } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import { get, post } from '../lib/api'
import { FACET_COLOR, FACET_LABELS } from '../lib/format'
import { useAppToast } from '../composables/useAppToast'

// Faceted Tagging (Addendum C §21.3) -- input tunggal + autocomplete grouped
// by facet, "+ buat tag baru" sebagai baris terakhir dropdown. Komponen ini
// MURNI cari & (kalau perlu) buat entri kamus -- TIDAK memutuskan sendiri
// "apply ke konten mana". Parent yang panggil apply_tag() lewat event
// `select`, supaya reusable lintas konteks (tag per-baris berita, filter
// bar, retroaktif) tanpa hardcode ref_table/ref_id di sini.
const { toast } = useAppToast()

const props = defineProps({
  placeholder: { type: String, default: 'cari/tambah tag (facet:value)...' },
  excludeCanonicals: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])

const query = ref('')
const suggestions = ref([])
const allTags = ref([])

async function loadTags() {
  allTags.value = await get('/api/tags')
}
onMounted(loadTags)

function search(event) {
  const q = (event.query || '').trim().toLowerCase()
  const matched = allTags.value.filter((t) => {
    if (props.excludeCanonicals.includes(t.canonical)) return false
    if (!q) return true
    return t.canonical.includes(q) || (t.aliases || []).some((a) => a.includes(q))
  })
  const byFacet = {}
  for (const t of matched) {
    (byFacet[t.facet] ||= []).push(t)
  }
  const groups = Object.entries(byFacet).map(([facet, items]) => ({
    label: FACET_LABELS[facet] || facet, items,
  }))
  // "+ buat tag baru" -- HANYA ditawarkan kalau query sudah format facet:value
  // penuh & belum ada match persis (controlled vocabulary, bukan free-text).
  if (q.includes(':') && !matched.some((t) => t.canonical === q)) {
    groups.push({ label: '+ Buat Tag Baru', items: [{ canonical: q, _isNew: true }] })
  }
  suggestions.value = groups
}

async function onSelect(event) {
  const item = event.value
  if (item._isNew) {
    const created = await post('/api/tags', { canonical: item.canonical })
    if (created.error) { toast(created.error); query.value = ''; return }
    allTags.value.push(created)
    emit('select', created)
  } else {
    emit('select', item)
  }
  query.value = ''
}
</script>

<template>
  <AutoComplete
    v-model="query" :suggestions="suggestions" @complete="search" @item-select="onSelect"
    optionLabel="canonical" optionGroupLabel="label" optionGroupChildren="items"
    :placeholder="placeholder" style="width: 220px"
  >
    <template #optiongroup="{ option }">
      <span class="src">{{ option.label }}</span>
    </template>
    <template #option="{ option }">
      <span v-if="option._isNew">+ Buat "{{ option.canonical }}"</span>
      <span v-else class="badge" :class="FACET_COLOR[option.facet]">{{ option.canonical }}</span>
    </template>
  </AutoComplete>
</template>
