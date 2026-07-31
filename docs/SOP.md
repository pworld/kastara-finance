# SOP PENGGUNAAN APLIKASI — Kastara Finance
**Versi:** 1.2 · 28 Juli 2026 · Owner: Giel
**Posisi dokumen:** mengatur KAPAN membuka panel apa dan APA yang boleh dilakukan di sana. Aturan level aset tetap di SOP masing-masing (single source of truth):

> **Struktur dokumen:** **Bagian A (§0–§7)** = ritme & aturan (kapan buka apa).
> **Bagian B (§8)** = **cara BACA tiap item di tiap panel** (arti angka, naik/turun
> artinya apa) — dipakai kalau kamu lupa "ini field apa maksudnya". **Bagian C
> (§9)** = lane Investing (dulu sidebar "Universal") — cara baca + cara isi.
> Kalau cuma mau ritual pagi: Bagian A cukup. Bagian B/C = kamus rujukan.

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

### Mode Ringkas — sesi 5 menit (hari sibuk)

> Detail penuh + rasional: `docs/mode_ringkas_pwa_mobile_v1.md`. Prinsip:
> aplikasi ini **habit engine**, bukan pengganti tools berat — metrik
> kesehatannya **streak harian** (dibuka kemarin, dan kemarinnya lagi), bukan
> kelengkapan fitur. Mode Ringkas menjaga rantai harian tidak putus di hari
> yang cuma menyisakan 5 menit — **bukan pengganti** ritual pagi penuh di atas.

**[WAJIB · ~1 menit]** — cuma ini saja = "hari tidak putus":
- [ ] Catat 1 prediksi ATAU nilai 1 prediksi yang jatuh tempo (`prediction_log`)
  — satu-satunya hal yang TIDAK BISA di-backfill; prediksi yang tak dicatat
  hari ini hilang permanen.

**[INTI · ~2 menit]** — kalau sempat:
- [ ] Scan data pagi 10 detik: ada anomali besar? (lihat, jangan analisa)
- [ ] Baca berita HIGH/briefing: ada yang mengubah lane hari ini? Flag
  `for_reading` kalau layak dibaca serius nanti.

**[BONUS · ~2 menit]** — kalau benar-benar longgar:
- [ ] Konfirmasi tag/thread SUGGESTED (klik, tak perlu mikir berat).
- [ ] Cek posisi ONGOING: ada yang kena aturan hari ini? (earnings saham AS
  H-1 = tutup penuh; event HIGH < 48 jam = SL breakeven.)

**TIDAK di Mode Ringkas** (tunggu sesi laptop): approve/reject sinyal,
sizing, jalankan persona (biaya LLM), synthesis panjang, backfill, settings,
grader override.

**Aturan mental (jangkar habit):** *"Hari tersibuk pun, saya catat atau
nilai satu prediksi."* Kalau cuma itu yang sempat, hari itu tetap sukses —
streak utuh. Semua yang lain boleh dikejar di sesi laptop berikutnya.

**Batas jujur:** Mode Ringkas bukan pengganti sesi penuh, dan tidak
menghasilkan keputusan trade (anti-impulsif, bukan bug). 5 hari berturut
hanya Mode Ringkas = sinyal untuk jujur soal disiplin vs kesibukan (§7).

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

# BAGIAN B — CARA BACA TIAP PANEL (kamus rujukan)

> Prinsip yang berlaku di SELURUH bagian ini: **angka = bahan, bukan vonis.**
> Kolom "cara baca" di bawah menjelaskan arti umum sebuah gerakan — BUKAN
> perintah beli/jual. Keputusan tetap lewat gate (§0 poin 2). Satu field naik
> jarang berarti apa-apa sendirian; yang dicari di synthesis adalah **beberapa
> field bercerita hal yang sama** (konfirmasi) atau **saling bertentangan**
> (disonansi — justru itu yang menarik).

## 8. PANEL PER PANEL

### 8.1 Panel 1 · Snapshot Pasar
Tiap kartu = 1 angka terakhir + **delta** (perbandingan vs Hari/Minggu/Bulan/
Tahun, pilih di dropdown atas). ▲ hijau = naik, ▼ merah = turun. Delta itu yang
penting, bukan angka absolutnya.

**Kelompok Crypto (BTC):**

