# SOP PENGGUNAAN APLIKASI — Kastara Finance
**Versi:** 1.0 · 12 Juli 2026 · Owner: Giel
**Posisi dokumen:** mengatur KAPAN membuka panel apa dan APA yang boleh dilakukan di sana. Aturan level aset tetap di SOP masing-masing (single source of truth):
- Aturan entry/SL/TP/sizing trade → Master Plan §3 + Build Contract v1.3
- Trigger & bracket emas, screening saham invest → Saham Emas SOP v2.0
- Alokasi multi-aset & low-point trigger → Investment SOP v4.1
Kalau dokumen ini terasa bertentangan dengan SOP di atas: SOP aset yang menang, dan konflik dicatat untuk direview.

---

## 0. PRINSIP PEMAKAIAN

1. **Dua lane, dua ritme, satu aplikasi.** TRADE lane = ritme harian (Panel 1–6). INVEST lane = ritme mingguan/kuartalan (Tab 8 + SOP invest). Jangan tukar ritmenya: cek posisi invest tiap hari = mengundang jadi trader di portfolio yang harusnya boring (prinsip Saham Emas SOP §0.1).
2. **Aplikasi men-suggest, Giel memutuskan.** Tidak ada keputusan yang sah tanpa melalui gate (`giel_approved`) — dan tidak ada trade yang sah tanpa row `trade_signals` yang di-approve lebih dulu. Trade tanpa sinyal tercatat = pelanggaran SOP, apa pun hasilnya.
3. **Data bolong = analisa ditunda, bukan ditebak.** `source_flags` merah pada field yang dibutuhkan hari itu → bagian analisa yang bergantung padanya di-skip dan dicatat, bukan diisi asumsi.
4. **Sesi pagi adalah sesi baca & keputusan — bukan sesi riset.** Riset mendalam (backfill, intake emiten, tuning) punya slot sendiri di luar ritual pagi.

---

## 1. SOP DAILY — RITUAL PAGI (±20 menit, 07.00 WIB)

> Prasyarat otomatis: scraper jalan 00.00, dashboard siap 06.30.

**07.00 — Panel 1 · Data Snapshot (2 menit)**
- [ ] Cek `source_flags`: semua hijau? Kalau ada merah → catat field mana; kalau field itu dipakai analisa hari ini (mis. funding rate merah padahal mau baca BTC), tandai analisa terkait sebagai LOW_CONFIDENCE hari ini.
- [ ] Lirik anomali besar (delta harian ekstrem) — bukan untuk disimpulkan, cukup ditandai untuk dibaca di panel berikutnya.

**07.02 — Panel 2 · News Briefing (3 menit)**
- [ ] Baca headline HIGH dulu, lalu MED. Flag `key_trigger` HANYA untuk berita yang benar-benar bisa mengubah lane — bukan semua berita menarik.
- [ ] Berita panjang yang butuh dibedah → masukkan `manual_articles` untuk sesi baca terpisah, JANGAN habiskan slot pagi.

