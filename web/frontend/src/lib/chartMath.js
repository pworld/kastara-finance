// Port dari web/static/js/panel5.js::rollingMA -- versi JS dari
// analysis/indicators.py::rolling_ma (WAJIB window penuh, null kalau kurang).
// Pure function, tidak disentuh saat wrap SVG chart apa adanya (lihat
// docs/migrationFE.md Fase 2 poin 4: "bungkus apa adanya dulu").
export function rollingMA(values, period) {
  const result = []
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < period) { result.push(null); continue }
    const window = values.slice(i + 1 - period, i + 1)
    result.push(window.some((v) => v === null || v === undefined) ? null : window.reduce((a, b) => a + b, 0) / period)
  }
  return result
}
