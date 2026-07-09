// ---------- Panel 5: Chart + S&R + Signals ----------
// MA rolling per-index (JS versi analysis/indicators.py::rolling_ma) --
// butuh window PENUH (None/null kalau kurang), dipakai buat MA50/100/200
// overlay + volume MA20. Dipanggil atas array PENUH (termasuk padding
// histori sebelum jendela yang ditampilkan) supaya MA200 valid sejak
// candle PALING KIRI yang kelihatan -- bukan cuma dihitung dari slice
// yang tampil saja (yang bakal all-null kalau visible < period).
function rollingMA(values, period) {
  const result = [];
  for (let i = 0; i < values.length; i++) {
    if (i + 1 < period) { result.push(null); continue; }
    const window = values.slice(i + 1 - period, i + 1);
    result.push(window.some(v => v === null || v === undefined) ? null : window.reduce((a, b) => a + b, 0) / period);
  }
  return result;
}

let CHART_VISIBLE = 90;
const CHART_PADDING = 220; // >= MA200 period, biar MA200 valid sejak candle pertama yang tampil

function drawCandleChart(allRows, zones, signals, visibleCount) {
  const svg = $("#chart");
  const W = 800, H = 400;
  const padL = 6, padR = 50, padT = 10, priceBottom = 270, volTop = 292, volBottom = 370, axisY = 390;

  const closesFull = allRows.map(r => r.close);
  const volumesFull = allRows.map(r => r.volume);
  const ma50Full = rollingMA(closesFull, 50);
  const ma100Full = rollingMA(closesFull, 100);
  const ma200Full = rollingMA(closesFull, 200);
  const volMaFull = rollingMA(volumesFull, 20);

  const startIdx = Math.max(0, allRows.length - visibleCount);
  const rows = allRows.slice(startIdx);
  const ma50 = ma50Full.slice(startIdx), ma100 = ma100Full.slice(startIdx), ma200 = ma200Full.slice(startIdx);
  const volMa = volMaFull.slice(startIdx);

  const valid = rows.filter(r => r.close !== null);
  if (valid.length < 2) {
    svg.innerHTML = `<text x="400" y="140" fill="#8b949e" text-anchor="middle">data kurang</text>`;
    $("#chartMeta").textContent = "";
    return;
  }

  let lo = Math.min(...valid.map(r => r.low ?? r.close));
  let hi = Math.max(...valid.map(r => r.high ?? r.close));
  [ma50, ma100, ma200].forEach(arr => arr.forEach(v => { if (v !== null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }));
  // sr_zones nyimpen SEMUA zona aktif sepanjang histori instrument (BTC
  // era $200-an ikut kebawa) -- kalau semua dipakai buat skala, axis jadi
  // mekar sampai jutaan dan candle yang ditampilkan keliatan gepeng.
  // Cuma zona yang "dekat" harga yang lagi ditampilkan yang dipakai buat
  // skala & digambar; zona jauh di luar rentang harga saat ini disembunyikan.
  const priceMargin = (hi - lo) * 0.5 || hi * 0.5;
  const relevantZones = zones.filter(z => z.zone_upper >= lo - priceMargin && z.zone_lower <= hi + priceMargin);
  relevantZones.forEach(z => { lo = Math.min(lo, z.zone_lower); hi = Math.max(hi, z.zone_upper); });
  const span = (hi - lo) || 1;
  const n = rows.length;
  const slot = (W - padL - padR) / n;
  const x = i => padL + i * slot + slot / 2;
  const y = v => priceBottom - ((v - lo) / span) * (priceBottom - padT);

  const maxVol = Math.max(1, ...rows.map(r => r.volume || 0), ...volMa.filter(v => v !== null));
  const yVol = v => volBottom - (v / maxVol) * (volBottom - volTop);

  let svgParts = [];

  // Sumbu harga (Y) -- gridline + label supaya angka open/close/level
  // kebaca langsung dari chart, bukan cuma dari #chartMeta.
  const priceTicks = 5;
  for (let t = 0; t <= priceTicks; t++) {
    const v = lo + (span * t) / priceTicks;
    const yy = y(v);
    svgParts.push(`<line x1="0" y1="${yy.toFixed(1)}" x2="${(W - padR + 4).toFixed(1)}" y2="${yy.toFixed(1)}" stroke="#2a313c" stroke-width="0.5"/>`);
    svgParts.push(`<text x="${(W - padR + 8).toFixed(1)}" y="${(yy + 3).toFixed(1)}" fill="#8b949e" font-size="10">${fmt(v)}</text>`);
  }

  // S&R zone bands (background area harga)
  relevantZones.forEach(z => {
    const yTop = y(z.zone_upper), yBot = y(z.zone_lower);
    const col = z.zone_type === "SUPPORT" ? "#3fb950" : "#f85149";
    svgParts.push(`<rect x="0" y="${yTop.toFixed(1)}" width="${W - padR}" height="${Math.max(1, yBot - yTop).toFixed(1)}"
      fill="${col}" opacity="0.08"/>`);
  });

  // Candles
  const bw = Math.max(1, slot * 0.6);
  rows.forEach((r, i) => {
    if (r.close === null) return;
    const up = r.close >= r.open;
    const col = up ? "#3fb950" : "#f85149";
    const cx = x(i);
    svgParts.push(`<line x1="${cx}" y1="${y(r.high).toFixed(1)}" x2="${cx}" y2="${y(r.low).toFixed(1)}" stroke="${col}" stroke-width="1"/>`);
    const bodyTop = y(Math.max(r.open, r.close)), bodyBot = y(Math.min(r.open, r.close));
    svgParts.push(`<rect x="${(cx - bw / 2).toFixed(1)}" y="${bodyTop.toFixed(1)}" width="${bw.toFixed(1)}"
      height="${Math.max(1, bodyBot - bodyTop).toFixed(1)}" fill="${col}"/>`);
  });

  // MA50/100/200 overlay
  function maPath(arr, color) {
    let d = "";
    arr.forEach((v, i) => {
      if (v === null) return;
      d += `${d === "" ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
    });
    if (d) svgParts.push(`<path d="${d}" fill="none" stroke="${color}" stroke-width="1.4" opacity="0.9"/>`);
  }
  maPath(ma50, "#e3b341");
  maPath(ma100, "#a371f7");
  maPath(ma200, "#f778ba");

  // Breakout/retest markers
  const dateIndex = {};
  rows.forEach((r, i) => dateIndex[r.date] = i);
  signals.forEach(s => {
    const i = dateIndex[s.date];
    if (i === undefined) return;
    const cy = s.entry_price ? y(s.entry_price) : y(rows[i].close);
    const col = s.signal_type === "BREAKOUT" ? "#3fb950" : "#4c9aff";
    const shape = s.signal_type === "BREAKOUT"
      ? `<circle cx="${x(i).toFixed(1)}" cy="${cy.toFixed(1)}" r="4" fill="${col}"/>`
      : `<circle cx="${x(i).toFixed(1)}" cy="${cy.toFixed(1)}" r="4" fill="none" stroke="${col}" stroke-width="2"/>`;
    svgParts.push(shape);
  });

  // Volume bars + volume MA20
  rows.forEach((r, i) => {
    if (r.volume === null || r.volume === undefined) return;
    const up = r.close >= r.open;
    const col = up ? "#3fb950" : "#f85149";
    const cx = x(i);
    const barTop = yVol(r.volume);
    svgParts.push(`<rect x="${(cx - bw / 2).toFixed(1)}" y="${barTop.toFixed(1)}" width="${bw.toFixed(1)}"
      height="${Math.max(1, volBottom - barTop).toFixed(1)}" fill="${col}" opacity="0.6"/>`);
  });
  let volMaPath = "";
  volMa.forEach((v, i) => {
    if (v === null) return;
    volMaPath += `${volMaPath === "" ? "M" : "L"}${x(i).toFixed(1)},${yVol(v).toFixed(1)} `;
  });
  if (volMaPath) svgParts.push(`<path d="${volMaPath}" fill="none" stroke="#4c9aff" stroke-width="1.2"/>`);

  svgParts.push(`<line x1="0" y1="${volTop - 8}" x2="${W}" y2="${volTop - 8}" stroke="#2a313c" stroke-width="1"/>`);

  // Penanda tanggal/bulan di sumbu bawah -- ambil titik pergantian bulan,
  // lalu di-thin kalau kepadatan tinggi (misal filter "Semua" ~4300 candle)
  // supaya label tidak numpuk.
  const monthBoundaries = [];
  let lastMonth = null;
  rows.forEach((r, i) => {
    if (!r.date) return;
    const ym = r.date.slice(0, 7);
    if (ym !== lastMonth) { monthBoundaries.push(i); lastMonth = ym; }
  });
  const maxLabels = 9;
  const step = Math.max(1, Math.ceil(monthBoundaries.length / maxLabels));
  monthBoundaries.filter((_, idx) => idx % step === 0).forEach(i => {
    const cx = x(i);
    const d = new Date(rows[i].date + "T00:00:00Z");
    const label = d.toLocaleDateString("id-ID", { month: "short", year: "2-digit", timeZone: "UTC" });
    svgParts.push(`<line x1="${cx.toFixed(1)}" y1="${volBottom}" x2="${cx.toFixed(1)}" y2="${(volBottom + 4).toFixed(1)}" stroke="#484f58" stroke-width="1"/>`);
    svgParts.push(`<text x="${cx.toFixed(1)}" y="${axisY}" fill="#8b949e" font-size="10" text-anchor="middle">${label}</text>`);
  });

  svg.innerHTML = svgParts.join("");
  const last = valid[valid.length - 1];
  const first = valid[0];
  const pct = ((last.close - first.close) / first.close * 100).toFixed(2);
  $("#chartMeta").textContent =
    `${first.date} → ${last.date} · close ${fmt(last.close)} · ${pct >= 0 ? "+" : ""}${pct}% (range) · ${relevantZones.length}/${zones.length} zona aktif (dekat harga saat ini)`;
}

async function loadChart() {
  const inst = $("#instrument").value;
  const [rows, zones, signals] = await Promise.all([
    fetch(`/api/asset_ohlcv?instrument=${encodeURIComponent(inst)}&limit=${CHART_VISIBLE + CHART_PADDING}`).then(r => r.json()),
    fetch(`/api/sr_zones?instrument=${encodeURIComponent(inst)}`).then(r => r.json()),
    fetch(`/api/signals?instrument=${encodeURIComponent(inst)}`).then(r => r.json()),
  ]);
  drawCandleChart(rows, zones, signals, CHART_VISIBLE);
  renderSignalsTable(signals);
}

// ---------- Context mini-charts (30 hari, independen instrument) ----------
function drawMiniLine(svg, values) {
  const W = 300, H = 100, pad = 6;
  const points = values.map((v, i) => ({ v, i })).filter(o => o.v !== null && o.v !== undefined);
  if (points.length < 2) {
    svg.innerHTML = `<text x="150" y="50" fill="#8b949e" text-anchor="middle" font-size="11">data kurang</text>`;
    return;
  }
  const vals = points.map(o => o.v);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const span = (hi - lo) || 1;
  const n = values.length;
  const x = i => pad + (n === 1 ? 0 : (i / (n - 1)) * (W - 2 * pad));
  const y = v => H - pad - ((v - lo) / span) * (H - 2 * pad);
  let d = "";
  points.forEach(({ v, i }) => { d += `${d === "" ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)} `; });
  const up = vals[vals.length - 1] >= vals[0];
  svg.innerHTML = `<path d="${d}" fill="none" stroke="${up ? "#3fb950" : "#f85149"}" stroke-width="1.6"/>`;
}

async function loadContextCharts() {
  const rows = await (await fetch("/api/daily_market?limit=30")).json();
  const ordered = [...rows].reverse(); // API balikin DESC, chart butuh ASC
  document.querySelectorAll(".ctx-chart").forEach(svg => {
    drawMiniLine(svg, ordered.map(r => r[svg.dataset.ctx]));
  });
}

function renderSignalsTable(signals) {
  tableCache.signals = signals;
  getTableState("signals").page = 1;
  drawSignalsPage();
}
function drawSignalsPage() {
  const { pageRows, total, totalPages } = applyTableControls("signals", tableCache.signals || [], {
    searchFields: ["date", "signal_type"],
  });
  $("#signalsBody").innerHTML = pageRows.map(s => {
    const status = s.approved ? "APPROVED" : (s.notes ? "REJECTED" : "pending");
    const badgeClass = status === "APPROVED" ? "LOW" : (status === "REJECTED" ? "HIGH" : "MED");
    const priceStr = s.entry_price
      ? `${fmt(s.entry_price)} / ${fmt(s.sl_price)} / ${fmt(s.tp1_price)}` : "-";
    const rr = s.rr_ratio ? s.rr_ratio.toFixed(2) : "-";
    const actions = status === "pending"
      ? `<button class="btn small secondary" data-act="approve" data-id="${s.id}">Approve</button>
         <button class="btn small danger" data-act="reject" data-id="${s.id}">Reject</button>`
      : `<span class="badge ${badgeClass}">${status}</span>`;
    return `<tr>
      <td class="src">${s.date}</td><td><span class="badge ${s.signal_type}">${s.signal_type}</span></td>
      <td>${priceStr}</td><td>${rr}</td>
      <td>${status === "pending" ? `<span class="badge ${badgeClass}">${status}</span>` : ""}</td>
      <td>${actions}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="6" class="src">belum ada sinyal untuk instrument ini</td></tr>`;
  renderTableBar("signals", total, totalPages, drawSignalsPage);
}
tableRerender.signals = drawSignalsPage;
$("#signalsBody").addEventListener("click", async (e) => {
  const act = e.target.dataset.act;
  if (!act) return;
  const id = e.target.dataset.id;
  let notes = null;
  if (act === "reject") notes = prompt("Alasan reject (opsional):") || "";
  await postJSON("/api/signals/review", { id: Number(id), approved: act === "approve", notes });
  toast(act === "approve" ? "Sinyal di-approve" : "Sinyal di-reject");
  loadChart();
});

async function loadAssets() {
  const list = await (await fetch("/api/assets")).json();
  const sel = $("#instrument");
  sel.innerHTML = list.map(i => `<option>${i}</option>`).join("");
  if (list.includes("BTC")) sel.value = "BTC";
  if (list.length) await loadChart();
}
$("#instrument").addEventListener("change", loadChart);
$("#chartRangeSelect").addEventListener("change", (e) => {
  CHART_VISIBLE = Number(e.target.value);
  loadChart();
});
