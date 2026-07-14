<script setup>
import { ref, onMounted } from 'vue'
import Column from 'primevue/column'
import DataTable from '../components/DataTable.vue'
import { get } from '../lib/api'
import { LENS_LABELS } from '../lib/format'

// Port dari web/static/js/panel7.js (lihat docs/migrationFE.md Fase 2).
const activeSub = ref('synthesis')
const subtabs = [
  { key: 'synthesis', label: 'Synthesis' },
  { key: 'prediksi', label: 'Prediksi' },
  { key: 'journal', label: 'Trading Journal' },
  { key: 'lensa', label: '4 Lensa' },
]

const synthesisLog = ref([])
const predictions = ref([])
const journal = ref([])
const lensaHistory = ref([])
const loading = ref(true)

function outcomeSeverity(outcome) {
  if (outcome === 'BENAR') return 'LOW'
  if (outcome === 'SALAH') return 'HIGH'
  return 'MED'
}

onMounted(async () => {
  const [s, p, j, l] = await Promise.all([
    get('/api/synthesis/log'), get('/api/predictions'),
    get('/api/journal'), get('/api/reading/history'),
  ])
  synthesisLog.value = s
  predictions.value = p
  journal.value = j
  lensaHistory.value = l
  loading.value = false
})
</script>

<template>
  <div class="subtabs">
    <button
      v-for="t in subtabs" :key="t.key"
      :class="{ active: activeSub === t.key }" @click="activeSub = t.key"
    >{{ t.label }}</button>
  </div>

  <div v-if="activeSub === 'synthesis'" class="subpanel active">
    <section>
      <h2>Riwayat Synthesis Harian</h2>
      <div class="panel">
        <p v-if="loading" class="src">Memuat...</p>
        <DataTable v-else :rows="synthesisLog" :searchFields="['notes']" emptyMessage="belum ada synthesis tersimpan">
          <Column field="date" header="Tanggal" sortable><template #body="{ data }"><span class="src">{{ data.date }}</span></template></Column>
          <Column field="notes" header="Synthesis" />
          <Column field="created_at" header="Disimpan" sortable><template #body="{ data }"><span class="src">{{ data.created_at || '' }}</span></template></Column>
        </DataTable>
      </div>
    </section>
  </div>

  <div v-if="activeSub === 'prediksi'" class="subpanel active">
    <section>
      <h2>Jurnal Prediksi (track record)</h2>
      <div class="panel">
        <p v-if="loading" class="src">Memuat...</p>
        <DataTable v-else :rows="predictions" :searchFields="['claim', 'basis', 'lesson']" emptyMessage="belum ada prediksi">
          <Column field="date_made" header="Dibuat" sortable><template #body="{ data }"><span class="src">{{ data.date_made }}</span></template></Column>
          <Column field="target_date" header="Target" sortable><template #body="{ data }"><span class="src">{{ data.target_date }}</span></template></Column>
          <Column field="claim" header="Claim" />
          <Column field="horizon" header="Horizon" sortable><template #body="{ data }"><span class="src">{{ data.horizon }}</span></template></Column>
          <Column field="confidence" header="Conf" sortable><template #body="{ data }"><span class="src">{{ data.confidence ?? '-' }}%</span></template></Column>
          <Column field="outcome" header="Hasil" sortable>
            <template #body="{ data }">
              <span v-if="data.outcome" class="badge" :class="outcomeSeverity(data.outcome)">{{ data.outcome }}</span>
              <span v-else class="src">belum</span>
            </template>
          </Column>
          <Column header="Lesson"><template #body="{ data }">{{ data.lesson || '-' }}</template></Column>
        </DataTable>
      </div>
    </section>
  </div>

  <div v-if="activeSub === 'journal'" class="subpanel active">
    <section>
      <h2>Jurnal Trading (entry)</h2>
      <div class="panel">
        <p v-if="loading" class="src">Memuat...</p>
        <DataTable
          v-else :rows="journal"
          :searchFields="['instrument', 'setup_type', 'personal_notes', 'lesson_learned']"
          emptyMessage="belum ada entri trading journal"
        >
          <Column field="date" header="Tanggal" sortable><template #body="{ data }"><span class="src">{{ data.date }}</span></template></Column>
          <Column field="instrument" header="Instrument" sortable />
          <Column field="setup_type" header="Setup" sortable><template #body="{ data }"><span class="src">{{ data.setup_type || '-' }}</span></template></Column>
          <Column header="Entry/SL/TP1">
            <template #body="{ data }"><span class="src">{{ [data.entry_price, data.sl_price, data.tp1_price].map(v => v ?? '-').join(' / ') }}</span></template>
          </Column>
          <Column header="Size (Plan/Actual)">
            <template #body="{ data }">
              <span v-if="data.skip_reason" class="badge HIGH">SKIP: {{ data.skip_reason }}</span>
              <span v-else class="src">{{ data.planned_size ?? '-' }} / {{ data.actual_size ?? '-' }}</span>
            </template>
          </Column>
          <Column field="outcome" header="Outcome" sortable><template #body="{ data }">{{ data.outcome || '-' }}</template></Column>
          <Column header="Catatan"><template #body="{ data }">{{ data.personal_notes || '-' }}</template></Column>
          <Column header="Lesson"><template #body="{ data }"><span class="src">{{ data.lesson_learned || '-' }}</span></template></Column>
        </DataTable>
      </div>
    </section>
  </div>

  <div v-if="activeSub === 'lensa'" class="subpanel active">
    <section>
      <h2>Riwayat 4 Lensa (Reading)</h2>
      <div class="panel">
        <p v-if="loading" class="src">Memuat...</p>
        <DataTable v-else :rows="lensaHistory" :searchFields="['lens', 'notes']" emptyMessage="belum ada catatan reading">
          <Column field="date" header="Tanggal" sortable><template #body="{ data }"><span class="src">{{ data.date }}</span></template></Column>
          <Column field="lens" header="Lensa" sortable><template #body="{ data }">{{ LENS_LABELS[data.lens] || data.lens }}</template></Column>
          <Column field="notes" header="Catatan" />
        </DataTable>
      </div>
    </section>
  </div>
</template>
