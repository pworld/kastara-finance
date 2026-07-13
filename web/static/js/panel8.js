// ---------- Panel 8: Universe & Grader (Phase J+ Build Contract v1.3 §19) ----------
function renderUniverseTable() {
  const { pageRows, total, totalPages } = applyTableControls("universe", tableCache.universe || [], {
    searchFields: ["instrument", "sector", "market"],
  });
  $("#universeBody").innerHTML = pageRows.map(r => {
    const laneClass = LANE_CLASS[r.lane] || "lane-none";
    const flags = r.integrity_flags ? (JSON.parse(r.integrity_flags) || []).length : 0;
    return `<tr>
      <td>${r.instrument}</td>
      <td class="src">${r.sector || "-"}</td>
      <td class="src">${r.market || "-"}</td>
      <td><span class="badge ${laneClass}">${r.lane || "-"}</span></td>
      <td class="src">${r.lane_validated_at || "-"}</td>
      <td class="src">${r.quadrant || "belum digrade"}</td>
      <td class="src">${r.fund_score ?? "-"}</td>
      <td class="src">${flags}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="8" class="src">belum ada instrumen di universe</td></tr>`;
  renderTableBar("universe", total, totalPages, renderUniverseTable);
}
tableRerender.universe = renderUniverseTable;

async function loadUniverse() {
  tableCache.universe = await (await fetch("/api/universe")).json();
  renderUniverseTable();
}

$("#intakeSaveBtn").addEventListener("click", async () => {
  const instrument = $("#intakeTicker").value.trim();
  if (!instrument) { toast("Ticker wajib diisi"); return; }
  const result = await postJSON("/api/intake", {
    instrument, market: $("#intakeMarket").value, sector: $("#intakeSector").value || null,
    market_cap: $("#intakeMcap").value ? Number($("#intakeMcap").value) : null,
    free_float: $("#intakeFreeFloat").value ? Number($("#intakeFreeFloat").value) : null,
    lot_size: $("#intakeLotSize").value ? Number($("#intakeLotSize").value) : null,
    lane: $("#intakeLane").value,
    is_financial: $("#intakeFinancial").checked,
    has_daily_limit: $("#intakeDailyLimit").checked,
  });
  if (result.error) { toast(result.error); return; }
  toast(`${instrument} tersimpan (lane ${result.lane})`);
  ["intakeTicker", "intakeSector", "intakeMcap", "intakeFreeFloat", "intakeLotSize"].forEach(id => $("#" + id).value = "");
  $("#intakeFinancial").checked = false;
  $("#intakeDailyLimit").checked = false;
  loadUniverse();
});

// ---------- Uji Kelayakan Kandidat (Gelombang 2, kontrak §19.3/§16) ----------
let lastGradeSnapshot = null;

$("#ujiIntegritasBtn").addEventListener("click", async () => {
  const instrument = $("#ujiTicker").value.trim();
  if (!instrument) { toast("Ticker wajib diisi"); return; }
  const result = await (await fetch(`/api/intake/integrity_check?instrument=${encodeURIComponent(instrument)}`)).json();
  const flagText = result.uma_active
    ? `<span class="badge lane-none" style="border-color:var(--high);color:var(--high)">UMA_ACTIVE</span>`
    : `<span class="badge LOW">bersih (tidak ada UMA baru-baru ini)</span>`;
  $("#ujiResult").innerHTML = `Cek Integritas ${instrument}: ${flagText} `
    + `(${result.uma_history.length} riwayat UMA ditemukan di laman)`;
});

$("#ujiGradeBtn").addEventListener("click", async () => {
  const instrument = $("#ujiTicker").value.trim();
  if (!instrument) { toast("Ticker wajib diisi"); return; }
  const result = await postJSON("/api/intake/grade", { instrument });
  if (result.error) { toast(result.error); return; }
  lastGradeSnapshot = result;
  $("#ujiResult").innerHTML = `Grade ${instrument}: score=${result.fund_score}, `
    + `kuadran=<b>${result.quadrant}</b>, flags=${JSON.stringify(result.integrity_flags)}`;
  toast(`Grade ${instrument}: ${result.quadrant}`);
  loadUniverse();
});

$("#ujiDecisionBtn").addEventListener("click", async () => {
  const instrument = $("#ujiTicker").value.trim();
  const reason = $("#ujiReason").value.trim();
  if (!instrument) { toast("Ticker wajib diisi"); return; }
  if (!reason) { toast("Alasan wajib diisi"); return; }
  const result = await postJSON("/api/intake/decision", {
    instrument, decision: $("#ujiDecision").value, reason,
    grade_snapshot: lastGradeSnapshot,
  });
  if (result.error) { toast(result.error); return; }
  toast(`Keputusan ${instrument} tercatat`);
  $("#ujiReason").value = "";
  loadIntakeLog();
});

function renderIntakeLogTable() {
  const { pageRows, total, totalPages } = applyTableControls("intakelog", tableCache.intakelog || [], {
    searchFields: ["instrument", "decision", "reason"],
  });
  $("#intakeLogBody").innerHTML = pageRows.map(r => `<tr>
    <td class="src">${r.decided_at}</td>
    <td>${r.instrument}</td>
    <td><span class="badge ${r.decision === "TOLAK" ? "HIGH" : r.decision === "WATCHLIST" ? "MED" : "LOW"}">${r.decision}</span></td>
    <td>${r.reason}</td>
  </tr>`).join("") || `<tr><td colspan="4" class="src">belum ada keputusan intake</td></tr>`;
  renderTableBar("intakelog", total, totalPages, renderIntakeLogTable);
}
tableRerender.intakelog = renderIntakeLogTable;

async function loadIntakeLog() {
  tableCache.intakelog = await (await fetch("/api/intake/log")).json();
  renderIntakeLogTable();
}

// ---------- Rasio Bank Manual (CAR/NPL/NIM/LDR, Phase J+ §2 J7/J-6) ----------
$("#bankSaveBtn").addEventListener("click", async () => {
  const instrument = $("#bankTicker").value.trim();
  const quarterEnd = $("#bankQuarterEnd").value;
  if (!instrument || !quarterEnd) { toast("Ticker & kuartal wajib diisi"); return; }
  const num = (id) => $("#" + id).value ? Number($("#" + id).value) : null;
  await postJSON("/api/fundamentals/bank_ratios", {
    instrument, quarter_end: quarterEnd,
    car: num("bankCar"), npl_gross: num("bankNpl"), nim: num("bankNim"), ldr: num("bankLdr"),
  });
  toast(`Rasio bank ${instrument} ${quarterEnd} tersimpan`);
  ["bankCar", "bankNpl", "bankNim", "bankLdr"].forEach(id => $("#" + id).value = "");
  loadBankRatios();
});

$("#bankLoadBtn").addEventListener("click", loadBankRatios);

async function loadBankRatios() {
  const instrument = $("#bankTicker").value.trim();
  if (!instrument) { toast("Isi ticker dulu"); return; }
  const rows = await (await fetch(`/api/fundamentals/bank_ratios?instrument=${encodeURIComponent(instrument)}`)).json();
  $("#bankRatiosBody").innerHTML = rows.map(r => `<tr>
    <td class="src">${r.quarter_end}</td><td>${r.car ?? "-"}</td><td>${r.npl_gross ?? "-"}</td>
    <td>${r.nim ?? "-"}</td><td>${r.ldr ?? "-"}</td><td class="src">${r.source}</td>
  </tr>`).join("") || `<tr><td colspan="6" class="src">belum ada rasio bank utk ${instrument}</td></tr>`;
}

// ---------- Detail Emiten (Komponen B, Addendum A §19.2) ----------
$("#detailLoadBtn").addEventListener("click", async () => {
  const ticker = $("#detailTicker").value.trim();
  if (!ticker) { toast("Ticker wajib diisi"); return; }
  const detail = await (await fetch(`/api/emiten/${encodeURIComponent(ticker)}`)).json();
  if (detail.error) { $("#detailResult").innerHTML = `<p class="src">${detail.error}</p>`; return; }
  const m = detail.metadata, g = detail.grade;
  let html = `<p><b>${m.instrument}</b> — ${m.sector || "-"} · ${m.market} · lane <span class="badge ${LANE_CLASS[m.lane] || "lane-none"}">${m.lane}</span></p>`;
  if (g) {
    const overrideText = g.giel_override
      ? ` <span class="badge MED">Override Giel: ${g.giel_override.quadrant} — ${g.giel_override.reason}</span>`
      : "";
    html += `<p class="src">Grade terakhir (${g.graded_at}): score=${g.fund_score}, kuadran mesin=<b>${g.quadrant}</b>${overrideText}</p>`;
    html += `<p class="src">Flags: ${g.integrity_flags.length ? g.integrity_flags.join(", ") : "tidak ada"}</p>`;
  } else {
    html += `<p class="src">Belum pernah digrade — jalankan "Uji Kelayakan" di atas dulu.</p>`;
  }
  // Playbook bank (kontrak §12.1): is_financial -> tampil CAR/NPL/NIM/LDR,
  // SEMBUNYIKAN metrik generik (revenue/OCF/FCF kurang relevan utk bank).
  const header = m.is_financial
    ? `<tr><th>Kuartal</th><th>Net Income</th><th>CAR</th><th>NPL</th><th>NIM</th><th>LDR</th><th>Confidence</th></tr>`
    : `<tr><th>Kuartal</th><th>Revenue</th><th>Net Income</th><th>OCF</th><th>FCF</th><th>Confidence</th></tr>`;
  const rows = detail.fundamentals.map(f => m.is_financial
    ? `<tr><td class="src">${f.quarter_end}</td><td>${fmt(f.net_income) ?? "-"}</td>
        <td>${f.car ?? "-"}</td><td>${f.npl_gross ?? "-"}</td><td>${f.nim ?? "-"}</td><td>${f.ldr ?? "-"}</td>
        <td class="src">${f.confidence}</td></tr>`
    : `<tr><td class="src">${f.quarter_end}</td><td>${fmt(f.revenue) ?? "-"}</td><td>${fmt(f.net_income) ?? "-"}</td>
        <td>${fmt(f.operating_cash_flow) ?? "-"}</td><td>${fmt(f.free_cash_flow) ?? "-"}</td>
        <td class="src">${f.confidence}</td></tr>`
  ).join("");
  html += `<table style="margin-top:8px"><thead>${header}</thead><tbody>${
    rows || `<tr><td colspan="7" class="src">belum ada fundamentals</td></tr>`
  }</tbody></table>`;
  $("#detailResult").innerHTML = html;
});

$("#overrideSaveBtn").addEventListener("click", async () => {
  const ticker = $("#detailTicker").value.trim();
  const reason = $("#overrideReason").value.trim();
  if (!ticker) { toast("Isi ticker di field \"Detail Emiten\" dulu"); return; }
  if (!reason) { toast("Alasan wajib diisi"); return; }
  const result = await postJSON(`/api/emiten/${encodeURIComponent(ticker)}/override`, {
    quadrant: $("#overrideQuadrant").value, reason,
  });
  if (result.error) { toast(result.error); return; }
  toast(`Override ${ticker} tersimpan`);
  $("#overrideReason").value = "";
  $("#detailLoadBtn").click();
  loadUniverse();
});

// ---------- Grader Log & Kalibrasi (Komponen D, Addendum A §19.4) ----------
function outcomeCell(row, field) {
  if (row[field]) return row[field];
  return `<select data-outcome-id="${row.id}" data-outcome-field="${field}">
    <option value="">-</option><option value="BENAR">BENAR</option>
    <option value="SALAH">SALAH</option><option value="PARTIAL">PARTIAL</option>
  </select>`;
}

function renderGraderLogTable() {
  const { pageRows, total, totalPages } = applyTableControls("graderlog", tableCache.graderlog || [], {
    searchFields: ["instrument", "reason"],
  });
  $("#graderLogBody").innerHTML = pageRows.map(r => `<tr>
    <td class="src">${r.date}</td><td>${r.instrument}</td>
    <td class="src">${r.old_grade || "-"} → ${r.new_grade}</td>
    <td>${r.reason || "-"}</td>
    <td>${outcomeCell(r, "outcome_3m")}</td>
    <td>${outcomeCell(r, "outcome_6m")}</td>
  </tr>`).join("") || `<tr><td colspan="6" class="src">belum ada grader log</td></tr>`;
  renderTableBar("graderlog", total, totalPages, renderGraderLogTable);
}
tableRerender.graderlog = renderGraderLogTable;

async function loadGraderLog() {
  tableCache.graderlog = await (await fetch("/api/grader_log")).json();
  renderGraderLogTable();
}

$("#graderLogBody").addEventListener("change", async (e) => {
  const sel = e.target.closest("[data-outcome-id]");
  if (!sel || !sel.value) return;
  await postJSON(`/api/grader_log/${sel.dataset.outcomeId}/outcome`, { [sel.dataset.outcomeField]: sel.value });
  toast("Outcome tersimpan");
  loadGraderLog();
});