**07.05 — Panel 3 · Forward Panel (5 menit)**
- [ ] Baca urut: Expectations (FedWatch/Dot Plot) → Positioning (COT, ETF flow, IHSG FF) → Policy Tracker terbaru → kalender: katalis HIGH berapa hari lagi?
- [ ] Cek Disonansi Flag. Kalau aktif → wajib disebut di synthesis nanti.
- [ ] **Output langkah ini: LANE hari ini per instrumen aktif** (bullish/bearish/netral — bias, bukan entry).
- [ ] Posisi terbuka saham AS? → cek countdown earnings. H-1 earnings = **tutup penuh hari ini** (keputusan terkunci #3), bukan besok.
- [ ] Event HIGH < 48 jam & ada posisi terbuka → jalankan rule SL-ke-breakeven sesuai SOP.

**07.10 — Panel 4 · Reading Workspace (5 menit)**
- [ ] Jalankan lensa persona SESUAI KEBUTUHAN, bukan ritual 4 kartu tiap hari:
  - Ada berita key trigger / katalis dekat → jalankan lensa yang relevan (berita Fed → GEMA+AKELA; kebijakan domestik → LEON; pergerakan BTC anomali → RIVAN).
  - Hari tenang tanpa katalis → boleh nol panggilan. Kartu kosong bukan kegagalan.
- [ ] Hasil lensa = bahan, bukan vonis. Konflik antar lensa → tulis di Conflict Notes, jangan didamaikan paksa.
- [ ] Output AI eksternal (kalau ada) masuk External AI Check — dibanding, tidak diikuti.

**07.15 — Panel 5 · Chart & Sinyal (3 menit)**
- [ ] Cek sinyal SUGGESTED. Untuk tiap sinyal, jalankan gate berurutan:
  1. Badge lane instrumen = TRADE/BOTH? (bukan INVEST/NONE/AVOID)
  2. Zona S&R sudah `validated_by_giel`?
  3. Breakout + retest + volume sesuai rules (bukan wick, volume hadir)?
  4. R:R ≥ 1.5?
  5. Lane dari Panel 3 tidak bertentangan frontal? (lane bearish + sinyal long = alasan kuat untuk reject/skip, tercatat)
  6. Kalender: tidak ada earnings (saham AS) / event HIGH yang melanggar rule hold?
- [ ] Semua lolos → APPROVE. Ada yang gagal → REJECT dengan notes satu kalimat. **Tidak ada "approve nanti sore dipikir lagi"** — keputusan di sesi ini atau reject.
- [ ] Approve ≠ eksekusi. Eksekusi = langkah §2 di bawah.

**07.18 — Panel 6 · Synthesis (2 menit)**
- [ ] Tulis synthesis 1 paragraf DENGAN TANGAN SENDIRI (bukan copy hasil lensa).
- [ ] Set outlook per instrumen aktif.
- [ ] Catat MAKSIMAL 1 prediksi ke `prediction_log` — hanya kalau memang ada klaim yang layak diuji. Prediksi kosong lebih baik daripada prediksi asal.
- [ ] Ada prediksi lama jatuh tempo? Nilai sekarang (BENAR/SALAH/PARTIAL) — jangan tunda ke "nanti".

**07.20 — Selesai.** Opsional: kirim Daily Briefing (tombol Panel 6) kalau konten mau dipublikasikan.

### Yang DILARANG di sesi pagi
- Membuka Tab 8 (Universe & Grader) — itu ritme mingguan/kuartalan. Kecuali satu hal: melihat badge lane/kuadran yang sudah tampil otomatis di Panel 5.
- Backfill, intake emiten, tuning parameter, baca artikel panjang.
- Approve sinyal yang gagal di salah satu gate "karena feeling bagus".

---

## 2. SOP EKSEKUSI (setelah approve — di luar aplikasi)

> Aplikasi berhenti di sinyal approved + size terhitung. Eksekusi = tangan Giel di broker. (Kontrak §15 — tanpa API broker.)

**Crypto (exchange):**
- [ ] Pasang buy limit di harga entry sinyal + SL sesuai sinyal. Ukuran dari sizing engine, tanpa pembulatan ke atas.

**Saham IDX (Stockbit) — jam pasar WIB:**
- [ ] Ukuran = hasil kuantisasi lot (pembulatan BAWAH). Kalau sinyal berstatus skip `RISK_CAPACITY_EXCEEDED` → TIDAK dieksekusi, titik. Dilarang menggeser SL supaya lot muat.
- [ ] Ingat buffer ARA/ARB: risiko riil > jarak SL. Kalau buffer 1.5× membuat total risiko melebihi batas per trade → skip, catat.

**Saham AS (IBKR) — dipasang siang/sore WIB:**
- [ ] GTC buy limit di harga entry sinyal. Fractional boleh — presisi sizing diutamakan.
- [ ] Cek TANGGAL EARNINGS instrumen sebelum pasang order: kalau earnings jatuh sebelum horizon swing wajar → pertimbangkan skip dari awal, karena posisi wajib ditutup penuh sebelum earnings.

**Setelah eksekusi (hari yang sama):**
- [ ] Isi `trading_journal`: entry aktual, planned_size vs actual_size, dan (kalau skip) skip_reason. Jurnal diisi HARI ITU — jurnal yang diisi mundur adalah jurnal fiksi.

---

## 3. SOP WEEKLY — SESI SENIN (±20 menit, di luar ritual pagi)

- [ ] **Emas**: jalankan cek trigger bracket per Saham Emas SOP Tab 01 (logammulia.com vs database). Ada trigger → eksekusi tranche sesuai SOP-nya. Aplikasi tidak mengatur ini — hanya tempat mencatat kalau mau.
- [ ] **SBN foreign flow**: input manual ke Forward Panel (Layer C). Ingat aturannya: ini bacaan matamu sendiri, tidak pernah masuk slice persona.
- [ ] **COT mingguan**: rilis CFTC sudah masuk otomatis — baca perubahan posisi besar, terutama kalau Disonansi Flag sempat aktif minggu lalu.
- [ ] **Review posisi ONGOING** di jurnal: masih sesuai premis? SL masih di tempatnya (bukan digeser)? Earnings/event HIGH minggu depan?
- [ ] **Tab 8 — lirik universe**: ada flag integritas baru (UMA/suspensi) pada emiten yang dipegang atau di watchlist? Emiten yang jadi AVOID saat sedang dipegang = agenda evaluasi hari itu juga, bukan menunggu kuartal.

---

## 4. SOP MONTHLY (±30 menit, akhir bulan)

- [ ] **Skor prediksi**: semua prediksi jatuh tempo bulan ini ternilai. Hitung kasar hit-rate — turun terus = bahan refleksi basis prediksi, bukan alasan berhenti mencatat.
- [ ] **Review jurnal**: baca semua trade + skip bulan ini. Cari pola pelanggaran SOP (bukan pola pasar): ada SL digeser? Ada trade tanpa sinyal? Ada approve di luar sesi pagi? Pelanggaran = tulis di lesson_learned, apa pun hasil trade-nya.
- [ ] **Data health check**: gap tanggal & NULL rate kolom kunci (pola: field yang lama merah di source_flags). Bolong sistematis → task perbaikan scraper, bukan dibiarkan.
- [ ] **Invest lane — setoran rutin**: jalankan alokasi bulanan per Investment SOP v4.1 (reksadana indeks via Bibit/Bareksa, dst). Aplikasi berperan satu hal saja: cek Panel 3/Tab 8 untuk konteks — TAPI low-point trigger dari SOP v4.1 yang menentukan, bukan lensa persona. Persona tidak mengatur nabung rutin.

---

## 5. SOP QUARTERLY (±1 jam, setelah musim laporan keuangan)

- [ ] **Refresh fundamental**: tarik/input kuartal terbaru untuk universe (J-4). Emiten dengan <8 kuartal tetap LOW_CONFIDENCE.
- [ ] **Jalankan ulang grader** seluruh universe → review perubahan kuadran di Tab 8. Kuadran berubah drastis → baca komponennya, jangan cuma badge-nya.
- [ ] **Isi grader_log outcome** untuk grade yang berumur 3/6 bulan (widget komponen D). Ini satu-satunya sesi di mana revisi bobot rubrik BOLEH dipertimbangkan — dan hanya kalau log menunjukkan pola, bukan karena satu kasus menjengkelkan.
- [ ] **Review universe**: emiten watchlist naik ke universe? Emiten universe yang 2 kuartal berturut memburuk → turunkan lane / keluarkan, tercatat dengan alasan.
- [ ] **Kalibrasi lane**: instrumen INVEST yang mau naik ke TRADE → wajib lewat validasi bar-replay dulu (`lane_validated_at`), bukan karena "sudah lama dipantau".
- [ ] **Review SOP ini sendiri**: ada langkah yang tidak pernah dijalankan 3 bulan berturut? Hapus atau perbaiki — SOP yang diabaikan lebih berbahaya daripada tidak ada SOP.

---

## 6. SOP INVEST LANE — PERAN APLIKASI (ringkas)

Invest lane hidup di SOP v4.1 + Saham Emas SOP. Aplikasi hanya berperan sebagai:
1. **Filter kualitas**: kandidat nabung saham individual wajib melewati grader (Tab 8) — kuadran AVOID tidak dibeli untuk lane mana pun, termasuk invest. INVESTABLE/WATCH = boleh masuk pertimbangan SOP invest.
2. **Konteks siklus**: Panel 3 (net liquidity, DXY, foreign flow) sebagai bacaan "musim" — memperkaya keputusan tranche, TIDAK meng-override trigger objektif SOP invest. Drawdown aset riil saat dollar-strength = mekanika forced-selling, bukan alasan mengubah alokasi (prinsip financial repression yang sudah dipegang).
3. **Intake**: emiten baru yang menarik → jalur intake Tab 8 (komponen C), grade dulu, baru masuk daftar pertimbangan. Tidak ada beli-karena-berita tanpa lewat intake.
4. **Pencatatan**: transaksi invest dicatat (jurnal/sheet sesuai SOP asetnya) — aplikasi bukan pengganti pencatatan SOP invest yang sudah jalan.

Yang DILARANG: memakai `trade_signals` untuk timing pembelian invest, dan memakai trigger invest untuk membenarkan trade. Dua lane, dua logika, satu larangan silang.

---

## 7. PROTOKOL KONDISI TIDAK NORMAL

| Kondisi | Protokol |
|---|---|
| Scraper gagal total (banyak merah) | Ritual pagi tetap jalan tapi TANPA keputusan sinyal baru hari itu. Perbaikan scraper = task siang, bukan panik pagi. |
| Sinyal muncul tapi Giel sedang emosional (habis loss, revenge mood) | Reject atau biarkan tanpa keputusan sampai besok pagi. Sinyal valid akan tetap valid; kebutuhan "harus sekarang" adalah sinyal emosi, bukan sinyal pasar. |
| Posisi kena SL | Eksekusi cut sesuai rule (close D1 di bawah zona). Isi jurnal hari itu + lesson. DILARANG membuka chart mencari entry baru di instrumen yang sama pada hari yang sama. |
| ARB berhari-hari (tidak bisa keluar) | Pasang antrian jual tiap hari di harga terbaik yang mungkin, catat di jurnal per hari. Ini skenario yang buffer 1.5× memang antisipasi — bukan kegagalan sistem. |
| Ingin mengubah aturan (SL, bobot, threshold) | Tulis usulan + alasan, TIDUR SATU MALAM, review saat tidak ada posisi terbuka di instrumen terkait. Perubahan hanya lewat revisi dokumen SOP/kontrak, tidak pernah lewat "pengecualian sekali ini". |

---

*SOP Penggunaan Aplikasi v1.0 — direview bersama SOP quarterly (§5 poin terakhir). Dokumen ini mengatur ritme; aturan aset tetap di SOP masing-masing.*