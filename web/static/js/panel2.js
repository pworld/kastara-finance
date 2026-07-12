// ---------- Panel 2: News ----------
function renderNewsTable() {
  const { pageRows, total, totalPages } = applyTableControls("news", tableCache.news || [], {
    searchFields: ["headline", "source"],
  });
  $("#newsBody").innerHTML = pageRows.map(r => {
    const link = r.raw_url
      ? `<a href="${r.raw_url}" target="_blank" rel="noopener">${r.headline}</a>`
      : r.headline;
    const isKey = r.is_key_trigger ? 1 : 0;
    const btn = r.id !== undefined
      ? `<button class="btn small ${isKey ? "key-on" : "secondary"}" data-flagid="${r.id}" data-iskey="${isKey}">${isKey ? "★ Key" : "🚩 key"}</button>`
      : "";
    return `<tr class="${isKey ? "news-key" : ""}">
      <td class="src">${r.date}</td>
      <td><span class="badge ${r.impact_level}">${r.impact_level}</span></td>
      <td>${link}</td><td class="src">${r.source}</td>
      <td>${btn}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="5" class="src">tidak ada berita untuk tanggal/filter ini</td></tr>`;
  renderTableBar("news", total, totalPages, renderNewsTable);
}
tableRerender.news = renderNewsTable;

async function loadNews() {
  const params = new URLSearchParams({ limit: "200" });
  const from = $("#newsDateFrom").value, to = $("#newsDateTo").value;
  const impact = $("#newsImpactSelect").value;
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  if (impact === "__KEY__") params.set("key_only", "1");
  else if (impact) params.set("impact", impact);
  tableCache.news = await (await fetch("/api/news?" + params)).json();
  renderNewsTable();
}
$("#newsBody").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-flagid]");
  if (!btn) return;
  const nowKey = btn.dataset.iskey === "1";
  await postJSON("/api/news/flag_key", { id: Number(btn.dataset.flagid), is_key: !nowKey });
  toast(nowKey ? "Key trigger dilepas" : "Ditandai key trigger");
  loadNews();
});
$("#newsImpactSelect").addEventListener("change", loadNews);
$("#newsDateFrom").addEventListener("change", loadNews);
$("#newsDateTo").addEventListener("change", loadNews);
$("#artSaveBtn").addEventListener("click", async () => {
  const headline = $("#artHeadline").value.trim();
  if (!headline) { toast("Headline wajib diisi"); return; }
  await postJSON("/api/articles/add", {
    date: $("#artDate").value || today(), source: $("#artSource").value,
    url: $("#artUrl").value, headline, notes: $("#artNotes").value,
    tags: $("#artTags").value, key_event: $("#artKeyEvent").checked,
  });
  toast("Artikel tersimpan");
  ["artSource","artUrl","artHeadline","artNotes","artTags"].forEach(id => $("#" + id).value = "");
  $("#artKeyEvent").checked = false;
});
