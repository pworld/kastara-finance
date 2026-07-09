const $ = (s) => document.querySelector(s);
const today = () => new Date().toISOString().slice(0, 10);

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

function fmt(v) {
  if (v === null || v === undefined) return null;
  if (typeof v !== "number") return String(v);
  const abs = Math.abs(v);
  if (abs >= 1e9) return (v / 1e9).toFixed(2) + "B";
  if (abs >= 1e6) return (v / 1e6).toFixed(2) + "M";
  if (abs >= 1000) return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (abs < 1 && abs > 0) return v.toPrecision(3);
  return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

// ---------- Generic table controls: search + sort + pagination (client-side) ----------
// Dipakai semua tabel data (News, Signals, Econ Calendar, Positioning, Policy,
// Panel 7 Riwayat) -- 1 utility dipakai berulang, bukan reimplementasi per tabel.
// Cari/sort/page BEROPERASI di baris yang SUDAH di-fetch (tableCache[key]),
// jadi ganti halaman/sort/cari TIDAK fetch ulang ke server.
const tableCache = {};    // key -> full row array (hasil fetch terakhir)
const tableState = {};    // key -> {search, sortKey, sortDir, page, pageSize}
const tableRerender = {}; // key -> fn() yang render ulang dari cache+state

function getTableState(key, pageSize = 20) {
  if (!tableState[key]) tableState[key] = { search: "", sortKey: null, sortDir: 1, page: 1, pageSize };
  return tableState[key];
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function applyTableControls(key, rows, { searchFields = [] } = {}) {
  const st = getTableState(key);
  let out = rows;
  if (st.search) {
    const q = st.search.toLowerCase();
    out = out.filter(r => searchFields.some(f => String(r[f] ?? "").toLowerCase().includes(q)));
  }
  if (st.sortKey) {
    out = [...out].sort((a, b) => {
      const av = a[st.sortKey], bv = b[st.sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * st.sortDir;
      return String(av).localeCompare(String(bv)) * st.sortDir;
    });
  }
  const total = out.length;
  const totalPages = Math.max(1, Math.ceil(total / st.pageSize));
  if (st.page > totalPages) st.page = totalPages;
  const start = (st.page - 1) * st.pageSize;
  return { pageRows: out.slice(start, start + st.pageSize), total, totalPages };
}

// Bar (cari + rows/hal) di ATAS tabel; foot (count + prev/next) di BAWAH
// tabel, count rata kiri & prev/next rata kanan -- pola pagination standar.
function renderTableBar(key, total, totalPages, onChange) {
  const st = getTableState(key);

  const bar = document.querySelector(`[data-tblbar="${key}"]`);
  if (bar) {
    bar.innerHTML = `<input type="text" class="tbl-search" placeholder="Cari...">`;
    bar.querySelector(".tbl-search").value = st.search;
    bar.querySelector(".tbl-search").addEventListener("input", debounce((e) => {
      st.search = e.target.value; st.page = 1; onChange();
    }, 250));
  }

  const foot = document.querySelector(`[data-tblfoot="${key}"]`);
  if (foot) {
    const startN = total === 0 ? 0 : (st.page - 1) * st.pageSize + 1;
    const endN = Math.min(st.page * st.pageSize, total);
    foot.innerHTML = `
      <div class="tbl-pageinfo">
        <span class="src">${startN}-${endN} dari ${total}</span>
        <select class="tbl-pagesize">
          <option value="10">10/hal</option><option value="20">20/hal</option>
          <option value="50">50/hal</option><option value="100">100/hal</option>
        </select>
      </div>
      <div class="tbl-pageinfo">
        <button class="btn small secondary tbl-prev" ${st.page <= 1 ? "disabled" : ""}>‹ Prev</button>
        <span class="src">Hal ${st.page}/${totalPages}</span>
        <button class="btn small secondary tbl-next" ${st.page >= totalPages ? "disabled" : ""}>Next ›</button>
      </div>
    `;
    foot.querySelector(".tbl-pagesize").value = String(st.pageSize);
    foot.querySelector(".tbl-pagesize").addEventListener("change", (e) => {
      st.pageSize = Number(e.target.value); st.page = 1; onChange();
    });
    foot.querySelector(".tbl-prev").addEventListener("click", () => { st.page--; onChange(); });
    foot.querySelector(".tbl-next").addEventListener("click", () => { st.page++; onChange(); });
  }
}

// Delegated sort-header clicks: <th data-sort="field"> di dalam <table data-tblkey="X">
document.addEventListener("click", (e) => {
  const th = e.target.closest("th[data-sort]");
  if (!th) return;
  const table = th.closest("table[data-tblkey]");
  if (!table) return;
  const key = table.dataset.tblkey;
  const st = getTableState(key);
  const field = th.dataset.sort;
  if (st.sortKey === field) st.sortDir *= -1; else { st.sortKey = field; st.sortDir = 1; }
  table.querySelectorAll("th[data-sort]").forEach(h => h.classList.remove("sort-asc", "sort-desc"));
  th.classList.add(st.sortDir === 1 ? "sort-asc" : "sort-desc");
  tableRerender[key]?.();
});

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

// ---------- Tabs ----------
$("#tabs").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  const tab = e.target.dataset.tab;
  [...$("#tabs").children].forEach(b => b.classList.toggle("active", b === e.target));
  document.querySelectorAll(".tabpanel").forEach(p => p.classList.toggle("active", p.id === "tab-" + tab));
});