| Item | Artinya | Cara baca gerakannya |
|---|---|---|
| **BTC Close** | Harga tutup BTC | Naik = momentum harga bullish. Konfirmasi selalu silang ke volume & funding di bawah — harga naik tanpa volume = lemah. |
| **BTC Vol MA20** | Rata-rata volume 20 hari | Volume hari ini jauh > MA20 = partisipasi tinggi (breakout/berita). Di bawah MA20 = pasar sepi, gerakan kurang bisa dipercaya. |
| **BTC Dominance %** | Porsi market cap BTC vs total kripto | Naik = uang lari ke BTC (risk-off di kripto / altcoin ditinggal). Turun = "altseason", risk-on. |
| **Funding Rate** | Biaya perpetual futures | **Positif** = long bayar short → crowd LONG (rawan long-squeeze kalau ekstrem). **Negatif** = short bayar long → crowd SHORT. Ekstrem ke satu sisi = sinyal posisi terlalu ramai. |
| **OI Agregat** | Open interest (total kontrak terbuka) | Naik + harga naik = uang baru masuk (tren sehat). Naik + harga flat = leverage menumpuk (rawan). Turun = posisi ditutup/likuidasi. |
| **Long/Short Ratio** | Rasio akun long : short | > 1 = mayoritas long. Ekstrem tinggi = crowd satu sisi, kontrarian sering waspada. |
| **Liquidation Long 24h** | Nominal LONG yang dipaksa tutup (harga jatuh) | Besar = kaskade jual paksa baru terjadi → sering jadi wash-out / titik pembalikan lokal. |
| **Liquidation Short 24h** | Nominal SHORT yang dipaksa tutup (harga naik) | Besar = short-squeeze → dorongan naik sebagian "bahan bakar paksa", bukan demand organik. |

**Kelompok Makro Global:**

| Item | Artinya | Cara baca gerakannya |
|---|---|---|
| **DXY** | Indeks dolar AS | Naik = dolar kuat → tekanan ke aset risiko, emas, EM (termasuk IHSG/rupiah), sering ke BTC juga. Turun = pelonggaran tekanan. Ini "gravitasi" makro paling sering dipakai. |
| **US10Y %** | Yield obligasi AS 10 tahun | Naik = biaya modal naik, tekanan ke aset durasi panjang/growth/emas. Turun = sebaliknya. |
| **VIX** | Indeks volatilitas ("indeks ketakutan" S&P) | > 20 mulai gelisah, > 30 = panik. Naik tajam = risk-off. Rendah & datar = pasar tenang/komplasen. |
| **Fear & Greed** | Sentimen kripto 0–100 (+ label) | < 25 Extreme Fear, > 75 Extreme Greed. Kontrarian: greed ekstrem = hati-hati euforia; fear ekstrem = sering dekat dasar. |
| **Net Liquidity** | Likuiditas Fed = WALCL − RRP − TGA | Naik = likuiditas mengalir ke sistem (tailwind aset risiko). Turun = pengetatan. Bacaan "musim" lambat, bukan pemicu harian. |

**Kelompok Ekuitas & FX:**

| Item | Artinya | Cara baca gerakannya |
|---|---|---|
| **S&P 500** | Bursa AS | Proksi risk-on/off global. Naik = selera risiko global positif. |
| **IHSG** | Bursa Indonesia | Silangkan dengan foreign flow (Panel 3): IHSG naik + asing jual = ditopang lokal (kurang kokoh). |
| **USD/IDR** | Rupiah per dolar | Naik = rupiah **melemah** (tekanan modal keluar). Turun = rupiah menguat. |
| **USD/JPY** | Yen per dolar | Proksi carry trade global; lonjakan cepat sering seiring guncangan risk-off. |
| **Gold** | Emas | Naik saat DXY & yield turun = klasik. Naik BERSAMA dolar kuat = sinyal stress/permintaan safe-haven (baca §Saham Emas SOP). |

