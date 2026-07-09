// ---------- Panel 4: Reading Workspace ----------
async function loadKeyNews() {
  const rows = await (await fetch(`/api/news?date=${today()}&key_only=1&limit=50`)).json();
  $("#keyNewsBody").innerHTML = rows.length
    ? `<table><thead><tr><th>Impact</th><th>Headline</th><th>Sumber</th></tr></thead><tbody>` +
      rows.map(r => {
        const link = r.raw_url
          ? `<a href="${r.raw_url}" target="_blank" rel="noopener">${r.headline}</a>` : r.headline;
        return `<tr><td><span class="badge ${r.impact_level}">${r.impact_level}</span></td>
          <td>${link}</td><td class="src">${r.source}</td></tr>`;
      }).join("") + `</tbody></table>`
    : `<div class="empty-inline">belum ada berita yang di-flag key hari ini — flag di Panel 2 (News) dulu.</div>`;
}

$("#readingSaveBtn").addEventListener("click", async () => {
  const r = await postJSON("/api/reading/save", {
    date: today(), external_ai: $("#lensExternalAi").value, conflict: $("#lensConflict").value,
  });
  toast(`${r.ids.length} catatan tersimpan`);
});

// ---------- Panel 4: 4 Analisa AI (OpenRouter, llm/persona_analysis.py) ----------
const PERSONA_ORDER = ["GEMA", "LEON", "AKELA", "RIVAN"];
let personaStatus = {};  // {lens: true/false} -- prompt sudah diisi?
let personaTexts = {};   // {lens: notes text or undefined}

function renderPersonaCards() {
  $("#personaGrid").innerHTML = PERSONA_ORDER.map(lens => {
    const label = LENS_LABELS[lens] || lens;
    const hasPrompt = !!personaStatus[lens];
    const text = personaTexts[lens];
    const preview = text
      ? text.slice(0, 140) + (text.length > 140 ? "…" : "")
      : "Belum ada analisa.";
    const missingNote = hasPrompt ? "" :
      `<div class="src" style="color:var(--fail)">Prompt belum diisi — tulis di prompts/persona_${lens.toLowerCase()}.txt</div>`;
    return `<div class="card persona-card ${lens} ${hasPrompt ? "" : "missing-prompt"}">
      <div class="label">${label}</div>
      <div class="persona-preview">${preview}</div>
      ${missingNote}
      <div class="form-row" style="margin-top:8px">
        <button class="btn small secondary" data-act="run-persona" data-lens="${lens}">Jalankan Analisa</button>
        <button class="btn small" data-act="view-persona" data-lens="${lens}" ${text ? "" : "disabled"}>Lihat Detail</button>
      </div>
    </div>`;
  }).join("");
}

async function loadPersonaAnalysis() {
  const [status, rows] = await Promise.all([
    (await fetch("/api/persona/status")).json(),
    (await fetch(`/api/reading?date=${today()}`)).json(),
  ]);
  personaStatus = status;
  personaTexts = {};
  rows.forEach(r => { if (PERSONA_ORDER.includes(r.lens)) personaTexts[r.lens] = r.notes; });
  renderPersonaCards();
}

function openPersonaModal(lens) {
  $("#personaModalTitle").textContent = LENS_LABELS[lens] || lens;
  $("#personaModalBody").textContent = personaTexts[lens] || "";
  $("#personaModal").showModal();
}
$("#personaModalClose").addEventListener("click", () => $("#personaModal").close());
$("#personaModal").addEventListener("click", (e) => {
  if (e.target === $("#personaModal")) $("#personaModal").close();
});

$("#personaGrid").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-act]");
  if (!btn) return;
  const lens = btn.dataset.lens;
  if (btn.dataset.act === "view-persona") { openPersonaModal(lens); return; }
  if (btn.dataset.act === "run-persona") {
    btn.disabled = true;
    btn.textContent = "Menjalankan…";
    const r = await postJSON("/api/persona/run", { lens });
    btn.disabled = false;
    btn.textContent = "Jalankan Analisa";
    if (r.error) { toast(r.error); return; }
    personaTexts[lens] = r.text;
    renderPersonaCards();
    toast(`Analisa ${LENS_LABELS[lens]} selesai`);
    openPersonaModal(lens);
  }
});
