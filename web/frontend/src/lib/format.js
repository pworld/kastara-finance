// Port dari web/static/js/core.js -- fmt/today/LANE_CLASS/LENS_LABELS.
// Dipakai lintas view, disatukan di sini spy tidak diduplikasi tiap panel
// (lihat docs/migrationFE.md peta reuse).

export function today() {
  return new Date().toISOString().slice(0, 10)
}

export function daysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

export function fmt(v) {
  if (v === null || v === undefined) return null
  if (typeof v !== 'number') return String(v)
  const abs = Math.abs(v)
  if (abs >= 1e9) return (v / 1e9).toFixed(2) + 'B'
  if (abs >= 1e6) return (v / 1e6).toFixed(2) + 'M'
  if (abs >= 1000) return v.toLocaleString('en-US', { maximumFractionDigits: 2 })
  if (abs < 1 && abs > 0) return v.toPrecision(3)
  return v.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

// 4 analisa persona -- kode (dipakai sebagai `lens` value di DB, jangan
// diubah) dipetakan ke label ANONIM (codename GEMA/LEON/AKELA/RIVAN
// sengaja tidak ditampilkan di UI) buat ditampilkan.
export const LENS_LABELS = {
  GEMA: 'Global & Capital Flow',
  LEON: 'Policy & Sistem Domestik',
  AKELA: 'Dinamika Pasar & Waktu',
  RIVAN: 'Fundamental & Realist',
  EXTERNAL_AI: 'External AI Check',
  CONFLICT: 'Conflict Notes',
}

// Badge class per lane (instrument_metadata.lane, Phase J+ Build Contract
// v1.3 §19) -- dipakai Panel 5 (badge header chart) & Panel 8 (kolom Lane).
export const LANE_CLASS = {
  TRADE: 'lane-trade', BOTH: 'lane-both', INVEST: 'lane-invest', NONE: 'lane-none',
}
