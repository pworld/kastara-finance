# Kastara Finance — Deployment & Mobile Access Strategy
**Versi:** 1.0 · 12 Juli 2026 · Owner: Giel
**Posisi dokumen:** mengatur DI MANA sistem berjalan dan FUNGSI MANA yang boleh diakses dari perangkat apa. Bukan spesifikasi UI detail — itu turunan setelah keputusan di sini diambil.
**Acuan:** Master Plan v1.6 (§0 spine, §5 pipeline), SOP Penggunaan Aplikasi v1.0 (§1 ritual pagi, §7 protokol), ARCHITECTURE.md §6.1 (SQLite single-writer).

---

## 0. PRINSIP — INI BUKAN SOAL UKURAN LAYAR

Pertanyaan yang benar bukan *"Telegram atau mobile-friendly?"* tapi **"fungsi mana yang boleh keluar dari meja kerja?"**

Sebagian fungsi sengaja dirancang butuh ritual, bukan kecepatan. Memindahkannya ke HP bukan peningkatan aksesibilitas — itu **penghapusan friksi yang justru disengaja.**

```
FRIKSI YANG DISENGAJA (jangan dihapus):
├── Gate 6 langkah approve sinyal  → dirancang 3 menit sadar di sesi pagi
├── Grade override + alasan wajib   → dirancang reflektif
├── Backfill preview-before-commit  → dirancang hati-hati
└── Settings/kurasi kamus tag       → dirancang lambat (§21.11 kontrak)

FRIKSI YANG TIDAK PERLU (boleh dihapus):
├── Harus duduk di meja cuma untuk BACA briefing
├── Harus nunggu pulang cuma untuk SIMPAN artikel yang ketemu
└── Harus buka laptop cuma untuk LIHAT timeline thread
```

**Aturan turunan:** yang boleh ke HP adalah **membaca** dan **menangkap** (capture). Yang tidak boleh adalah **memutuskan**.

---

## 1. MATRIKS FUNGSI × PERANGKAT

| Fungsi | Telegram | Mobile Web | Desktop | Alasan |
|---|---|---|---|---|
| Baca Daily Briefing | ✅ utama | ✅ | ✅ | Push, nol infra, sudah ada (`send_briefing.py`) |
| Cek status scraper / data pagi | ✅ ringkas | ✅ | ✅ | Read-only murni |
| Simpan artikel dari luar (kirim URL) | ✅ utama | — | ✅ | **Use case HP paling nyata** → `manual_articles` |
| Baca timeline thread | — | ✅ | ✅ | Butuh layout, tidak butuh keputusan |
| Baca output persona terakhir | — | ✅ | ✅ | Read-only |
| Baca jurnal / posisi ONGOING | — | ✅ | ✅ | Read-only |
| Konfirmasi tag SUGGESTED | — | ✅ ringan | ✅ | Reversible, bukan keputusan uang |
| Konfirmasi link thread + stance | — | ⚠️ boleh | ✅ | Reversible; tapi stance idealnya tidak terburu-buru |
| Set `for_reading` | — | ✅ | ✅ | Kurasi ringan, reversible |
| **Approve/reject sinyal** | ❌ | ❌ | ✅ **ONLY** | Gate 6 langkah = ritual sadar (SOP §1) |
| **Sizing / eksekusi** | ❌ | ❌ | ✅ ONLY | Keputusan uang |
| **Grade override** | ❌ | ❌ | ✅ ONLY | Reflektif + alasan wajib |
| **Backfill / seed** | ❌ | ❌ | ✅ ONLY | Preview-before-commit |
| **Settings (kamus tag, merge, status thread)** | ❌ | ❌ | ✅ ONLY | Kurasi lambat (§21.11) |
| **Jalankan persona (biaya LLM)** | ❌ | ⚠️ opsional | ✅ | Hemat biaya + hindari klik iseng |

