// ---------- Panel 7: Riwayat (arsip input manual) ----------
function renderSynthesisLogTable() {
  const { pageRows, total, totalPages } = applyTableControls("histsynth", tableCache.histsynth || [], {
    searchFields: ["notes"],
  });
  $("#histSynthBody").innerHTML = pageRows.map(r =>
    `<tr><td class="src">${r.date}</td><td>${r.notes}</td><td class="src">${r.created_at || ""}</td></tr>`
  ).join("") || `<tr><td colspan="3" class="src">belum ada synthesis tersimpan</td></tr>`;
  renderTableBar("histsynth", total, totalPages, renderSynthesisLogTable);
}
tableRerender.histsynth = renderSynthesisLogTable;
async function loadSynthesisLog() {
  tableCache.histsynth = await (await fetch("/api/synthesis/log")).json();
  renderSynthesisLogTable();
}

function renderPredictionsHistoryTable() {
  const { pageRows, total, totalPages } = applyTableControls("histpred", tableCache.histpred || [], {
    searchFields: ["claim", "basis", "lesson"],
  });
  $("#histPredBody").innerHTML = pageRows.map(r => {
    const outcome = r.outcome
      ? `<span class="badge ${r.outcome === "BENAR" ? "LOW" : r.outcome === "SALAH" ? "HIGH" : "MED"}">${r.outcome}</span>`
      : `<span class="src">belum</span>`;
    return `<tr><td class="src">${r.date_made}</td><td class="src">${r.target_date}</td>
      <td>${r.claim}</td><td class="src">${r.horizon}</td><td class="src">${r.confidence ?? "-"}%</td>
      <td>${outcome}</td><td class="src">${r.lesson || "-"}</td></tr>`;
  }).join("") || `<tr><td colspan="7" class="src">belum ada prediksi</td></tr>`;
  renderTableBar("histpred", total, totalPages, renderPredictionsHistoryTable);
}
tableRerender.histpred = renderPredictionsHistoryTable;
async function loadPredictionsHistory() {
  tableCache.histpred = await (await fetch("/api/predictions")).json();
  renderPredictionsHistoryTable();
}

function renderJournalHistoryTable() {
  const { pageRows, total, totalPages } = applyTableControls("histjournal", tableCache.histjournal || [], {
    searchFields: ["instrument", "setup_type", "personal_notes", "lesson_learned"],
  });
  $("#histJournalBody").innerHTML = pageRows.map(r => {
    const px = [r.entry_price, r.sl_price, r.tp1_price].map(v => v ?? "-").join(" / ");
    const size = r.skip_reason
      ? `<span class="badge HIGH">SKIP: ${r.skip_reason}</span>`
      : `${r.planned_size ?? "-"} / ${r.actual_size ?? "-"}`;
    return `<tr><td class="src">${r.date}</td><td>${r.instrument}</td><td class="src">${r.setup_type || "-"}</td>
      <td class="src">${px}</td><td class="src">${size}</td><td>${r.outcome || "-"}</td>
      <td>${r.personal_notes || "-"}</td><td class="src">${r.lesson_learned || "-"}</td></tr>`;
  }).join("") || `<tr><td colspan="8" class="src">belum ada entri trading journal</td></tr>`;
  renderTableBar("histjournal", total, totalPages, renderJournalHistoryTable);
}
tableRerender.histjournal = renderJournalHistoryTable;
async function loadJournalHistory() {
  tableCache.histjournal = await (await fetch("/api/journal")).json();
  renderJournalHistoryTable();
}

function renderLensaHistoryTable() {
  const { pageRows, total, totalPages } = applyTableControls("histlensa", tableCache.histlensa || [], {
    searchFields: ["lens", "notes"],
  });
  $("#histLensaBody").innerHTML = pageRows.map(r =>
    `<tr><td class="src">${r.date}</td><td>${LENS_LABELS[r.lens] || r.lens}</td><td>${r.notes}</td></tr>`
  ).join("") || `<tr><td colspan="3" class="src">belum ada catatan reading</td></tr>`;
  renderTableBar("histlensa", total, totalPages, renderLensaHistoryTable);
}
tableRerender.histlensa = renderLensaHistoryTable;
async function loadLensaHistory() {
  tableCache.histlensa = await (await fetch("/api/reading/history")).json();
  renderLensaHistoryTable();
}

async function loadHistory() {
  await Promise.all([
    loadSynthesisLog(), loadPredictionsHistory(), loadJournalHistory(), loadLensaHistory(),
  ]);
}
$("#historySubtabs").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  const sub = e.target.dataset.sub;
  [...$("#historySubtabs").children].forEach(b => b.classList.toggle("active", b === e.target));
  document.querySelectorAll("#tab-p7 .subpanel").forEach(p =>
    p.classList.toggle("active", p.id === "sub-" + sub));
});
