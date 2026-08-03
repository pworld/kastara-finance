"""Seed tag_dictionary + kandidat thread awal (Addendum C §21.12).

Sumber: docs/seed_tags_threads.md. Tag = seed penuh (aman berlebih, kamus
dimulai kosong). Thread = SEMUA 8 kandidat dibuat sbg DORMANT -- SENGAJA
tidak ada yang diaktifkan otomatis (17 Jul 2026: DB produksi sudah punya 5
thread ACTIVE dgn judul & arah tesis sendiri yang beda dari kandidat generik
di sini, mis. thread real "Rezim Warsh Dovish" vs Kandidat A yang menulis
"Hawkish" -- aktivasi/penyesuaian tetap keputusan Giel lewat Settings, bukan
skrip ini). Skrip ini TIDAK PERNAH menyentuh/menutup thread yang sudah ada.

`who:purbaya` SENGAJA di-skip (jabatan/ejaan belum diverifikasi, lihat
Aturan Pakai #3 di docs/seed_tags_threads.md).

Idempotent: create_tag/save_thread dicek dulu (exact-match canonical/title),
aman di-re-run -- pola sama pipeline/seed_context_weight.py.

Pakai:
    python -m pipeline.seed_tags
"""
from __future__ import annotations

from db.connection import get_connection, init_db
from web.writes import apply_tag, create_tag, patch_thread, resolve_tag, save_thread

# ---------- BAGIAN 1: tags (facet, [(canonical, description), ...]) ----------

TAGS: dict[str, list[tuple[str, str]]] = {
    "geo": [
        ("geo:us", "Amerika Serikat"), ("geo:id", "Indonesia"), ("geo:cn", "China"),
        ("geo:eu", "Uni Eropa / kawasan euro"), ("geo:jp", "Jepang"), ("geo:uk", "Inggris"),
        ("geo:in", "India"), ("geo:global", "lintas negara / global"), ("geo:asia", "kawasan Asia (regional)"),("geo:kr", "geo", "Korea Selatan"),
    ],
    "org": [
        ("org:fed", "Federal Reserve"), ("org:fomc", "FOMC (komite kebijakan Fed)"),
        ("org:bi", "Bank Indonesia"), ("org:ojk", "OJK"), ("org:kemenkeu", "Kementerian Keuangan RI"),
        ("org:gov-id", "Pemerintah RI (eksekutif)"), ("org:pboc", "People's Bank of China"),
        ("org:ecb", "European Central Bank"), ("org:boj", "Bank of Japan"), ("org:imf", "IMF"),
        ("org:worldbank", "World Bank"), ("org:comex", "COMEX"), ("org:lbma", "LBMA"),
        ("org:idx", "Bursa Efek Indonesia (institusi)"),("org:opec", "org", "OPEC / OPEC+"),
    ],
    "who": [
        ("who:warsh", "Kevin Warsh (Fed Chair)"), ("who:powell", "Jerome Powell"),
        ("who:waller", "Christopher Waller"), ("who:williams", "John Williams (NY Fed)"),
        ("who:logan", "Lorie Logan (Dallas Fed)"), ("who:trump", "Donald Trump"),
        ("who:prabowo", "Prabowo Subianto"),
        ("who:ueda",     "who", "Kazuo Ueda — Gubernur BoJ"),
        ("who:takaichi", "who", "Sanae Takaichi — PM Jepang"),
        ("who:katayama", "who", "Satsuki Katayama — Menkeu Jepang"),
        # who:purbaya SENGAJA tidak dimasukkan -- lihat docstring modul.
    ],
    "sym": [
        ("sym:btc", "Bitcoin"), ("sym:eth", "Ethereum"), ("sym:xau", "Emas (gold spot)"),
        ("sym:dxy", "US Dollar Index"), ("sym:us10y", "US Treasury 10Y"), ("sym:vix", "VIX"),
        ("sym:sp500", "S&P 500"), ("sym:idx", "IHSG (indeks)"), ("sym:usd-idr", "USD/IDR"),
        ("sym:usd-jpy", "USD/JPY"), ("sym:id-bbca", "BBCA"), ("sym:id-bbri", "BBRI"),
        ("sym:id-bmri", "BMRI"), ("sym:id-tlkm", "TLKM"), ("sym:us-tsla", "Tesla"),
        ("sym:us-nvda", "Nvidia"), ("sym:us-aapl", "Apple"),("sym:oil",   "sym", "Minyak mentah (Brent/WTI)"),("sym:kospi", "sym", "KOSPI — indeks Korea Selatan"),("sym:jgb10", "sym", "JGB 10 tahun"),
    ],
    "theme": [
        ("theme:rate-policy", "kebijakan suku bunga"), ("theme:inflation", "inflasi / CPI / PCE / PPI"),
        ("theme:foreign-flow", "arus modal asing"), ("theme:liquidity", "likuiditas (net liquidity, QT/QE)"),
        ("theme:geopolitics", "geopolitik / konflik / sanksi"), ("theme:fiscal", "kebijakan fiskal / anggaran / defisit"),
        ("theme:earnings", "laba korporasi / musim laporan"), ("theme:commodities", "komoditas (energi, logam, pangan)"),
        ("theme:currency", "nilai tukar / valas"), ("theme:credit", "kredit / spread / obligasi"),
        ("theme:employment", "ketenagakerjaan / NFP / pengangguran"), ("theme:trade", "perdagangan / tarif / neraca dagang"),
        ("theme:crypto-regulation", "regulasi kripto"), ("theme:etf-flow", "arus ETF (BTC/emas)"),
    ],
    "sec": [
        ("sec:banking", "perbankan"), ("sec:consumer", "konsumer / ritel"), ("sec:energy", "energi"),
        ("sec:mining", "pertambangan"), ("sec:automotive", "otomotif"), ("sec:technology", "teknologi"),
        ("sec:property", "properti"), ("sec:telco", "telekomunikasi"), ("sec:healthcare", "kesehatan"),
        ("sec:industrials", "industri"),("sec:semiconductor", "sec", "Semikonduktor / memori"),("sec:defense","sec", "Pertahanan / defense contractor"),
    ],
}