**Catatan penegakan:** untuk fungsi ✅ ONLY, endpoint keputusan **tidak di-render sama sekali** di view mobile — bukan disembunyikan lewat CSS. Kalau tombolnya tidak ada, tidak ada godaan.

---

## 2. KEPUTUSAN: TELEGRAM *DAN* MOBILE WEB (bukan salah satu)

Keduanya punya peran berbeda dan tidak tumpang tindih:

**Telegram = jalur PUSH & CAPTURE**
- Sudah ada (`notify/telegram.py`, `send_briefing.py`) — nol infra baru.
- Cocok untuk: briefing pagi, alert data gagal, kirim URL artikel ke bot.
- **Batas:** jangan bangun "dashboard di Telegram" (inline keyboard untuk approve, dst). Chat bukan tempat mengambil keputusan berisiko, dan bot command yang banyak justru lebih ribet daripada web.

**Mobile Web = jalur BACA MENDALAM**
- Satu view terpisah `/m`, **bukan** membuat ketujuh tab responsif.
- Isi cukup 3 hal: (a) feed berita hari ini + konfirmasi tag/thread ringan, (b) timeline thread aktif, (c) output persona terakhir + jurnal posisi ONGOING.
- Alasan view terpisah: memoles 7 tab jadi responsif = effort besar di komponen 70% (commodity) — lihat Competitive Mapping §C1. View `/m` minimal jauh lebih murah dan lebih tepat guna.

---

## 3. DEPLOYMENT & KEAMANAN (bagian paling kritis)

> **Peringatan:** `web/app.py` saat ini **tidak punya autentikasi**, dan sejak Phase C punya endpoint tulis. Mengeksposnya ke internet publik apa adanya = siapa pun yang menemukan URL bisa menulis ke database.

### 3.1 Rekomendasi: jaringan privat, bukan expose publik

| Opsi | Cara kerja | Kelebihan | Kekurangan |
|---|---|---|---|
| **Tailscale / WireGuard** ⭐ | App tetap di mesin sendiri; HP masuk lewat VPN mesh privat | **Nol port terbuka**, nol kode auth, satu sore setup, gratis untuk pribadi | Perlu app VPN aktif di HP |
| Cloudflare Tunnel + Access | Tunnel keluar; auth di layer Cloudflare | Tidak perlu VPN di HP; auth email/SSO | Trafik lewat pihak ketiga; setup lebih ribet |
| VPS + reverse proxy + auth sendiri | Pindah app ke VPS | Selalu online walau laptop mati | **Perlu bangun auth**, HTTPS, hardening — beban paling besar |
| ~~Expose port + basic auth~~ | Port forward router | — | ❌ **HINDARI.** Rawan, mudah salah konfigurasi |

**Keputusan yang disarankan:** mulai **Tailscale**. Alasan: menyelesaikan masalah akses HP tanpa menulis satu baris kode auth, dan tanpa memindahkan database. Kalau nanti butuh selalu-online (laptop sering mati), baru pertimbangkan VPS — dan saat itu auth jadi prasyarat, bukan opsional.

### 3.2 Aturan keras: SATU DATABASE
```
❌ JANGAN: DB lokal jalan sendiri + DB VPS jalan sendiri, lalu disinkronkan.
✅ SELALU: satu file DB, satu lokasi. Pindah = pindah semua.
```
Asumsi **single-writer** di ARCHITECTURE.md §6.1 dan FLOW.md §5 langsung runtuh kalau ada dua salinan aktif. Konflik SQLite menyakitkan dan sering baru ketahuan setelah data korup berhari-hari.

**Kalau nanti pindah ke VPS:** cron scraper ikut pindah (jangan scraper lokal menulis ke DB VPS lewat jaringan). Ini juga trigger yang tercatat untuk meninjau ulang SQLite → Postgres (ARCHITECTURE §6.1).

