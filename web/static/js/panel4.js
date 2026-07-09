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

async function loadReadingEntries() {
  const rows = await (await fetch(`/api/reading?date=${today()}`)).json();
  // sembunyikan SYNTHESIS & OUTLOOK:* (punya tempat sendiri di Panel 6) —
  // di sini cuma 4 lensa + external/conflict.
  const visible = rows.filter(r => r.lens !== "SYNTHESIS" && !r.lens.startsWith("OUTLOOK:"));
  $("#readingBody").innerHTML = visible.map(r =>
    `<tr><td>${r.lens}</td><td>${r.notes}</td></tr>`
  ).join("") || `<tr><td colspan="2" class="src">belum ada entri hari ini</td></tr>`;
}
$("#readingSaveBtn").addEventListener("click", async () => {
  const r = await postJSON("/api/reading/save", {
    date: today(), gema: $("#lensGema").value, leon: $("#lensLeon").value,
    akela: $("#lensAkela").value, rivan: $("#lensRivan").value,
    external_ai: $("#lensExternalAi").value, conflict: $("#lensConflict").value,
  });
  toast(`${r.ids.length} catatan tersimpan`);
  loadReadingEntries();
});
