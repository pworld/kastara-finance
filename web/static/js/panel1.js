// ---------- Panel 1: Snapshot + Backfill ----------
let latestSnapshotData = null;
let snapshotPeriod = "day";

function renderSnapshotCards() {
  if (!latestSnapshotData) return;
  const d = latestSnapshotData;

  function cardHtml(s) {
    let val = fmt(s.value);
    if (s.column === "fear_greed_value" && d.fear_greed_label && val !== null)
      val = val + " · " + d.fear_greed_label;
    const na = val === null;

    const comp = s.compare && s.compare[snapshotPeriod];
    let deltaClass = "na", deltaText = "n/a";
    if (comp) {
      const arrow = comp.delta > 0 ? "▲" : comp.delta < 0 ? "▼" : "–";
      deltaClass = comp.delta > 0 ? "up" : comp.delta < 0 ? "down" : "flat";
      const deltaStr = fmt(Math.abs(comp.delta));
      const pctStr = comp.pct !== null && comp.pct !== undefined
        ? ` (${comp.pct >= 0 ? "+" : "-"}${Math.abs(comp.pct).toFixed(2)}%)` : "";
      deltaText = `${arrow} ${comp.delta >= 0 ? "+" : "-"}${deltaStr}${pctStr}`;
    }

    return `<div class="card"><div class="label">${s.label}</div>
      <div class="value ${na ? "na" : ""}">${na ? "n/a" : val}</div>
      <div class="delta ${deltaClass}">${deltaText}</div></div>`;
  }

  // Kelompokkan per kategori (dari server, urutan kemunculan pertama
  // dipertahankan) biar 14 kartu tidak numpuk jadi 1 grid rata.
  const byCategory = new Map();
  for (const s of d.snapshot) {
    if (!byCategory.has(s.category)) byCategory.set(s.category, []);
    byCategory.get(s.category).push(s);
  }

  $("#cards").innerHTML = [...byCategory.entries()].map(([cat, items]) => `
    <div class="cat-group">
      <h4 class="cat-title">${cat}</h4>
      <div class="grid cards">${items.map(cardHtml).join("")}</div>
    </div>`).join("");
}

$("#snapshotPeriodSelect").addEventListener("change", (e) => {
  snapshotPeriod = e.target.value;
  renderSnapshotCards();
});

async function loadLatest() {
  const d = await (await fetch("/api/latest")).json();
  if (d.empty) {
    $("#emptyState").style.display = "block";
    $("#content").style.display = "none";
    $("#asOf").textContent = "kosong";
    return;
  }
  $("#emptyState").style.display = "none";
  $("#content").style.display = "block";
  $("#asOf").textContent = "per " + d.date + " · " + d.news_today + " berita hari itu";

  latestSnapshotData = d;
  renderSnapshotCards();

  const order = { fail: 0, skip: 1, ok: 2 };
  const flags = Object.entries(d.source_flags)
    .sort((a, b) => (order[a[1]] - order[b[1]]) || a[0].localeCompare(b[0]));
  $("#flags").innerHTML = flags.map(([k, v]) =>
    `<span class="flag"><span class="dot ${v}"></span>${k}</span>`).join("")
    || '<span class="src">tidak ada flag</span>';
}

async function loadDataGaps() {
  const inst = $("#bfInstrument").value;
  $("#bfGapInfo").textContent = "Memuat info data...";
  const g = await (await fetch(`/api/data_gaps?instrument=${encodeURIComponent(inst)}`)).json();
  if (!g.total_rows) { $("#bfGapInfo").textContent = "Belum ada data untuk instrument ini."; return; }

  const range = `${g.total_rows.toLocaleString("id-ID")} baris · ${g.date_from} s.d. ${g.date_to}`;
  if (g.calendar === "WEEKLY_WED") {
    $("#bfGapInfo").innerHTML = `${range} <span class="src">(rilis mingguan tiap Rabu — jeda antar-Rabu wajar, bukan gap)</span>`;
    return;
  }
  if (g.gaps_total_count === 0) {
    $("#bfGapInfo").innerHTML = `${range} <span style="color:var(--ok)">· tidak ada gap terdeteksi</span>`;
    return;
  }
  const shown = g.gaps.slice(0, 5)
    .map(gap => `${gap.from} s.d. ${gap.to} (${gap.days} hari)`).join(", ");
  const more = g.gaps_total_count > 5 ? ` · +${g.gaps_total_count - 5} gap lain` : "";
  $("#bfGapInfo").innerHTML = `${range} <span style="color:var(--fail)">· ${g.gaps_total_count} gap terdeteksi</span>: ${shown}${more}`;
}
$("#bfInstrument").addEventListener("change", loadDataGaps);

let bfPreviewData = null;
$("#bfPreviewBtn").addEventListener("click", async () => {
  const body = { instrument: $("#bfInstrument").value, from: $("#bfFrom").value, to: $("#bfTo").value };
  if (!body.from || !body.to) { toast("Isi rentang tanggal dulu"); return; }
  const r = await postJSON("/api/backfill/preview", body);
  bfPreviewData = body;
  $("#bfResult").textContent = `Fetched ${r.fetched}, baru ${r.new}, duplikat ${r.dup}` +
    (r.sample_from ? ` (contoh ${r.sample_from} .. ${r.sample_to})` : "");
  $("#bfCommitBtn").style.display = r.new > 0 ? "inline-block" : "none";
});
$("#bfCommitBtn").addEventListener("click", async () => {
  if (!bfPreviewData) return;
  const r = await postJSON("/api/backfill/commit", bfPreviewData);
  $("#bfResult").textContent = `OK — ${r.new} baris baru ditulis (${r.dup} duplikat di-skip).`;
  $("#bfCommitBtn").style.display = "none";
  toast("Backfill selesai");
});
