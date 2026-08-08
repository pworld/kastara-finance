"""One-off: sapu historis dalam ke 2010 (5 Agustus 2026, "ambil per tahun
sampai 2010 tapi dengan cara santai. buat jeda tidak apa apa" -- Giel).

BUKAN per-tahun secara harfiah lewat CLI biasa: search_cnbcindonesia/
search_antaranews urut TERBARU-DULU dan tidak punya offset absolut per
tanggal -- panggil terpisah per tahun berarti tiap tahun HARUS mem-paging
ulang semua tahun yang lebih baru dulu sebelum sampai ke tahun target
(mis. tahun 2010 butuh paging lewat 2011..2026 dulu), lalu diulang lagi
dari nol utk tahun 2011, dst -- boros drastis. Sapuan SATU KALI per
keyword dari sekarang mundur ke 2010-01-01 jauh lebih efisien (tiap
halaman cuma pernah diminta sekali), dan hasilnya tetap mencakup semua
tahun turun ke 2010 -- cuma cara eksekusinya beda dari permintaan
harfiah, bukan cakupannya.

Hanya 13 keyword yg TIDAK kena cap 10.000 hasil CNBC (diverifikasi live
4 Agustus 2026, lihat docs/ROADMAP.md) -- 8 keyword volume tinggi
(bank indonesia, fed, ihsg, inflasi, obligasi, rupiah, suku bunga, the fed)
dilewati krn 2010 provably unreachable utk mereka berapa pun max_pages.

Checkpoint per-keyword (commit ke DB stlh tiap keyword selesai, bukan
nunggu semua 13x2 sumber kelar) -- kalau job ini berhenti di tengah jalan
(mis. network/timeout), progress yg sudah masuk TIDAK hilang.

Pakai:
    python -m tools.deep_backfill_2010
"""
from __future__ import annotations

from db.connection import get_connection, init_db
from pipeline.run_daily import insert_news_dedup
from scrapers.news_archive import search_antaranews, search_cnbcindonesia

DATE_FROM = "2010-01-01"
DATE_TO = "2026-08-05"

# 13 keyword TIDAK kena cap 10.000 CNBC (total terverifikasi 4 Agustus 2026).
KEYWORDS = [
    "bi rate", "cpi", "earnings", "etf", "fomc", "gdp", "inflation",
    "nasdaq", "powell", "rate cut", "rate hike", "unemployment", "yield",
]

DELAY = 1.5  # detik antar-request -- "santai", jangan bombardir sumbernya.

SEARCHERS = [
    ("CNBC Indonesia", search_cnbcindonesia, {"page_size": 20, "max_pages": 400, "delay": DELAY}),
    ("ANTARA Ekonomi", search_antaranews, {"max_pages": 100, "delay": DELAY}),
]


def run() -> None:
    init_db()
    grand_total = 0
    for kw in KEYWORDS:
        seen: set[tuple[str, str]] = set()
        articles: list[dict] = []
        for source_name, fn, kwargs in SEARCHERS:
            print(f"[deep_backfill_2010] {kw!r} / {source_name} -- mencari {DATE_FROM}..{DATE_TO} ...")
            try:
                results = fn(kw, DATE_FROM, DATE_TO, **kwargs)
            except Exception as exc:  # noqa: BLE001
                print(f"[deep_backfill_2010] {kw!r} / {source_name}: gagal -- {type(exc).__name__}: {exc}")
                continue
            for a in results:
                key = (a["date"], a["headline"].lower())
                if key in seen:
                    continue
                seen.add(key)
                articles.append(a)
            print(f"[deep_backfill_2010] {kw!r} / {source_name}: {len(results)} artikel mentah ditemukan.")
        if articles:
            oldest = min(a["date"] for a in articles)
            newest = max(a["date"] for a in articles)
            with get_connection() as conn:
                n_new = insert_news_dedup(conn, articles)
                conn.commit()
            grand_total += n_new
            print(f"[deep_backfill_2010] {kw!r}: {n_new} baris BARU disimpan (rentang {oldest}..{newest}). Total sejauh ini: {grand_total}")
        else:
            print(f"[deep_backfill_2010] {kw!r}: 0 artikel ditemukan dari kedua sumber.")
    print(f"[deep_backfill_2010] SELESAI -- {grand_total} baris baru total dari {len(KEYWORDS)} keyword x {len(SEARCHERS)} sumber.")


if __name__ == "__main__":
    run()
