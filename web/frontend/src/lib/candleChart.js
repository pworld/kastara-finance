// Extracted dari ChartView.vue (6 Agustus 2026) supaya MobileView.vue bisa
// reuse chart candlestick yang SAMA PERSIS -- tidak ada logic baru di sini,
// murni pindah fungsi + ganti closure (chartEl.value/chartMeta.value) jadi
// parameter/return value biar tidak terikat 1 komponen.
import { fmt } from './format'
import { rollingMA } from './chartMath'

// svgEl: elemen <svg> tujuan render. Return: string meta ringkasan (kosong
// kalau data kurang) -- caller yang taruh ke ref-nya sendiri.
export function drawCandleChart(svgEl, allRows, zones, sigs, visibleCount) {
  if (!svgEl) return ''
  const W = 800, H = 400
  const padL = 6, padR = 50, padT = 10, priceBottom = 270, volTop = 292, volBottom = 370, axisY = 390

  const closesFull = allRows.map((r) => r.close)
  const volumesFull = allRows.map((r) => r.volume)
  const ma50Full = rollingMA(closesFull, 50)
  const ma100Full = rollingMA(closesFull, 100)
  const ma200Full = rollingMA(closesFull, 200)
  const volMaFull = rollingMA(volumesFull, 20)

  const startIdx = Math.max(0, allRows.length - visibleCount)
  const rows = allRows.slice(startIdx)
  const ma50 = ma50Full.slice(startIdx), ma100 = ma100Full.slice(startIdx), ma200 = ma200Full.slice(startIdx)
  const volMa = volMaFull.slice(startIdx)

  const valid = rows.filter((r) => r.close !== null)
  if (valid.length < 2) {
    svgEl.innerHTML = `<text x="400" y="140" fill="#8b949e" text-anchor="middle">data kurang</text>`
    return ''
  }

  let lo = Math.min(...valid.map((r) => r.low ?? r.close))
  let hi = Math.max(...valid.map((r) => r.high ?? r.close))
  ;[ma50, ma100, ma200].forEach((arr) => arr.forEach((v) => { if (v !== null) { lo = Math.min(lo, v); hi = Math.max(hi, v) } }))
  const priceMargin = (hi - lo) * 0.5 || hi * 0.5
  const relevantZones = zones.filter((z) => z.zone_upper >= lo - priceMargin && z.zone_lower <= hi + priceMargin)
  relevantZones.forEach((z) => { lo = Math.min(lo, z.zone_lower); hi = Math.max(hi, z.zone_upper) })
  const span = (hi - lo) || 1
  const n = rows.length
  const slot = (W - padL - padR) / n
  const x = (i) => padL + i * slot + slot / 2
  const y = (v) => priceBottom - ((v - lo) / span) * (priceBottom - padT)

  const maxVol = Math.max(1, ...rows.map((r) => r.volume || 0), ...volMa.filter((v) => v !== null))
  const yVol = (v) => volBottom - (v / maxVol) * (volBottom - volTop)

  let svgParts = []

  const priceTicks = 5
  for (let t = 0; t <= priceTicks; t++) {
    const v = lo + (span * t) / priceTicks
    const yy = y(v)
    svgParts.push(`<line x1="0" y1="${yy.toFixed(1)}" x2="${(W - padR + 4).toFixed(1)}" y2="${yy.toFixed(1)}" stroke="#2a313c" stroke-width="0.5"/>`)
    svgParts.push(`<text x="${(W - padR + 8).toFixed(1)}" y="${(yy + 3).toFixed(1)}" fill="#8b949e" font-size="10">${fmt(v)}</text>`)
  }

  relevantZones.forEach((z) => {
    const yTop = y(z.zone_upper), yBot = y(z.zone_lower)
    const col = z.zone_type === 'SUPPORT' ? '#3fb950' : '#f85149'
    svgParts.push(`<rect x="0" y="${yTop.toFixed(1)}" width="${W - padR}" height="${Math.max(1, yBot - yTop).toFixed(1)}" fill="${col}" opacity="0.08"/>`)
  })

  const bw = Math.max(1, slot * 0.6)
  rows.forEach((r, i) => {
    if (r.close === null) return
    const up = r.close >= r.open
    const col = up ? '#3fb950' : '#f85149'
    const cx = x(i)
    svgParts.push(`<line x1="${cx}" y1="${y(r.high).toFixed(1)}" x2="${cx}" y2="${y(r.low).toFixed(1)}" stroke="${col}" stroke-width="1"/>`)
    const bodyTop = y(Math.max(r.open, r.close)), bodyBot = y(Math.min(r.open, r.close))
    svgParts.push(`<rect x="${(cx - bw / 2).toFixed(1)}" y="${bodyTop.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1, bodyBot - bodyTop).toFixed(1)}" fill="${col}"/>`)
  })

  function maPath(arr, color) {
    let d = ''
    arr.forEach((v, i) => {
      if (v === null) return
      d += `${d === '' ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)} `
    })
    if (d) svgParts.push(`<path d="${d}" fill="none" stroke="${color}" stroke-width="1.4" opacity="0.9"/>`)
  }
  maPath(ma50, '#e3b341')
  maPath(ma100, '#a371f7')
  maPath(ma200, '#f778ba')

  const dateIndex = {}
  rows.forEach((r, i) => { dateIndex[r.date] = i })
  sigs.forEach((s) => {
    const i = dateIndex[s.date]
    if (i === undefined) return
    const cy = s.entry_price ? y(s.entry_price) : y(rows[i].close)
    const col = s.signal_type === 'BREAKOUT' ? '#3fb950' : '#4c9aff'
    const shape = s.signal_type === 'BREAKOUT'
      ? `<circle cx="${x(i).toFixed(1)}" cy="${cy.toFixed(1)}" r="4" fill="${col}"/>`
      : `<circle cx="${x(i).toFixed(1)}" cy="${cy.toFixed(1)}" r="4" fill="none" stroke="${col}" stroke-width="2"/>`
    svgParts.push(shape)
  })

  rows.forEach((r, i) => {
    if (r.volume === null || r.volume === undefined) return
    const up = r.close >= r.open
    const col = up ? '#3fb950' : '#f85149'
    const cx = x(i)
    const barTop = yVol(r.volume)
    svgParts.push(`<rect x="${(cx - bw / 2).toFixed(1)}" y="${barTop.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(1, volBottom - barTop).toFixed(1)}" fill="${col}" opacity="0.6"/>`)
  })
  let volMaPath = ''
  volMa.forEach((v, i) => {
    if (v === null) return
    volMaPath += `${volMaPath === '' ? 'M' : 'L'}${x(i).toFixed(1)},${yVol(v).toFixed(1)} `
  })
  if (volMaPath) svgParts.push(`<path d="${volMaPath}" fill="none" stroke="#4c9aff" stroke-width="1.2"/>`)

  svgParts.push(`<line x1="0" y1="${volTop - 8}" x2="${W}" y2="${volTop - 8}" stroke="#2a313c" stroke-width="1"/>`)

  const monthBoundaries = []
  let lastMonth = null
  rows.forEach((r, i) => {
    if (!r.date) return
    const ym = r.date.slice(0, 7)
    if (ym !== lastMonth) { monthBoundaries.push(i); lastMonth = ym }
  })
  const maxLabels = 9
  const step = Math.max(1, Math.ceil(monthBoundaries.length / maxLabels))
  monthBoundaries.filter((_, idx) => idx % step === 0).forEach((i) => {
    const cx = x(i)
    const d = new Date(rows[i].date + 'T00:00:00Z')
    const label = d.toLocaleDateString('id-ID', { month: 'short', year: '2-digit', timeZone: 'UTC' })
    svgParts.push(`<line x1="${cx.toFixed(1)}" y1="${volBottom}" x2="${cx.toFixed(1)}" y2="${(volBottom + 4).toFixed(1)}" stroke="#484f58" stroke-width="1"/>`)
    svgParts.push(`<text x="${cx.toFixed(1)}" y="${axisY}" fill="#8b949e" font-size="10" text-anchor="middle">${label}</text>`)
  })

  svgEl.innerHTML = svgParts.join('')
  const last = valid[valid.length - 1]
  const first = valid[0]
  const pct = ((last.close - first.close) / first.close * 100).toFixed(2)
  return `${first.date} → ${last.date} · close ${fmt(last.close)} · ${pct >= 0 ? '+' : ''}${pct}% (range) · ${relevantZones.length}/${zones.length} zona aktif (dekat harga saat ini)`
}
