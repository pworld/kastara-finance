function initDateDefaults() {
  ["#newsDateFrom", "#newsDateTo", "#synthDate"].forEach(sel => {
    const el = $(sel);
    if (el && !el.value) el.value = today();
  });
}

async function refreshAll() {
  initDateDefaults();
  await loadLatest();
  await loadDataGaps();
  await loadAssets();
  await loadContextCharts();
  await loadNews();
  await loadEconCalendar();
  await loadExpectations();
  await loadPositioning();
  await loadDisonansi();
  await loadPolicyNotes();
  await loadKeyNews();
  await loadPersonaAnalysis();
  await loadOutlookInstruments();
  await loadSynthesisForDate();
  await loadDuePredictions();
  await loadHistory();
}
$("#refresh").addEventListener("click", refreshAll);
refreshAll();
