// ---------- Panel 3: Forward Panel ----------
function renderEconCalendarTable() {
  const { pageRows, total, totalPages } = applyTableControls("econcal", tableCache.econcal || [], {
    searchFields: ["event_name", "country"],
  });
  const now = new Date();
  $("#calBody").innerHTML = pageRows.map(r => {
    const days = Math.ceil((new Date(r.event_date) - now) / 86400000);
    const actualCell = r.actual
      ? `${r.actual} <button class="btn small secondary" data-act="edit-actual" data-id="${r.id}">Ubah</button>`
      : `<input type="text" class="calActualInput" data-id="${r.id}" placeholder="isi setelah rilis" style="width:80px">
         <button class="btn small secondary" data-act="save-actual" data-id="${r.id}">Simpan</button>`;
    return `<tr><td>${r.event_date}</td><td class="src">${days <= 0 ? "hari ini/lewat" : "H-" + days}</td>
      <td>${r.event_name}</td><td class="src">${r.country || "-"}</td>
      <td><span class="badge ${r.importance}">${r.importance}</span></td>
      <td class="src">${r.forecast || "-"}</td><td class="src">${r.previous || "-"}</td>
      <td>${actualCell}</td></tr>`;
  }).join("") || `<tr><td colspan="8" class="src">tidak ada event mendatang</td></tr>`;
  renderTableBar("econcal", total, totalPages, renderEconCalendarTable);
}
tableRerender.econcal = renderEconCalendarTable;

async function loadEconCalendar() {
  tableCache.econcal = await (await fetch("/api/econ_calendar")).json();
  renderEconCalendarTable();
}
$("#calBody").addEventListener("click", async (e) => {
  const btn = e.target;
  const id = btn.dataset.id;
  if (!id) return;
  if (btn.dataset.act === "edit-actual") {
    const row = btn.closest("tr");
    const cell = btn.closest("td");
    cell.innerHTML = `<input type="text" class="calActualInput" data-id="${id}" style="width:80px">
      <button class="btn small secondary" data-act="save-actual" data-id="${id}">Simpan</button>`;
    return;
  }
  if (btn.dataset.act === "save-actual") {
    const input = btn.closest("td").querySelector(".calActualInput");
    const actual = input.value.trim();
    if (!actual) { toast("Actual wajib diisi"); return; }
    await postJSON("/api/econ_calendar/actual", { id: Number(id), actual });
    toast("Actual tersimpan");
    loadEconCalendar();
  }
});
// ---------- Panel 3: Expectations (Layer B, manual) ----------
async function loadExpectations() {
  const rows = await (await fetch("/api/expectations?limit=15")).json();
  $("#expBody").innerHTML = rows.map(r => `<tr>
    <td class="src">${r.date}</td><td>${r.metric}</td><td>${r.value}</td><td class="src">${r.horizon || "-"}</td>
  </tr>`).join("") || `<tr><td colspan="4" class="src">belum ada entri</td></tr>`;
}
$("#expSaveBtn").addEventListener("click", async () => {
  const value = $("#expValue").value;
  if (value === "") { toast("Value wajib diisi"); return; }
  await postJSON("/api/expectations/add", {
    date: $("#expDate").value || today(), metric: $("#expMetric").value,
    value: Number(value), horizon: $("#expHorizon").value || null, source: "manual",
  });
  toast("Expectation tersimpan");
  $("#expValue").value = ""; $("#expHorizon").value = "";
  loadExpectations();
});

// ---------- Panel 3: Positioning (Layer C, COT/ETF otomatis + manual) ----------
function renderPositioningTable() {
  const { pageRows, total, totalPages } = applyTableControls("positioning", tableCache.positioning || [], {
    searchFields: ["instrument", "metric", "source"],
  });
  $("#posBody").innerHTML = pageRows.map(r => `<tr>
    <td class="src">${r.date}</td><td>${r.instrument}</td><td>${r.metric}</td>
    <td>${fmt(r.value) ?? r.value}</td><td class="src">${r.source || "-"}</td>
  </tr>`).join("") || `<tr><td colspan="5" class="src">belum ada data</td></tr>`;
  renderTableBar("positioning", total, totalPages, renderPositioningTable);
}
tableRerender.positioning = renderPositioningTable;

async function loadPositioning() {
  tableCache.positioning = await (await fetch("/api/positioning?limit=200")).json();
  renderPositioningTable();
}
$("#posSaveBtn").addEventListener("click", async () => {
  const value = $("#posValue").value;
  const metric = $("#posMetric").value.trim();
  if (value === "" || !metric) { toast("Metric dan value wajib diisi"); return; }
  await postJSON("/api/positioning/add", {
    date: $("#posDate").value || today(), instrument: $("#posInstrument").value,
    metric, value: Number(value), source: "manual",
  });
  toast("Positioning tersimpan");
  $("#posMetric").value = ""; $("#posValue").value = "";
  loadPositioning();
});

// ---------- Panel 3: Disonansi Flag ----------
async function loadDisonansi() {
  const r = await (await fetch("/api/disonansi")).json();
  const el = $("#disonansiBody");
  if (!r.available) {
    el.className = "empty-inline";
    el.textContent = "Belum cukup data untuk dibandingkan (butuh stance_score Policy Tracker + minimal 2 baris COT DXY).";
    return;
  }
  el.className = "";
  el.innerHTML = `<span class="badge ${r.flagged ? "HIGH" : "LOW"}">${r.flagged ? "DISONANSI" : "SEARAH"}</span>
    <span class="src" style="margin-left:8px">${r.note}</span>`;
}

function renderPolicyTable() {
  const { pageRows, total, totalPages } = applyTableControls("policy", tableCache.policy || [], {
    searchFields: ["speaker", "literal_statement", "inference"],
  });
  $("#policyBody").innerHTML = pageRows.map(r => `<tr>
    <td class="src">${r.date}</td><td>${r.speaker || "-"}</td>
    <td>${(r.literal_statement || "").slice(0, 80)}</td>
    <td>${(r.inference || "").slice(0, 80)}</td>
    <td><span class="badge ${r.inference_flag === "SPEKULATIF" ? "MED" : "LOW"}">${r.inference_flag || "-"}</span></td>
  </tr>`).join("") || `<tr><td colspan="5" class="src">belum ada entri</td></tr>`;
  renderTableBar("policy", total, totalPages, renderPolicyTable);
}
tableRerender.policy = renderPolicyTable;

async function loadPolicyNotes() {
  tableCache.policy = await (await fetch("/api/policy?limit=100")).json();
  renderPolicyTable();
}
$("#polSaveBtn").addEventListener("click", async () => {
  const literal = $("#polLiteral").value.trim();
  if (!literal) { toast("Literal statement wajib diisi"); return; }
  await postJSON("/api/policy/add", {
    date: $("#polDate").value || today(), speaker: $("#polSpeaker").value,
    institution: $("#polInstitution").value, source_url: $("#polUrl").value,
    literal_statement: literal, stance_score: $("#polStance").value ? Number($("#polStance").value) : null,
    inference: $("#polInference").value, inference_flag: $("#polFlag").value,
    drift_note: $("#polDrift").value,
  });
  toast("Policy note tersimpan");
  ["polSpeaker","polInstitution","polUrl","polLiteral","polStance","polInference","polDrift"].forEach(id => $("#" + id).value = "");
  loadPolicyNotes();
});
