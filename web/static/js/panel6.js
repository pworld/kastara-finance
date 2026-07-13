// ---------- Panel 6: Synthesis / Journal / Prediction ----------
async function loadOutlookInstruments() {
  const list = await (await fetch("/api/outlook_instruments")).json();
  $("#outlookGrid").innerHTML = list.map(inst => `
    <div class="card">
      <div class="label">${inst}</div>
      <select data-outlook="${inst}" style="margin-top:6px">
        <option>Neutral</option><option>Bullish</option><option>Bearish</option>
      </select>
    </div>`).join("");
  // Wire change -> simpan outlook utk tanggal yang dipilih di Panel 6.
  $("#outlookGrid").querySelectorAll("[data-outlook]").forEach(sel => {
    sel.addEventListener("change", async () => {
      await postJSON("/api/outlook/save", {
        date: $("#synthDate").value || today(),
        instrument: sel.dataset.outlook, stance: sel.value,
      });
      toast(`Outlook ${sel.dataset.outlook}: ${sel.value}`);
    });
  });
}

async function loadSynthesisForDate() {
  const date = $("#synthDate").value || today();
  const s = await (await fetch(`/api/synthesis?date=${date}`)).json();
  $("#synthText").value = s.text || "";
  const outlook = await (await fetch(`/api/outlook?date=${date}`)).json();
  $("#outlookGrid").querySelectorAll("[data-outlook]").forEach(sel => {
    sel.value = outlook[sel.dataset.outlook] || "Neutral";
  });
}
$("#synthDate").addEventListener("change", loadSynthesisForDate);

$("#synthSaveBtn").addEventListener("click", async () => {
  const text = $("#synthText").value.trim();
  if (!text) { toast("Isi synthesis dulu"); return; }
  await postJSON("/api/synthesis/save", { date: $("#synthDate").value || today(), text });
  toast("Synthesis tersimpan");
  loadSynthesisLog();  // segarkan riwayat di Panel 7
});
$("#jSizingBtn").addEventListener("click", async () => {
  const instrument = $("#jInstrument").value.trim();
  const entry = $("#jEntry").value, sl = $("#jSl").value;
  if (!instrument || !entry || !sl) { toast("Instrument, Entry, SL wajib diisi dulu"); return; }
  const result = await (await fetch(
    `/api/sizing/suggest?instrument=${encodeURIComponent(instrument)}&entry=${entry}&sl=${sl}`
  )).json();
  if (result.error) { $("#jSizingResult").textContent = result.error; return; }
  if (result.skip) {
    $("#jSizingResult").textContent = `SKIP — ${result.skip_reason} (budget ${fmt(result.risk_budget)} tidak cukup utk 1 lot)`;
    $("#jSkipReason").value = result.skip_reason;
    $("#jPlannedSize").value = "";
  } else {
    $("#jSizingResult").textContent = `Suggested: ${result.suggested_units} unit (risiko aktual ${fmt(result.actual_risk)} / budget ${fmt(result.risk_budget)})`;
    $("#jPlannedSize").value = result.suggested_units;
    $("#jSkipReason").value = "";
  }
});

$("#jSaveBtn").addEventListener("click", async () => {
  await postJSON("/api/journal/add", {
    date: today(), instrument: $("#jInstrument").value, setup_type: $("#jSetup").value,
    entry_price: $("#jEntry").value || null, sl_price: $("#jSl").value || null,
    tp1_price: $("#jTp1").value || null, outcome: $("#jOutcome").value,
    personal_notes: $("#jNotes").value, lesson_learned: $("#jLesson").value,
    planned_size: $("#jPlannedSize").value || null, actual_size: $("#jActualSize").value || null,
    skip_reason: $("#jSkipReason").value || null,
  });
  toast("Tersimpan ke trading journal");
  ["jSetup","jEntry","jSl","jTp1","jNotes","jLesson","jPlannedSize","jActualSize","jSkipReason"].forEach(id => $("#" + id).value = "");
  $("#jSizingResult").textContent = "";
});
$("#pSaveBtn").addEventListener("click", async () => {
  const claim = $("#pClaim").value.trim();
  if (!claim || !$("#pTargetDate").value) { toast("Claim & target date wajib diisi"); return; }
  await postJSON("/api/prediction/add", {
    date_made: today(), horizon: $("#pHorizon").value, claim,
    confidence: $("#pConfidence").value || null, basis: $("#pBasis").value,
    target_date: $("#pTargetDate").value,
  });
  toast("Prediksi tercatat");
  ["pConfidence","pClaim","pBasis","pTargetDate"].forEach(id => $("#" + id).value = "");
  loadDuePredictions();
});
async function loadDuePredictions() {
  const rows = await (await fetch("/api/prediction/due")).json();
  $("#dueBody").innerHTML = rows.map(r => `<tr>
    <td class="src">${r.date_made}</td><td class="src">${r.target_date}</td>
    <td>${r.claim}</td><td>${r.confidence ?? "-"}%</td>
    <td>
      <button class="btn small secondary" data-score="BENAR" data-id="${r.id}">Benar</button>
      <button class="btn small danger" data-score="SALAH" data-id="${r.id}">Salah</button>
      <button class="btn small secondary" data-score="PARTIAL" data-id="${r.id}">Partial</button>
    </td>
  </tr>`).join("") || `<tr><td colspan="5" class="src">tidak ada prediksi jatuh tempo</td></tr>`;
}
$("#dueBody").addEventListener("click", async (e) => {
  const outcome = e.target.dataset.score;
  if (!outcome) return;
  await postJSON("/api/prediction/score", { id: Number(e.target.dataset.id), outcome });
  toast("Prediksi di-skor: " + outcome);
  loadDuePredictions();
});

// ---------- Panel 6: Daily Briefing -> Telegram (Phase E) ----------
$("#briefingSendBtn").addEventListener("click", async () => {
  const r = await postJSON("/api/briefing/send", { date: today() });
  $("#briefingPreview").textContent = r.text;
  toast(r.sent ? "Briefing terkirim ke Telegram" : "Gagal kirim — cek TELEGRAM_BOT_TOKEN/CHAT_ID di .env");
});