### 3.3 Checklist sebelum akses dari luar
```
[ ] Tailscale terpasang di mesin host + HP, koneksi terverifikasi
[ ] Flask bind ke interface Tailscale / localhost — BUKAN 0.0.0.0 publik
[ ] Backup DB otomatis sebelum mulai akses jarak jauh (file SQLite, salin harian)
[ ] Verifikasi: dari jaringan luar TANPA VPS/VPN, dashboard TIDAK bisa dibuka
[ ] .env (API key OpenRouter, dst) tidak ikut ter-expose di direktori statis
```

---

## 4. URUTAN EKSEKUSI (paling murah dulu)

```
TAHAP 1 — AKSES (satu sore, NOL kode)
[ ] Tailscale setup + checklist §3.3
[ ] Buka dashboard desktop apa adanya dari HP
[ ] PAKAI 1–2 minggu. Catat: fungsi apa yang benar-benar dibutuhkan di luar?
    (jangan menebak — biarkan pemakaian yang memberi tahu)

TAHAP 2 — TELEGRAM (kecil, tinggi manfaat)
[ ] Briefing pagi via Telegram (sudah ada — pastikan jadwalnya pas)
[ ] Bot handler: kirim URL → simpan ke manual_articles
[ ] (opsional) Alert kalau scraper gagal total

TAHAP 3 — VIEW /m (hanya untuk yang TERBUKTI sering dipakai di Tahap 1)
[ ] Route /m read-only: feed berita, timeline thread, persona terakhir, jurnal
[ ] Konfirmasi tag/thread + for_reading (light write, reversible)
[ ] Endpoint keputusan TIDAK di-render di view ini
[ ] Test: pastikan tidak ada jalur approve/backfill/settings yang bocor ke /m

TAHAP 4 — VPS (hanya kalau perlu selalu-online)
[ ] Prasyarat: auth beneran, HTTPS, backup otomatis
[ ] DB + cron pindah SEMUA (aturan §3.2)
[ ] Tinjau ulang SQLite → Postgres kalau muncul writer paralel
```

---

## 5. RISIKO YANG DIPANTAU

| Risiko | Tanda awal | Mitigasi |
|---|---|---|
| **Ritual pagi terkikis** | Mulai "cukup baca briefing di HP" lalu skip sesi desktop | Briefing = pengingat, bukan pengganti. Kalau 3 hari berturut sesi desktop terlewat, itu bukan masalah UI — itu masalah disiplin (SOP §7) |
| **Keputusan merembes ke HP** | Muncul keinginan "approve cepat dari HP saja" | Endpoint tidak ada di /m. Kalau tergoda menambahkannya, baca ulang SOP §7 + Visi Pengalaman Bagian 4 |
| **Dua database** | "Sementara pakai DB lokal dulu" saat VPS bermasalah | Aturan §3.2 — tidak ada pengecualian |
| **Expose tanpa sadar** | Flask bind 0.0.0.0 + port forward "sementara" | Checklist §3.3 dijalankan tiap kali deployment berubah |
| **Effort bocor ke 70%** | Menghabiskan minggu memoles UI mobile | View /m minimal saja. Polish UI = ranah TradingView (Competitive Mapping §C1) |

---

## 6. KAITAN SOP

Tambahan ke SOP Penggunaan Aplikasi v1.0:
- **§1 (ritual pagi):** tetap desktop. Briefing Telegram boleh dibaca lebih dulu, tapi tidak menggantikan sesi.
- **§3 (weekly):** cek backup DB berjalan; verifikasi akses luar masih tertutup dari jaringan publik.
- **§7 (protokol tidak normal):** tambah baris — *"Muncul keinginan approve sinyal dari HP → itu sinyal emosi/terburu-buru, bukan kebutuhan fitur. Tunggu sesi pagi berikutnya."*

---

## 7. RAILWAY DEPLOYMENT (override, 31 Jul 2026)

