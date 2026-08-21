import { nextTick } from 'vue'

// Bungkus fungsi async (biasanya load*()) supaya posisi scroll window
// dipertahankan lewat reload -- root cause: rows.value = await get(...)
// mengganti seluruh array reaktif, Vue re-render seluruh DataTable, browser
// reset scroll ke atas (scroll di level window/document, bukan
// sub-container -- lihat App.vue/style.css). Tangkap window.scrollY
// SEBELUM reload, pulihkan SETELAH DOM update (nextTick), bukan setTimeout.
export function preserveScroll(fn) {
  return async function (...args) {
    const y = window.scrollY
    const result = await fn.apply(this, args)
    await nextTick()
    window.scrollTo(0, y)
    return result
  }
}
