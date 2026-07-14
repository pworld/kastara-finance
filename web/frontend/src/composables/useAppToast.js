import { useToast } from 'primevue/usetoast'

// Menggantikan toast(msg) global di core.js (setTimeout 2200ms hide) --
// PrimeVue Toast (dipasang di App.vue, ToastService di main.js) sudah
// handle animasi show/hide sendiri, di sini cuma dipetakan ke signature
// lama yang simpel: 1 argumen pesan.
export function useAppToast() {
  const toast = useToast()
  return {
    toast: (message, severity = 'info') => {
      toast.add({ severity, summary: message, life: 2200 })
    },
  }
}