> **Catatan transparansi:** Giel eksplisit minta deploy langsung ke Railway
> (cloud publik) — bukan Tailscale dulu seperti urutan §4 di atas. Ini
> keputusan sadar Giel sendiri, bukan retraksi rekomendasi §3/§4 — kalau
> nanti butuh akses "nol setup, satu sore" lagi di konteks lain, §3/§4 tetap
> berlaku. Auth (§Auth `web/app.py`) sudah ada sejak migrasi Vue, jadi
> prasyarat "auth beneran" utk expose publik (§3.1 baris VPS) sudah
> terpenuhi lebih dulu — bukan ditambah khusus utk Railway.

### 7.1 Keputusan: tetap SQLite, bukan Postgres

Trigger pindah Postgres di ARCHITECTURE §6.1 ada 3: banyak user concurrent,
banyak proses penulis bersamaan, atau butuh hosting cloud managed. Railway
menyalakan alasan ketiga, tapi **tidak butuh migrasi DB** — cukup attach
**Railway Volume** (disk persisten) ke service dan arahkan `KASTARA_DB_PATH`
ke sana. App ini tetap single-user/single-writer (cron pipeline + 1 sesi
browser Giel), jadi tidak ada alasan nyata untuk Postgres (concurrent write,
managed backup/replikasi) — itu semua biaya tanpa manfaat riil di sini.

### 7.2 Yang sudah disiapkan di repo (31 Jul 2026)

- **`Dockerfile`** (multi-stage): stage 1 (`node:22-alpine`) build
  `web/frontend/` → `dist/`; stage 2 (`python:3.12-slim`) install
  `requirements.txt` + copy source + copy `dist/` dari stage 1. `CMD`
  jalankan `gunicorn web.app:app --bind 0.0.0.0:$PORT --workers 2
  --timeout 300` — timeout digenerouskan krn `/api/run_daily_now` (trigger
  pipeli hari-ini dari Snapshot) bisa lama (fetch semua sumber eksternal).
- **`.dockerignore`** — exclude `.venv/`, `node_modules/`, `*.db`,
  `kastara-finance-data/`, `.git/`, `.env`, `prompts/persona_*.txt`, `logs/`,
  dan `*.md` (docs tidak dibaca app saat runtime).
- **`requirements.txt`** — tambah `gunicorn`.
- **`web/app.py`** — `init_db()` dipindah ke level modul (bukan cuma di
  `main()`) — WAJIB, karena gunicorn import modul langsung tanpa pernah
  eksekusi `if __name__ == "__main__"`. Tanpa ini, Volume kosong di deploy
  pertama akan gagal di query API pertama (tabel belum ada). Idempotent,
  jadi tidak masalah tetap dipanggil tiap start proses.
- **`tests/test_web_app.py`** — set `KASTARA_DB_PATH` ke file temp SEBELUM
  import `web.app` (perubahan di atas berarti import modul ini sekarang
  memicu `init_db()` — tanpa guard ini, test akan diam-diam kena ke DB
  produksi asli lewat `.env` lokal Giel).
- **Diverifikasi lokal**: `docker build` sukses, container dijalankan
  (`docker run` + env var dummy), `/` (SPA) 200, `/api/auth/login` +
  `/api/auth/status` + `/api/latest` (authenticated) semua jalan benar
  end-to-end di dalam image. Image test dihapus setelah verifikasi
  (bukan ditinggal di disk).

### 7.3 Langkah setup Railway (belum dieksekusi — butuh akun/login Giel sendiri)

