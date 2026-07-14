<script setup>
import { ref, onMounted, watch } from 'vue'
import Column from 'primevue/column'
import DataTable from '../components/DataTable.vue'
import { get, post } from '../lib/api'
import { today, daysAgo } from '../lib/format'
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
  if (impact.value === '__KEY__') params.key_only = '1'
  else if (impact.value) params.impact = impact.value
  rows.value = await get('/api/news', params)
  loading.value = false
}
watch([dateFrom, dateTo, impact], loadNews)
onMounted(loadNews)

async function toggleKey(row) {
  const nowKey = !!row.is_key_trigger
  await post('/api/news/flag_key', { id: row.id, is_key: !nowKey })
  toast(nowKey ? 'Key trigger dilepas' : 'Ditandai key trigger')
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
          <option value="__KEY__">🚩 Key saja</option>
        </select>
      </div>
      <p v-if="loading" class="src">Memuat...</p>
      <DataTable
        v-else :rows="rows" :dataKey="'id'"
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
          </template>
        </Column>
        <Column field="source" header="Sumber" sortable>
          <template #body="{ data }"><span class="src">{{ data.source }}</span></template>
        </Column>
        <Column header="">
          <template #body="{ data }">
            <button
              class="btn small" :class="data.is_key_trigger ? 'key-on' : 'secondary'"
              @click="toggleKey(data)"
            >{{ data.is_key_trigger ? '★ Key' : '🚩 key' }}</button>
          </template>
        </Column>
      </DataTable>
    </div>
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