**Status Sumber Data (source_flags):** buka bagian collapsible di bawah kartu.
🟢 ok / 🟡 skip / 🟠 stale / 🔴 fail per sumber. **`stale`** (khusus
`fred_dxy`/`fred_us10y`/`fred_vix`/dll) = fetch-nya SUKSES tapi observasi
FRED yang didapat lebih tua dari batas wajar (`MAX_LAG_DAYS`,
`scrapers/macro_fred.py`) — beda dari `fail`. Angka di kartu tetap tampil
(basi masih lebih berguna drpd kosong), tapi jangan dibaca sebagai "hari
ini" — cek tanggal observasi aslinya kalau ragu. Field yang kamu butuhkan
hari ini merah (fail) ATAU oranye (stale) dan krusial → analisa yang
bergantung padanya LOW_CONFIDENCE / ditunda (§0 poin 3), bukan ditebak.

> **Manual Backfill** di panel ini = alat isi lubang data historis, BUKAN bacaan
> harian. Info gap tampil per instrument saat ganti dropdown; "Cek & Preview
> Semua Gap" mengecek semua instrument sekaligus. Ini kerja sesi riset (§0 poin
> 4), bukan ritual pagi.

### 8.2 Panel 2 · News
| Kolom | Cara baca |
|---|---|
| **Impact HIGH** | Berpotensi menggerakkan lane (Fed, CPI, BI rate, geopolitik besar). Baca duluan. |
| **Impact MED** | Konteks penting, jarang mengubah arah sendirian. |
| **Impact LOW** | Latar belakang / noise. Lewati saat pagi. |
| **Tombol 🚩 Key** | Kamu yang menandai. **HANYA** untuk berita yang benar-benar bisa mengubah lane — ini yang muncul di Panel 4 sebagai bahan 4 lensa. Jangan flag semua yang menarik (§1 07.02). |

> Impact di sini rule-based (kata kunci), bukan AI — anggap sebagai penyortir
> kasar, penilaian akhir tetap matamu. Berita panjang yang butuh dibedah →
> `manual_articles`, bukan dihabiskan di slot pagi.

### 8.3 Panel 3 · Forward
Ini panel "apa yang menunggu di depan". Baca urut: Calendar → Expectations →
Positioning → Policy → Disonansi.

**Economic Calendar** — event ekonomi mendatang (otomatis ForexFactory; `actual`
diisi otomatis pass sore investing.com atau manual).

| Kolom | Cara baca |
|---|---|
| **Importance HIGH** ("bintang 3") | Katalis kelas-berat (CPI, FOMC, NFP, RDG BI). Default filter tabel = HIGH saja. Toggle "HIGH + MED" kalau perlu lihat semua. |
| **Countdown (H-n)** | Berapa hari lagi. Ini **sumbu waktu** trade: "katalis apa, berapa hari lagi". Event HIGH < 48 jam + ada posisi → rule SL-ke-breakeven (§1 07.05). |
| **Forecast vs Previous** | Ekspektasi konsensus vs rilis sebelumnya. Arah perubahan = ekspektasi pasar. |
| **Actual** | Hasil rilis. **Yang menggerakkan pasar adalah Actual vs Forecast**, bukan Actual sendirian. Actual jauh di atas forecast (mis. **Core CPI** aktual 0.4% vs forecast 0.2%) = inflasi lebih panas dari dugaan → hawkish → tekanan ke aset risiko. "Core" = tanpa pangan & energi (inti tren inflasi). |

**Expectations (Layer B — manual):**
- **CME FedWatch cut probability** — peluang (0–1) pasar atas pemangkasan suku
  bunga di rapat berikut. 0.72 = pasar hargai 72% peluang cut. Naik = ekspektasi
  makin dovish.
- **Fed Dot Plot median** — proyeksi median FOMC untuk suku bunga. Baca sebagai
  arah jangka menengah.
- *Diisi manual* — API resmi berbayar (lihat catatan panel).

**Positioning (Layer C):** siapa memegang posisi apa.
- **COT** (otomatis) — posisi net spekulan di BTC/DXY/GOLD/SP500. Net-long
  ekstrem = crowd satu sisi.
- **BTC ETF net flow** (otomatis) — arus masuk/keluar ETF. Positif berhari-hari =
  demand institusi.
- **IHSG foreign flow** (otomatis) — `foreign_net_buy_value` positif = asing net
  beli. Silang ke IHSG di Panel 1.
- **SBN foreign flow** (manual, mingguan) — asing di obligasi negara. Ini
  **bacaan matamu sendiri, TIDAK pernah masuk slice persona** (§3).