```
[ ] 1. Buat project baru di Railway, hubungkan repo ini (atau railway up
       dari CLI kalau tidak lewat GitHub).
[ ] 2. Attach Volume ke service, mount path mis. /data.
[ ] 3. Set environment variables (Settings -> Variables):
       - KASTARA_DB_PATH=/data/kastara-finance.db
       - DASHBOARD_PASSWORD=<isi sendiri, JANGAN aku yang isi -- kredensial>
       - FLASK_SECRET_KEY=<isi sendiri, string acak panjang -- WAJIB diisi
         eksplisit di Railway, beda dari lokal yang boleh auto-generate;
         kalau kosong, tiap redeploy invalidate semua sesi login>
       - FRED_API_KEY, OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN,
         TELEGRAM_CHAT_ID, COINALYZE_API_KEY, RISK_CAPITAL_IDR,
         RISK_CAPITAL_USD (sama seperti .env lokal, lihat .env.example)
[ ] 4. Deploy pertama kali (Volume masih kosong) -- pastikan container hidup
       & /api/auth/status merespons (schema kosong ter-buat otomatis lewat
       init_db() level-modul di atas).
[ ] 5. Fresh start (keputusan Giel 4 Agustus 2026) -- DB lokal lama TIDAK
       diupload, tetap jadi data dev di mesin lokal. Volume Railway mulai
       kosong, init_db() level-modul otomatis buat 30 tabel fresh.
[ ] 6. ~~Tambah service KEDUA (cron)~~ -- TIDAK DIPAKAI. Lihat §8: Railway
       Volume cuma bisa attach ke SATU service (dikonfirmasi dari docs
       Railway sendiri, 4 Agustus 2026) -- service kedua akan punya Volume
       terpisah = DB terpisah, melanggar aturan §3.2 "SATU DATABASE".
       Gantinya: trigger manual via Telegram bot (§8).
[ ] 7. Verifikasi: login dari browser publik, cek /m + PWA install dari HP
       (start_url sudah /m, lihat ROADMAP.md 31 Jul 2026), cek Trigger
       Berita dari Snapshot benar-benar mengisi data.
```

### 7.4 Yang TIDAK dikerjakan di sesi ini

Migrasi Postgres (dianggap tidak perlu, §7.1). Upload DB lokal lama ke
Railway (fresh start dipilih, §7.3 langkah 5). Cron via service Railway
terpisah (tidak bisa krn constraint Volume, §8).

---

## 8. CRON HARIAN via TELEGRAM (bukan service kedua, 4 Agustus 2026)

### 8.0 Kenapa bukan Railway Cron Job biasa

Rencana awal §7.3 langkah 7 (service kedua khusus cron, custom start command
`python -m pipeline.run_daily`, Railway Cron Schedule) **tidak bisa dipakai**
utk app ini: dicek langsung ke docs Railway saat eksekusi (4 Agustus 2026) --
**satu Volume cuma bisa attach ke satu service**. Service kedua akan
otomatis butuh Volume-nya sendiri (DB SQLite terpisah, kosong) -- itu
melanggar aturan keras §3.2 "SATU DATABASE, pindah = pindah semua", bukan
sekadar duplikasi data tapi 2 sumber kebenaran yang diam-diam divergen.

### 8.1 Solusi: trigger manual via bot Telegram (2 arah, webhook, 3 command)

Daripada Railway Cron Job (butuh service kedua), pipeline harian di-trigger
lewat command Telegram yang memanggil endpoint di SERVICE YANG SAMA (yang
sudah punya Volume/DB asli) -- bukan proses terpisah, bukan long-polling.
- **`POST /api/telegram/webhook`** (`web/app.py`) -- exempt dari session
  auth (Telegram yang panggil, bukan browser Giel), tapi digerbangi 2 lapis:
  (1) `chat_id` pesan HARUS masuk allowlist `TELEGRAM_CHAT_IDS` (jamak,
  koma-pisah -- fallback ke `TELEGRAM_CHAT_ID` tunggal kalau blm di-set,
  abaikan diam-diam kalau tidak masuk daftar, tidak bocorkan info ke
  pengirim asing), (2) opsional secret token header
  `X-Telegram-Bot-Api-Secret-Token` (kalau `TELEGRAM_WEBHOOK_SECRET`
  diisi) -- pertahanan tambahan drpd cuma chat_id.
