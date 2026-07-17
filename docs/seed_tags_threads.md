# Kastara Finance — Seed Tags & Threads (Init)

Dipakai untuk mengisi `tag_dictionary` dan mengusulkan thread awal, supaya Giel
tidak mulai dari kamus kosong. Tag = di-seed penuh (vocabulary, aman
berlebih). Thread = kandidat saja (aktivasi manual, hormati batas 7 ACTIVE).
Prinsip yang dijaga: tag deskriptif (tidak berarah), thread berarah (punya
`current_read` yang bisa salah). Semua tag lowercase, `-` untuk spasi, `sym:`
wajib region-prefix.

Diimport lewat `pipeline/seed_tags.py` (`python -m pipeline.seed_tags`).
**17 Jul 2026**: dijalankan sekali dengan kandidat thread B–H sebagai
**DORMANT** (bukan ACTIVE) — DB produksi sudah punya 5 thread ACTIVE dengan
judul/arah sendiri yang beda dari kandidat generik di sini (mis. "Rezim Warsh
Dovish" vs Kandidat A "Hawkish"), jadi tidak ada kandidat yang diaktifkan
otomatis. `who:purbaya` SENGAJA di-skip dari seed (lihat Aturan Pakai #3 —
jabatan/ejaan belum diverifikasi).

## BAGIAN 1 — SEED TAGS (langsung masuk `tag_dictionary`)

### facet: geo (geografi)

```
geo:us          Amerika Serikat
geo:id          Indonesia
geo:cn          China
geo:eu          Uni Eropa / kawasan euro
geo:jp          Jepang
geo:uk          Inggris
geo:in          India
geo:global      lintas negara / global
geo:asia        kawasan Asia (regional)
```

### facet: org (institusi)

```
org:fed         Federal Reserve
org:fomc        FOMC (komite kebijakan Fed)
org:bi          Bank Indonesia
org:ojk         OJK
org:kemenkeu    Kementerian Keuangan RI
org:gov-id      Pemerintah RI (eksekutif)
org:pboc        People's Bank of China
org:ecb         European Central Bank
org:boj         Bank of Japan
org:imf         IMF
org:worldbank   World Bank
org:comex       COMEX
org:lbma        LBMA
org:idx         Bursa Efek Indonesia (institusi)
```

### facet: who (tokoh)

```
who:warsh       Kevin Warsh (Fed Chair)
who:powell      Jerome Powell
who:waller      Christopher Waller
who:williams    John Williams (NY Fed)
who:logan       Lorie Logan (Dallas Fed)
who:trump       Donald Trump
who:prabowo     Prabowo Subianto
who:purbaya     (pejabat fiskal/moneter ID — sesuaikan; DI-SKIP saat seed
                 17 Jul 2026, belum diverifikasi jabatan/ejaan)
```

### facet: sym (instrumen — WAJIB region-prefix)

```
sym:btc         Bitcoin
sym:eth         Ethereum
sym:xau         Emas (gold spot)
sym:dxy         US Dollar Index
sym:us10y       US Treasury 10Y
sym:vix         VIX
sym:sp500       S&P 500
sym:idx         IHSG (indeks)
sym:usd-idr     USD/IDR
sym:usd-jpy     USD/JPY
sym:id-bbca     BBCA
sym:id-bbri     BBRI
sym:id-bmri     BMRI
sym:id-tlkm     TLKM
sym:us-tsla     Tesla
sym:us-nvda     Nvidia
sym:us-aapl     Apple
```

### facet: theme (tema kebijakan/pasar — deskriptif, bukan arah)

```
theme:rate-policy       kebijakan suku bunga
theme:inflation         inflasi / CPI / PCE / PPI
theme:foreign-flow      arus modal asing
theme:liquidity         likuiditas (net liquidity, QT/QE)
theme:geopolitics       geopolitik / konflik / sanksi
theme:fiscal            kebijakan fiskal / anggaran / defisit
theme:earnings          laba korporasi / musim laporan
theme:commodities       komoditas (energi, logam, pangan)
theme:currency          nilai tukar / valas
theme:credit            kredit / spread / obligasi
theme:employment        ketenagakerjaan / NFP / pengangguran
theme:trade             perdagangan / tarif / neraca dagang
theme:crypto-regulation regulasi kripto
theme:etf-flow          arus ETF (BTC/emas)
```

### facet: sec (sektor — untuk saham individual Phase J)

```
sec:banking         perbankan
sec:consumer        konsumer / ritel
sec:energy          energi
sec:mining          pertambangan
sec:automotive      otomotif
sec:technology      teknologi
sec:property        properti
sec:telco           telekomunikasi
sec:healthcare      kesehatan
sec:industrials     industri
```

## BAGIAN 2 — KANDIDAT THREAD (JANGAN aktifkan semua — pilih yang sedang dilacak)

Tiap kandidat sudah punya `current_read` (bisa salah) + `persona_tags` + `tags`
awal. Aktifkan MAKS 7. Sisanya biarkan sebagai catatan sampai relevan.

### Kandidat A — "Rezim Warsh Hawkish" ⭐ (sudah aktif — pertahankan)

```
current_read : Fed di bawah Warsh bergerak lebih ketat; hike masih di meja.
persona_tags : GEMA, AKELA
tags         : who:warsh, org:fed, org:fomc, theme:rate-policy, geo:us
```

### Kandidat B — "Inflasi Global Belum Jinak" ⭐ (disarankan aktifkan)

```
current_read : Inflasi lintas negara masih di atas target; tekanan bunga belum reda.
persona_tags : GEMA, AKELA
tags         : theme:inflation, geo:global, geo:us, geo:in, geo:cn
```

### Kandidat C — "Outflow Asing dari IHSG"

```
current_read : Asing net distribusi dari ekuitas Indonesia; domestik menyerap.
persona_tags : GEMA, LEON
tags         : theme:foreign-flow, sym:idx, sym:usd-idr, geo:id
```

### Kandidat D — "Arah Fiskal Prabowo"

```
current_read : Arah fiskal pemerintahan baru ekspansif; dampak ke defisit & SBN.
persona_tags : LEON
tags         : who:prabowo, org:gov-id, org:kemenkeu, theme:fiscal, geo:id
```

### Kandidat E — "BI vs The Fed (Divergensi Kebijakan)"

```
current_read : BI terjepit antara menahan IDR dan mendukung pertumbuhan saat Fed hawkish.
persona_tags : GEMA, LEON
tags         : org:bi, org:fed, theme:rate-policy, sym:usd-idr, geo:id
```

### Kandidat F — "De-dollarization / Emas Bank Sentral"

```
current_read : Bank sentral non-Barat mengakumulasi emas menjauh dari dolar.
persona_tags : GEMA, RIVAN
tags         : theme:commodities, sym:xau, org:pboc, org:comex, geo:global
```

### Kandidat G — "AI Capex Bubble"

```
current_read : Belanja AI mega-cap tak akan hasilkan profit sepadan; koreksi menanti.
persona_tags : AKELA, RIVAN
tags         : theme:earnings, sec:technology, sym:us-nvda, geo:us
```

### Kandidat H — "Financial Repression 2026" (thread payung tesis Giel)

```
current_read : Inflasi menggerus utang riil; aset riil jadi penerima transfer kekayaan.
persona_tags : GEMA, RIVAN
tags         : theme:inflation, theme:liquidity, theme:fiscal, sym:xau, geo:global
catatan      : Thread tesis jangka panjang — hati-hati jadi confirmation funnel.
               Justru thread ini paling butuh disiplin mencatat bukti KONTRA.
```

### CATATAN KONVERSI (dari thread lama Giel yang keliru jadi tag)

```
"The Fed"              → BUKAN thread. Jadi tag org:fed (+ org:fomc).
"IHSG"                 → BUKAN thread. Jadi tag sym:idx (+ theme:foreign-flow).
"Pemerintah Indonesia" → BUKAN thread. Pecah: org:gov-id + who:prabowo.
                         Kalau mau thread, pakai Kandidat D (berarah).
```

> **Catatan 17 Jul 2026**: konversi di atas ditulis mengasumsikan judul thread
> lama yang generik ("The Fed", "IHSG", dst). DB produksi saat seed dijalankan
> ternyata sudah punya 5 thread ACTIVE dengan judul & arah tesis SENDIRI
> (mis. "Rezim Warsh Dovish", "IHSG Menguat, Saham Bullish") yang tidak cocok
> 1:1 dengan asumsi ini — konversi manual (kalau memang mau dilakukan) jadi
> keputusan Giel sendiri via Settings, BUKAN dijalankan otomatis oleh
> `seed_tags.py` (skrip ini tidak pernah menyentuh/menutup thread yang sudah
> ada, cuma menambah tag & kandidat DORMANT baru).

## ATURAN PAKAI

1. Import seluruh BAGIAN 1 ke `tag_dictionary` (aman berlebih).
2. Aktifkan Kandidat A + B dulu (paling relevan dengan berita saat ini).
   Tambah C–H hanya saat narasinya benar-benar sedang dilacak. Maks 7 ACTIVE.
3. `who:purbaya` dan beberapa entri: verifikasi jabatan/ejaan saat seed —
   jangan pakai kalau tidak yakin.
4. Tag baru tetap lahir dari pemakaian (ketik-Enter di News). Seed ini cuma
   titik awal, bukan kamus final.
