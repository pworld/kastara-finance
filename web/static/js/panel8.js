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