**Policy Tracker (Layer A):** apa yang pejabat bank sentral katakan.
| Kolom | Cara baca |
|---|---|
| **Literal statement** | Yang BENAR-BENAR dikatakan (kutipan). Fakta. |
| **Stance score −2..+2** | Nilaian kamu: −2 sangat dovish (longgar) … +2 sangat hawkish (ketat). |
| **Inference** | Pembacaan arah/niat — **subjektif, tebakanmu**. |
| **Flag TESTABLE / SPEKULATIF** | Jujur: inference ini bisa diuji nanti (TESTABLE) atau cuma dugaan (SPEKULATIF). |
| **Drift note** | Berubah dari pernyataan sebelumnya? Perubahan nada = sinyal. |

**Disonansi Flag:** membandingkan **stance Policy Tracker** vs **positioning COT
DXY**. `SEARAH` = retorika & posisi sejalan. `DISONANSI` = bertentangan (mis.
pejabat hawkish tapi posisi taruhan dolar melemah) — **wajib disebut di
synthesis** (§1 07.05). Butuh stance_score terisi + ≥ 2 baris COT DXY, kalau
belum → "belum cukup data".

### 8.4 Panel 4 · Reading
| Bagian | Cara baca / pakai |
|---|---|
| **Berita Key Hari Ini** | Yang kamu flag 🚩 di Panel 2. Bahan mentah untuk 4 lensa. Kosong = flag dulu di Panel 2. |
| **4 Analisa (AI)** | 4 lensa persona (label: Global & Capital Flow, Policy & Sistem Domestik, Dinamika Pasar & Waktu, Fundamental & Realist). Klik "Jalankan" per kartu SESUAI KEBUTUHAN — bukan ritual 4 kartu tiap hari (§1 07.10). Hari tenang = boleh nol. |
| **Hasil lensa** | **Bahan, bukan vonis.** Lensa saling bertentangan = normal → tulis di Conflict Notes, jangan didamaikan paksa. |
| **External AI Check** | Paste hasil banding AI luar (opsional). Dibanding, TIDAK diikuti. |
| **Conflict Notes** | Poin yang belum sepakat antar lensa. Ini justru bahan paling berharga untuk synthesis. |

> Kartu bertanda "Prompt belum diisi" = file `prompts/persona_*.txt` kosong;
> lensa itu tak bisa jalan sampai promptnya ditulis.

### 8.5 Panel 5 · Chart
**Membaca chart candlestick:**
- **Candle hijau** = close ≥ open (naik), **merah** = turun. Sumbu (wick) = high–low, badan = open–close.
- **Garis MA** — MA50 (kuning), MA100 (ungu), MA200 (pink). Harga di atas MA200 = struktur jangka panjang bullish; MA pendek memotong ke atas MA panjang = momentum menguat. Legenda warna ada di header chart.
- **Volume bar** (bawah) + garis biru = volume MA20. Breakout **wajib** disertai volume di atas MA20 — kalau tidak, curigai.
- **Zona S&R** — kotak **hijau = SUPPORT**, **merah = RESISTANCE**. Meta chart menampilkan berapa zona aktif (dekat harga). Zona hanya sah jadi gate sinyal kalau sudah kamu validasi (`validated_by_giel`).
- **Marker sinyal** — lingkaran **isi hijau = BREAKOUT**, lingkaran **kosong biru = RETEST**, di titik entry.

**Rentang** (dropdown): 1 bulan … Semua. **Lane badge** di header (TRADE/BOTH/
INVEST/NONE) = boleh-tidaknya instrument ini di-trade.

**Tabel Sinyal (Breakout/Retest):**
| Kolom | Cara baca |
|---|---|
| **Tipe** | BREAKOUT (tembus zona) / RETEST (uji ulang zona). |
| **Entry / SL / TP1** | Harga saran dari engine. |
| **R:R** | Risk-reward. **Gate wajib ≥ 1.5** (§1 07.15). Di bawah itu = reject. |
| **Status** | pending / APPROVED / REJECTED. Approve/Reject di sini menjalankan gate 6 langkah (§1 07.15). **Approve ≠ eksekusi.** |

**Context Charts (30 hari):** mini-line DXY, S&P 500, US10Y, Fear & Greed —
konteks makro cepat tanpa pindah panel. Hijau = naik periode, merah = turun.

