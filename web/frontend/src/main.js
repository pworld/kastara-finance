import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import 'primeicons/primeicons.css'

import './style.css'
import App from './App.vue'
import router from './router'

// Dashboard lama SELALU dark (dashboard.css tidak punya mode terang sama
// sekali) -- PrimeVue butuh class ini di ancestor supaya preset dark-nya
// aktif (darkModeSelector di bawah), tanpa ini semua komponen PrimeVue
// (DataTable dkk) jatuh ke tema terang bawaan -> background putih.
document.documentElement.classList.add('app-dark')

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.app-dark',
    },
  },
})
app.use(ToastService)
app.use(ConfirmationService)

app.mount('#app')
