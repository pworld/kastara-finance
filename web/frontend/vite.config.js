import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

// Dev: proxy /api ke Flask (127.0.0.1:5000) -- backend TIDAK dipindah/diubah
// sama sekali, cuma dikonsumsi. Prod: web/app.py menyajikan hasil `vite build`
// (lihat docs/migrationFE.md).
//
// PWA (docs/mode_ringkas_pwa_mobile_v1.md BAGIAN B, Langkah 3, 31 Jul 2026):
// start_url `/m` -- ikon home-screen buka langsung Mode Ringkas, BUKAN
// dashboard desktop 7-tab. navigateFallbackDenylist /api biar service worker
// tidak pernah nyoba cache/serve response API dari cache (data harus selalu
// fresh dari network -- app ini bukan app offline-first, cuma installable).
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'favicon.svg', 'apple-touch-icon-180x180.png'],
      manifest: {
        name: 'Kastara Finance',
        short_name: 'Kastara',
        description: 'Habit engine harian: prediksi, berita, thread, jurnal posisi.',
        start_url: '/m',
        scope: '/',
        display: 'standalone',
        background_color: '#0e1117',
        theme_color: '#0e1117',
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