# ---------- BAGIAN 2: kandidat thread (SEMUA dibuat DORMANT, lihat docstring) ----------

CANDIDATES = [
    {
        "title": "Rezim Warsh Hawkish",
        "current_read": "Fed di bawah Warsh bergerak lebih ketat; hike masih di meja.",
        "persona_tags": ["GEMA", "AKELA"],
        "tags": ["who:warsh", "org:fed", "org:fomc", "theme:rate-policy", "geo:us"],
    },
    {
        "title": "Inflasi Global Belum Jinak",
        "current_read": "Inflasi lintas negara masih di atas target; tekanan bunga belum reda.",
        "persona_tags": ["GEMA", "AKELA"],
        "tags": ["theme:inflation", "geo:global", "geo:us", "geo:in", "geo:cn"],
    },
    {
        "title": "Outflow Asing dari IHSG",
        "current_read": "Asing net distribusi dari ekuitas Indonesia; domestik menyerap.",
        "persona_tags": ["GEMA", "LEON"],
        "tags": ["theme:foreign-flow", "sym:idx", "sym:usd-idr", "geo:id"],
    },
    {
        "title": "Arah Fiskal Prabowo",
        "current_read": "Arah fiskal pemerintahan baru ekspansif; dampak ke defisit & SBN.",
        "persona_tags": ["LEON"],
        "tags": ["who:prabowo", "org:gov-id", "org:kemenkeu", "theme:fiscal", "geo:id"],
    },
    {
        "title": "BI vs The Fed (Divergensi Kebijakan)",
        "current_read": "BI terjepit antara menahan IDR dan mendukung pertumbuhan saat Fed hawkish.",
        "persona_tags": ["GEMA", "LEON"],
        "tags": ["org:bi", "org:fed", "theme:rate-policy", "sym:usd-idr", "geo:id"],
    },
    {
        "title": "De-dollarization / Emas Bank Sentral",
        "current_read": "Bank sentral non-Barat mengakumulasi emas menjauh dari dolar.",
        "persona_tags": ["GEMA", "RIVAN"],
        "tags": ["theme:commodities", "sym:xau", "org:pboc", "org:comex", "geo:global"],
    },
    {
        "title": "AI Capex Bubble",
        "current_read": "Belanja AI mega-cap tak akan hasilkan profit sepadan; koreksi menanti.",
        "persona_tags": ["AKELA", "RIVAN"],
        "tags": ["theme:earnings", "sec:technology", "sym:us-nvda", "geo:us"],
    },
    {
        "title": "Financial Repression 2026",
        "current_read": "Inflasi menggerus utang riil; aset riil jadi penerima transfer kekayaan.",
        "persona_tags": ["GEMA", "RIVAN"],
        "tags": ["theme:inflation", "theme:liquidity", "theme:fiscal", "sym:xau", "geo:global"],
    },
{
        "title": "Perang AS-Iran & Premium Risiko Energi",
        "current_read": (
            "Konflik AS/Israel-Iran sejak Feb 2026 belum reda; gangguan Selat Hormuz "
            "menaruh premium risiko permanen di harga energi dan menekan disinflasi global."
        ),
        "persona_tags": ["GEMA", "AKELA"],
        "tags": ["theme:geopolitics", "theme:commodities", "sym:oil",
                 "geo:us", "geo:global", "who:trump"],
        "catatan_fakta": (
            "Operation Epic Fury 28 Feb 2026 (AS+Israel). Eskalasi berlanjut: serangan "
            "AS 8 Jul, waiver sanksi minyak Iran dicabut efektif 17 Jul. Brent sempat "
            "$76.48 (tertinggi sejak 23 Jun). Arus tanker Hormuz (~1/5 pasokan minyak "
            "global) sempat terhenti; Aramco Ras Tanura sempat dihentikan."
        ),
    },
    {
        "title": "Gelembung Semikonduktor Asia Pecah",
        "current_read": (
            "Euforia AI-semikonduktor Asia berbalik jadi deleveraging; koreksi KOSPI "
            "adalah peringatan dini untuk pasar tech-heavy lain, bukan kejadian lokal."
        ),
        "persona_tags": ["AKELA", "RIVAN"],
        "tags": ["sec:semiconductor", "sec:technology", "sym:kospi",
                 "geo:kr", "geo:cn", "geo:asia", "theme:earnings"],
        "catatan_fakta": (
            "KOSPI puncak intraday 9,385.59 (19 Jun) → 5,663.24 (29 Jul) ≈ -40% dari "
            "puncak. 8 circuit breaker sepanjang 2026. Samsung+SK Hynix >50% bobot "
            "indeks. Pemicu struktural: tekanan DRAM dari CXMT (China) ~7.7% revenue "
            "DRAM global. Likuidasi paksa ritel ₩2.3T dalam 2.5 bulan (leverage + "
            "ETF berungkit). MSCI menolak masuk watchlist DM (23 Jun) → inflow pasif "
            "~$29-30 miliar yang diharapkan tidak datang."
        ),
    },
    {
        "title": "Krisis Yen & Unwind Carry Trade",
        "current_read": (
            "Normalisasi BoJ tidak menyelamatkan yen; yen di titik terlemah 40 tahun "
            "sementara yield JGB tertinggi 30 tahun — risiko unwind carry trade global naik."
        ),
        "persona_tags": ["GEMA", "AKELA"],
        "tags": ["org:boj", "sym:usd-jpy", "sym:jgb10", "theme:currency",
                 "theme:liquidity", "theme:rate-policy", "geo:jp",
                 "who:ueda", "who:katayama"],
        "catatan_fakta": (
            "BoJ tahan 1.00% (31 Jul) setelah hike Juni — tertinggi sejak 1995. "
            "JGB 10Y sempat ~2.78% (tertinggi 30 tahun), turun <2.8% pasca-BoJ. "
            "Yen di titik terlemah 40 tahun; intervensi ¥11.73T (≈$74M) akhir Apr-Mei, "
            "dugaan intervensi lagi 30 Jul (rally singkat). GDP FY2026 dinaikkan ke "
            "~0.8% dari 0.5%. Poll Reuters 23 Jul: 70% ekonom lihat rate ≥1.50% pada Q2 2027."
        ),
    },
    {
        "title": "Deleveraging Ritel Lintas Pasar",
        "current_read": (
            "Leverage ritel yang menumpuk saat euforia sedang dipaksa keluar lintas "
            "aset (ekuitas Asia, kripto); likuidasi paksa memperbesar amplitudo koreksi."
        ),
        "persona_tags": ["RIVAN", "AKELA"],
        "tags": ["theme:liquidity", "theme:credit", "sym:kospi", "sym:btc", "geo:global"],
        "catatan": "Berguna kalau ingin melacak pola likuidasi paksa lintas pasar "
                   "(KOSPI ₩2.3T vs likuidasi long/short BTC dari Coinalyze). "
                   "Overlap dengan RIVAN slice — cek jangan jadi duplikat.",
    },
]


