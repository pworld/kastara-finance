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