- **3 command** (spec Giel "Telegram Bot Commands v1.0", 5-6 Agustus 2026):
  - `/start` -- daftar command.
  - `/status` -- baca `daily_market` terbaru (kapan run_daily terakhir) +
    tanggal terbaru `asset_ohlcv`/`daily_news` MASING-MASING (bukan
    diasumsikan sinkron) + event `econ_calendar` mendatang + sinyal
    `trade_signals` pending approve + thread link SUGGESTED nunggu review.
  - `/run_daily` -> jalankan `run_daily_mod.run_daily()` di **background
    thread** (bukan langsung di handler) -- Telegram retry kirim update
    kalau webhook tidak balas cepat, dan `run_daily()` bisa lama (fetch
    semua sumber eksternal). Handler balas ack cepat ("⏳ run_daily
    dimulai..."), baru kirim pesan susulan (format SAMA seperti `/status`)
    setelah proses beneran selesai, reuse `notify/telegram.py::send_message()`.
    Digerbangi **lock file** (`$TMPDIR/kastara_run_daily.lock`, isi
    PID+timestamp, stale >30 menit diambil alih -- cegah 2 run bersamaan,
    SQLite single-writer §6.1) + **rate limit 5 menit** antar-trigger
    (file terpisah, cegah spam trigger BERURUTAN stlh run sebelumnya
    selesai).
- **Command lain SENGAJA tidak dibangun** (`approve/reject sinyal`,
  `backfill`, `settings/grader override`) -- per spec §1: itu operasi yang
  butuh gate/ritual sadar (anti-impulsif, friksi yang disengaja), bukan
  operasi pipa idempoten seperti `run_daily`/`run_analysis` (well,
  `run_analysis` juga belum dibangun sbg command -- ditandai "boleh" di
  spec tapi tidak masuk 3 command yang benar2 dispesifikasikan, jadi belum
  diimplementasikan, bisa ditambah nanti kalau terbukti perlu).
- **Kenapa TETAP webhook, bukan long-polling+systemd** (draft awal spec
  minta VPS terpisah): Railway SUDAH jadi host always-on -- prasyarat spec
  itu sendiri sudah terpenuhi. Long-polling+systemd butuh proses ke-2 yang
  jalan terus, yang di Railway berarti service ke-2 -- kena blocker Volume-
  cuma-1-service yang SAMA PERSIS yang menggagalkan rencana cron-service
  di atas (§8.0). Webhook di service yang sama menghindari masalah ini
  sepenuhnya.

### 8.2 Setup (aksi manual, butuh token/domain asli Giel)

```
[ ] 1. Set env var di Railway (Settings -> Variables), sama seperti .env:
       TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (sudah ada dari Daily Briefing
       kalau sudah pernah setup lokal). Tambah juga:
       TELEGRAM_WEBHOOK_SECRET=<string acak, rekomendasi tapi opsional>
       TELEGRAM_CHAT_IDS=<opsional, koma-pisah kalau mau >1 chat_id boleh
       trigger bot -- kalau kosong fallback ke TELEGRAM_CHAT_ID tunggal>
[ ] 2. Setelah service live & domain publik ada (§7.3 langkah 4/7), daftar-
       kan webhook ke Telegram SEKALI (dari mesin lokal, ganti <TOKEN>/
       <URL>/<SECRET>):
       curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
         -d "url=https://<domain-railway-kamu>/api/telegram/webhook" \
         -d "secret_token=<SECRET, sama dgn TELEGRAM_WEBHOOK_SECRET>"
[ ] 3. Verifikasi: kirim "/run_daily" dari akun Telegram-mu ke bot -- balasan
       ack harus muncul dalam hitungan detik, lalu ringkasan hasil beberapa
       saat kemudian (durasi run_daily() beneran, network fetch semua sumber).
[ ] 4. Cek `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo` kalau
       mau pastikan webhook ter-register benar (lihat field "url" & tidak
       ada "last_error_message").
```

### 8.3 Yang TIDAK dikerjakan

Command Telegram lain selain `/run_daily`. Rate-limiting/anti-spam di
endpoint webhook (dianggap tidak perlu -- gerbang chat_id sudah cukup ketat
utk app single-user ini). Konfirmasi 2 langkah sebelum trigger (mis. "yakin?"
sebelum run) -- `/run_daily` dianggap aman dipicu langsung, sama seperti
tombol "Trigger Berita (Sekarang)" di Snapshot yang juga tanpa konfirmasi.

## 9. PROMPT PERSONA DI RAILWAY (10 Agustus 2026)

`prompts/persona_<lens>.txt` (Panel 4, 4 Analisa AI) sengaja gitignored
(`prompts/README.md`) -- isinya cara berpikir/analisa Giel sendiri, sama
prinsip dengan `.env`. Konsekuensinya: `git push` TIDAK PERNAH membawa
file-file ini ke Railway. Kalau di-upload manual ke `prompts/` biasa
(bukan di Volume), hilang lagi begitu deploy berikutnya -- filesystem app
di luar Volume dibangun ULANG dari image tiap deploy, cuma Volume yang
persisten (pelajaran yang sama dgn kenapa cron service kedua ditolak §8.0).

**Solusi**: `llm/persona_analysis.py` sekarang baca env var opsional
`KASTARA_PROMPTS_DIR` -- kosong (default) = pakai `prompts/` di source
tree seperti biasa (dev lokal, TIDAK berubah). Diisi = pakai folder itu,
diarahkan ke Volume yang SAMA dgn `KASTARA_DB_PATH` supaya prompt
bertahan lintas deploy.

```
[ ] 1. Set env var Railway: KASTARA_PROMPTS_DIR=/data/prompts
       (ganti /data kalau mount path Volume-mu beda -- cek dari
       KASTARA_DB_PATH yang sudah ada, biasanya folder yang sama)
[ ] 2. Buat folder-nya dulu + upload 4 file prompt (SEKALI, dari mesin
       lokal, jalan lewat railway ssh -- pola sama migrasi data
       sebelumnya):
       railway ssh -- "mkdir -p /data/prompts"
       railway ssh -- "cat > /data/prompts/persona_gema.txt" < prompts/persona_gema.txt
       railway ssh -- "cat > /data/prompts/persona_leon.txt" < prompts/persona_leon.txt
       railway ssh -- "cat > /data/prompts/persona_akela.txt" < prompts/persona_akela.txt
       railway ssh -- "cat > /data/prompts/persona_rivan.txt" < prompts/persona_rivan.txt
[ ] 3. Deploy staged env var change (Railway tidak auto-apply).
[ ] 4. Verifikasi: GET /api/persona/status di Railway harus balikin
       semua 4 lens true. Coba "Jalankan Analisa" beneran di Panel 4.
```

Kalau nanti prompt di-edit di lokal, ulangi langkah 2 utk lens yang
berubah (bukan proses otomatis -- personal & jarang berubah, tidak worth
dibikin pipeline).

---

*Deployment & Mobile Access Strategy v1.0 — mulai dari Tahap 1, biarkan pemakaian nyata yang menentukan Tahap 3. Pakai dulu, bangun setelah tahu.*
*§7 (Railway) ditambahkan 31 Jul 2026 sebagai override eksplisit Giel — lihat catatan transparansi di atas.*
*§8 (Telegram cron trigger) ditambahkan 4 Agustus 2026 setelah deploy pertama Giel menemukan constraint Volume-per-service Railway di lapangan.*
*§9 (Prompt persona di Volume) ditambahkan 10 Agustus 2026 -- Giel minta prompt yang sudah ditulis jadi aktif & ter-upload ke produksi.*