def seed_tags(conn) -> tuple[int, int]:
    """Return (created, skipped)."""
    created = skipped = 0
    for entries in TAGS.values():
        for canonical, description in entries:
            try:
                create_tag(conn, canonical, description=description)
                created += 1
            except ValueError:
                skipped += 1  # sudah ada di kamus -- aman diabaikan
    return created, skipped


def seed_candidate_threads(conn) -> tuple[int, int]:
    """Return (created, skipped). Idempotent by exact title match -- skrip
    ini TIDAK PERNAH menyentuh thread existing (real atau kandidat yang
    sudah pernah di-seed sebelumnya)."""
    created = skipped = 0
    for c in CANDIDATES:
        existing = conn.execute(
            "SELECT 1 FROM news_threads WHERE title = ?", (c["title"],)
        ).fetchone()
        if existing:
            skipped += 1
            continue
        thread = save_thread(
            conn, title=c["title"], current_read=c["current_read"], persona_tags=c["persona_tags"],
        )
        # DORMANT segera setelah dibuat -- save_thread() default ACTIVE, tapi
        # kandidat SENGAJA tidak diaktifkan otomatis (lihat docstring modul).
        patch_thread(conn, thread["id"], status="DORMANT")
        for tag_canonical in c["tags"]:
            if resolve_tag(conn, tag_canonical) is not None:
                apply_tag(conn, "news_threads", thread["id"], tag_canonical)
            # tag tidak ketemu (mis. keluar dari BAGIAN 1) -- diam-diam
            # dilewati, bukan error keras; seed tag & seed thread dalam
            # 1 run yang sama jadi tidak saling gagal.
        created += 1
    return created, skipped


def main() -> None:
    init_db()
    with get_connection() as conn:
        t_created, t_skipped = seed_tags(conn)
        c_created, c_skipped = seed_candidate_threads(conn)
        conn.commit()
    print(f"[seed_tags] Tags: {t_created} baru, {t_skipped} sudah ada (dilewati).")
    print(f"[seed_tags] Kandidat thread: {c_created} baru (status DORMANT), {c_skipped} sudah ada (dilewati).")


if __name__ == "__main__":
    main()
