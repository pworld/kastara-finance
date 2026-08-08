"""CLI: backfill gap tanggal daily_news lewat search on-site tiap sumber
(BUKAN RSS -- lihat scrapers/news_archive.py docstring). Cakupan SAAT INI
cuma 2 sumber (CNBC Indonesia, ANTARA Ekonomi) yang sudah diverifikasi
live 4 Agustus 2026 -- lihat docs/ROADMAP.md utk audit lengkap kenapa
Wayback Machine & paid news API ditolak duluan.

Query pakai kamus IMPACT_KEYWORDS yang sudah ada (bukan daftar kata baru)
supaya cakupan konsisten dgn apa yang dianggap penting di pipeline ini
(HIGH/MED) -- BUKAN replikasi persis "semua artikel hari itu" (RSS asli
tidak filter keyword sama sekali, tapi replikasi itu butuh listing
per-tanggal yang JS-rendered di sisi sumber, lihat catatan di plan).

Pola preview -> konfirmasi -> commit sama seperti pipeline/backfill.py.

Pakai:
    python -m tools.backfill_news_archive --since 2026-06-16 --until 2026-06-24
    python -m tools.backfill_news_archive --since 2026-06-16 --until 2026-06-24 --yes
"""
from __future__ import annotations

import argparse

from db.connection import get_connection, init_db
from pipeline.run_daily import insert_news_dedup
from scrapers.feeds_config import IMPACT_KEYWORDS
from scrapers.news_archive import search_antaranews, search_cnbcindonesia

SEARCHERS = {
    "CNBC Indonesia": search_cnbcindonesia,
    "ANTARA Ekonomi": search_antaranews,
}

# Reuse kamus impact yang sudah ada -- bukan daftar kata query baru.
QUERY_KEYWORDS = sorted(set(IMPACT_KEYWORDS["HIGH"]) | set(IMPACT_KEYWORDS["MED"]))


def collect(
    date_from: str, date_to: str, *, keywords: list[str] | None = None,
    max_pages: int | None = None, delay: float = 0.0,
) -> list[dict]:
    """Loop keyword x source, dedup (date, headline) di Python dulu (dedup
    final tetap di DB lewat insert_news_dedup/UNIQUE index). Gagal 1
    source/keyword TIDAK menghentikan yang lain (pola sama safe_call).

    `keywords` -- override QUERY_KEYWORDS (mis. subset yg tidak kena cap
    10.000 CNBC). `max_pages`/`delay` -- diteruskan ke tiap searcher kalau
    diisi (None = pakai default masing-masing fungsi, page_size CNBC juga
    tetap default)."""
    seen: set[tuple[str, str]] = set()
    articles: list[dict] = []
    kw_list = keywords if keywords is not None else QUERY_KEYWORDS
    extra_kwargs: dict = {"delay": delay}
    if max_pages is not None:
        extra_kwargs["max_pages"] = max_pages
    for source_name, fn in SEARCHERS.items():
        for kw in kw_list:
            try:
                results = fn(kw, date_from, date_to, **extra_kwargs)
            except Exception as exc:  # noqa: BLE001
                print(f"[backfill_news_archive] {source_name}/{kw}: gagal -- {type(exc).__name__}: {exc}")
                continue
            for a in results:
                key = (a["date"], a["headline"].lower())
                if key in seen:
                    continue
                seen.add(key)
                articles.append(a)
    return articles


def cmd_backfill(args: argparse.Namespace) -> None:
    init_db()
    kw = getattr(args, "keywords", None)
    kw_list = [k.strip() for k in kw.split(",") if k.strip()] if kw else None
    articles = collect(
        args.since, args.until, keywords=kw_list,
        max_pages=getattr(args, "max_pages", None), delay=getattr(args, "delay", 0.0),
    )
    if not articles:
        print(f"[backfill_news_archive] tidak ada artikel ditemukan {args.since}..{args.until}.")
        return
    by_date: dict[str, int] = {}
    for a in articles:
        by_date[a["date"]] = by_date.get(a["date"], 0) + 1
    print(f"[backfill_news_archive PREVIEW] {args.since}..{args.until}: {len(articles)} artikel ditemukan.")
    for d in sorted(by_date):
        print(f"  {d}: {by_date[d]} artikel")
    if not args.yes:
        answer = input("\nLanjut commit ke daily_news? [y/N] ").strip().lower()
        if answer != "y":
            print("[backfill_news_archive] dibatalkan.")
            return
    with get_connection() as conn:
        n_new = insert_news_dedup(conn, articles)
        conn.commit()
    print(f"[backfill_news_archive] selesai -- {n_new} baris baru dari {len(articles)} kandidat (sisanya duplikat).")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Kastara backfill berita historis via search on-site (bukan RSS)")
    p.add_argument("--since", required=True, help="tanggal mulai, format YYYY-MM-DD")
    p.add_argument("--until", required=True, help="tanggal akhir, format YYYY-MM-DD")
    p.add_argument("--yes", action="store_true", help="skip konfirmasi (untuk script/test)")
    p.add_argument("--keywords", help="override QUERY_KEYWORDS, pisah koma (mis. utk skip keyword yg kena cap 10rb CNBC)")
    p.add_argument("--max-pages", type=int, dest="max_pages", help="override max_pages tiap searcher (default per-fungsi)")
    p.add_argument("--delay", type=float, default=0.0, help="jeda detik antar-request tiap searcher (\"santai\", default 0)")
    p.set_defaults(func=cmd_backfill)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