### 8.6 Panel 6 · Synthesis
Di sinilah semua bacaan di atas jadi SATU keputusan. Urutan mengisi:

| Bagian | Cara isi |
|---|---|
| **Synthesis Harian** | 1 paragraf **tulis tangan sendiri** (bukan copy hasil lensa). Ganti tanggal untuk baca/edit hari lain. |
| **Outlook per Instrumen** | Set Bullish/Bearish/Neutral per instrument aktif. Ini bias, bukan entry. |
| **Trading Journal** | Catat trade HARI ITU (jurnal mundur = fiksi, §2). Tombol **Hitung Ukuran** = sizing engine (khusus universe Phase J+): kasih Entry+SL, keluar `suggested_units`. `SKIP — RISK_CAPACITY_EXCEEDED` = budget tak cukup 1 lot → **tidak dieksekusi**, jangan geser SL. Catatan buffer ARA/ARB 1.5× muncul kalau diterapkan (risiko riil > jarak SL). |
| **Prediction Log** | MAKS 1 prediksi/hari, hanya kalau ada klaim layak diuji. Isi claim + target date + basis. Prediksi kosong > prediksi asal. |
| **Skor Prediksi Jatuh Tempo** | Prediksi lama jatuh tempo → nilai BENAR/SALAH/PARTIAL sekarang, jangan tunda. |
| **Daily Briefing → Telegram** | Opsional, setelah Panel 4–6 terisi. Merakit dari data yang SUDAH ada, tidak generate sendiri. |

**Checklist "apa yang harus saya analisa" saat sampai di synthesis:**
1. **Arah makro** (Panel 1): DXY & yield naik/turun? Itu gravitasi hari ini.
2. **Katalis di depan** (Panel 3): event HIGH berapa hari lagi? Actual vs forecast tadi malam mengubah apa?
3. **Posisi crowd** (Panel 1 funding/LS + Panel 3 COT): ada yang terlalu ramai satu sisi?
4. **Disonansi** (Panel 3): retorika vs posisi bertentangan? Kalau ya, itu headline synthesis.
5. **Struktur harga** (Panel 5): harga di mana relatif MA200 & zona? Ada sinyal valid?
6. **Konflik lensa** (Panel 4): apa yang belum sepakat? Jangan disembunyikan.
7. Tarik jadi 1 paragraf + outlook. Kalau data kunci merah/bolong → tulis
   ketidakpastiannya, jangan dipoles.

---

# BAGIAN C — LANE INVESTING (sidebar "Investing" & "Arsip")

> Sidebar dulu bernama **"Universal"** (membingungkan) → sekarang dipisah jadi
> **"Investing"** (halaman Universe — lane saham investasi) dan **"Arsip"**
> (halaman Riwayat — track record lintas-lane). Keduanya **ritme mingguan/
> kuartalan**, bukan harian (§0 poin 1). Dilarang dibuka saat ritual pagi
> kecuali melihat badge lane/kuadran (§1 "Yang DILARANG").

## 9. HALAMAN "INVESTING" (Universe & Grader)

### 9.1 Cara BACA tabel Universe
| Kolom | Cara baca |
|---|---|
| **Ticker / Sektor / Market** | Identitas emiten (IDX/US). |
| **Lane** | TRADE / BOTH / INVEST / NONE — boleh dipakai lane mana. Instrumen baru **hanya boleh INVEST/NONE** sampai lolos validasi bar-replay (§9.5). |
| **Divalidasi** | Tanggal lane di-sign-off bar-replay. Kosong = belum pernah → jangan di-TRADE-kan. |
| **Kuadran** | Hasil grader dua-sumbu (lihat §9.3). "belum digrade" = jalankan Uji Kelayakan dulu. |
| **Score** | `fund_score` mentah (fundamental). Baca komponennya di Detail, jangan cuma angkanya. |
| **Flags** | Jumlah flag integritas (UMA/suspensi dll). > 0 = ada catatan, buka detail. |

### 9.2 Cara ISI — alur intake emiten baru (urut)
1. **+ Intake Kandidat (Gelombang 1)** — metadata dasar (ticker, market,
   sektor, mcap, free float, lot size, finansial?, batas harian ARA/ARB?). Lane
   dari sini **wajib INVEST/NONE**. Ini cuma mendaftarkan, belum menilai.
