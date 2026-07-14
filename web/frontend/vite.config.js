import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Dev: proxy /api ke Flask (127.0.0.1:5000) -- backend TIDAK dipindah/diubah
// sama sekali, cuma dikonsumsi. Prod: web/app.py menyajikan hasil `vite build`
// (lihat docs/migrationFE.md).
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
