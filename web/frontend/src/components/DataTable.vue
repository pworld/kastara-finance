<script setup>
import { ref, watch } from 'vue'
import PDataTable from 'primevue/datatable'
import { FilterMatchMode } from '@primevue/core/api'

// Menggantikan core.js: applyTableControls() + renderTableBar() +
// tableCache/tableState/tableRerender + handler sort delegated (lihat
// docs/migrationFE.md peta reuse). Search + sort + paginate SEMUA
// client-side lewat PrimeVue DataTable bawaan -- kolom didefinisikan slot
// oleh tiap view (<DataTable :rows="rows" :search-fields="[...]">
//   <Column field="x" header="X" sortable />
// </DataTable>), sama seperti pemakaian PrimeVue DataTable biasa.

const props = defineProps({
  rows: { type: Array, required: true },
  searchFields: { type: Array, default: () => [] },
  pageSize: { type: Number, default: 20 },
  emptyMessage: { type: String, default: 'Tidak ada data' },
  dataKey: { type: String, default: undefined },
})

const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } })
const search = ref('')
watch(search, (v) => { filters.value.global.value = v })
</script>

<template>
  <div class="tbl-bar">
    <input v-model="search" type="text" class="tbl-search" placeholder="Cari..." style="width:200px">
  </div>
  <PDataTable
    v-bind="$attrs"
    :value="props.rows"
    :filters="filters"
    :globalFilterFields="props.searchFields"
    paginator :rows="props.pageSize"
    :rowsPerPageOptions="[10, 20, 50, 100]"
    removableSort
    :dataKey="props.dataKey"
    tableStyle="width: 100%"
  >
    <template #empty>{{ props.emptyMessage }}</template>
    <slot />
  </PDataTable>
</template>

<style scoped>
.tbl-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
</style>