2. **Uji Kelayakan (Gelombang 2)** — 3 langkah berurutan:
   - **1. Cek Integritas (UMA)** — scrape flag UMA IDX. `UMA_ACTIVE` = ada
     peringatan aktivitas tak wajar → hati-hati.
   - **2. Jalankan Grade** — hitung `fund_score` + kuadran + flags.
   - **3. Catat Keputusan** — Masuk Universe / Watchlist / Tolak + **alasan
     wajib**. Tercatat di Riwayat Keputusan Intake.
3. **Rubrik sama dengan universe existing** — tidak ada jalur istimewa.

### 9.3 Membaca Kuadran Grader
Dua sumbu: **fund_score** (kualitas fundamental) × **integrity flags** (bersih/
bermasalah).
- **INVESTABLE** — fundamental kuat + bersih. Boleh masuk pertimbangan SOP invest.
- **WATCH** — layak dipantau, belum penuh syarat.
- **SPECULATIVE** — ada daya tarik tapi flag/kualitas belum meyakinkan.
- **AVOID** — **tidak dibeli untuk lane mana pun**, termasuk invest (§6 poin 1).
  Emiten yang jadi AVOID saat sedang dipegang = agenda evaluasi hari itu juga.

Mesin memberi kuadran; kalau kamu tak setuju → **Override** (butuh alasan).
Override tampil sebagai badge terpisah, kuadran mesin tetap tersimpan.

### 9.4 Detail Emiten (Komponen B)
Tabel fundamental adaptif:
- **Emiten biasa:** Revenue, Net Income, OCF (operating cash flow), FCF (free
  cash flow) per kuartal.
- **Emiten finansial (bank):** Net Income, **CAR** (kecukupan modal, makin tinggi
  makin kuat), **NPL** (kredit macet, makin rendah makin sehat), **NIM** (margin
  bunga bersih), **LDR** (rasio pinjaman:simpanan).
- **Confidence** per baris: < 8 kuartal = LOW_CONFIDENCE (data terlalu pendek).

### 9.5 Validasi Lane (Bar-Replay Sign-off)
"Engine teruji di BTC ≠ teruji di BBRI" (Kontrak §13.1). Lane naik ke TRADE/BOTH
**hanya** setelah kamu mereview chart historis emiten itu SENDIRI (bar-replay
manual, di Panel 5), lalu **merekam** kesimpulannya di sini. Form ini cuma
MEREKAM — tidak ada validasi otomatis. Evidence wajib diisi (apa yang dicek &
kesimpulannya). Riwayatnya tampil di "Riwayat Validasi Lane".

### 9.6 Rasio Bank (Manual)
CAR/NPL/NIM/LDR **tidak ada di yfinance** → isi manual dari laporan resmi
(OJK/laporan tahunan). Tidak akan tertimpa backfill otomatis. Khusus emiten
finansial.

### 9.7 Grader Log & Kalibrasi (Komponen D)
Widget "Nilai Outcome" untuk grade berumur 3/6 bulan (pola sama Skor Prediksi).
**Revisi bobot rubrik grader HANYA lewat log ini** (kalau log menunjukkan POLA,
bukan karena satu kasus menjengkelkan) — sesi quarterly §5.

## 10. HALAMAN "ARSIP" (Riwayat) — cara baca
Track record, dibaca saat review (§3/§4), bukan diisi (isian terjadi di panel
asalnya). 4 sub-tab:
- **Synthesis** — arsip kesimpulan harian. Baca pola pikirmu dari waktu ke waktu.
- **Prediksi** — track record klaim + hasil (BENAR/SALAH/PARTIAL) + lesson.
  Hit-rate turun terus = bahan refleksi basis prediksi (§4).
- **Trading Journal** — semua entry & SKIP. Cari pola **pelanggaran SOP** (SL
  digeser? trade tanpa sinyal? approve di luar sesi pagi?), bukan pola pasar (§4).
- **4 Lensa** — arsip hasil persona per tanggal.

---

*SOP Penggunaan Aplikasi v1.1 — Bagian A (ritme) + Bagian B (cara baca panel) +
Bagian C (lane Investing). Direview bersama SOP quarterly (§5 poin terakhir).
Dokumen ini mengatur ritme & literasi panel; aturan aset tetap di SOP masing-masing.*