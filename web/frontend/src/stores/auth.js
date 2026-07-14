import { defineStore } from 'pinia'
import { get, post } from '../lib/api'

// Session auth (Fase 3 migrasi FE) -- status disimpan client-side, tapi
// sumber kebenaran tetap Flask session cookie (/api/auth/status baca ulang
// tiap app start / route guard, bukan cuma percaya state lokal).
export const useAuthStore = defineStore('auth', {
  state: () => ({
    authenticated: false,
    passwordConfigured: true,
    checked: false,
  }),
  actions: {
    async checkStatus() {
      const r = await get('/api/auth/status')
      this.authenticated = r.authenticated
      this.passwordConfigured = r.password_configured
      this.checked = true
    },
    async login(password) {
      const r = await post('/api/auth/login', { password })
      if (r.error) throw new Error(r.error)
      this.authenticated = true
    },
    async logout() {
      await post('/api/auth/logout', {})
      this.authenticated = false
    },
  },
})
