"""One-off cleanup (6 Agustus 2026): kolaps duplikat `daily_news` akibat
bug tanggal-scrape di `scrapers/news.py` (diperbaiki commit yang sama hari
ini, tapi TIDAK memperbaiki baris yang SUDAH terlanjur masuk). Sebelum
fix: tiap artikel yang masih nongkrong di window rolling RSS ke-insert
ULANG tiap kali cron jalan, masing2 dapat `date` = tanggal SCRAPE (hari
itu), bukan tanggal TERBIT asli -- 1 artikel jadi berkali-kali baris,
SEMUANYA salah kecuali kebetulan. Ditemukan Giel lewat 1 contoh nyata
("World Cup gave bars...", tanggal asli Jul 15 tapi muncul di 08-09) --
digali lebih dalam, ternyata sistemik: 986 grup (headline+source) duplikat
di DB lokal, 2.352 baris berlebih.

Strategi tentukan tanggal BENAR per grup (headline, source, raw_url):
  1. Kalau raw_url CNBC (pola /YYYY/MM/DD/ tertanam di path -- diverifikasi
     live match 100% sampel) -- ekstrak tanggal dari URL (tanggal terbit
     ASLI dari sumbernya sendiri, bukan tebakan).
  2. Kalau tidak (mis. ANTARA, URL cuma id artikel) -- pakai MIN(date) di
     antara baris duplikat (best-effort -- baris yang PALING AWAL ke-scrape
     kemungkinan paling dekat ke tanggal terbit asli, drpd baris yg
     ke-scrape berbulan-bulan kemudian saat artikel itu somehow masih ada
     di respons search/cache sumbernya).

WAJIB re-point `content_tags`/`news_thread_links` yang nempel di baris yg
akan DIHAPUS ke baris yang DIPERTAHANKAN dulu (bukan orphan referensi) --
kalau target sudah py pasangan yang sama (UNIQUE collision), baris
duplikat itu di-DELETE bukan di-UPDATE. `tag_dictionary.usage_count`
di-recompute di akhir krn ikut berubah.

Pola preview -> konfirmasi -> commit sama seperti pipeline/backfill.py.

Pakai:
    python -m tools.dedupe_news
    python -m tools.dedupe_news --yes
"""
from __future__ import annotations

import argparse
import re

from db.connection import get_connection, init_db

CNBC_URL_DATE_RE = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")


def _true_date_for_group(raw_url: str, dates: list[str]) -> str:
    # Semua baris 1 grup berbagi raw_url yang SAMA PERSIS (bagian dari
    # kunci grup) -- cukup dicek sekali, bukan per-baris.
    m = CNBC_URL_DATE_RE.search(raw_url or "")
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo}-{d}"
    return min(dates)


def collect_groups(conn) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        "SELECT headline, source, raw_url FROM daily_news "
        "GROUP BY headline, source, raw_url HAVING COUNT(*) > 1"
    ).fetchall()
    return [(r["headline"], r["source"], r["raw_url"]) for r in rows]


def preview(conn) -> dict:
    groups = collect_groups(conn)
    excess_rows = 0
    url_dated = 0
    for headline, source, raw_url in groups:
        n = conn.execute(
            "SELECT COUNT(*) AS n FROM daily_news WHERE headline=? AND source=? AND raw_url=?",
            (headline, source, raw_url),
        ).fetchone()["n"]
        excess_rows += n - 1
        if CNBC_URL_DATE_RE.search(raw_url or ""):
            url_dated += 1
    return {"groups": len(groups), "excess_rows": excess_rows, "url_dated_groups": url_dated}


def apply(conn) -> dict:
    groups = collect_groups(conn)
    summary = {"groups": 0, "rows_deleted": 0, "dates_corrected": 0, "tags_repointed": 0, "links_repointed": 0}
    for headline, source, raw_url in groups:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, date FROM daily_news WHERE headline=? AND source=? AND raw_url=? ORDER BY id",
            (headline, source, raw_url),
        ).fetchall()]
        if len(rows) < 2:
            continue  # sudah dikolaps grup lain (headline+source+raw_url sama tapi query ulang)
        true_date = _true_date_for_group(raw_url, [r["date"] for r in rows])
        keep = next((r for r in rows if r["date"] == true_date), rows[0])
        keep_id = keep["id"]
        if keep["date"] != true_date:
            conn.execute("UPDATE daily_news SET date=? WHERE id=?", (true_date, keep_id))
            summary["dates_corrected"] += 1
        for r in rows:
            if r["id"] == keep_id:
                continue
            for tag_row in conn.execute(
                "SELECT id, tag_id FROM content_tags WHERE ref_table='daily_news' AND ref_id=?", (r["id"],),
            ).fetchall():
                collide = conn.execute(
                    "SELECT 1 FROM content_tags WHERE ref_table='daily_news' AND ref_id=? AND tag_id=?",
                    (keep_id, tag_row["tag_id"]),
                ).fetchone()
                if collide:
                    conn.execute("DELETE FROM content_tags WHERE id=?", (tag_row["id"],))
                else:
                    conn.execute("UPDATE content_tags SET ref_id=? WHERE id=?", (keep_id, tag_row["id"]))
                    summary["tags_repointed"] += 1
            for link_row in conn.execute(
                "SELECT id, thread_id FROM news_thread_links WHERE ref_table='daily_news' AND ref_id=?", (r["id"],),
            ).fetchall():
                collide = conn.execute(
                    "SELECT 1 FROM news_thread_links WHERE ref_table='daily_news' AND thread_id=? AND ref_id=?",
                    (link_row["thread_id"], keep_id),
                ).fetchone()
                if collide:
                    conn.execute("DELETE FROM news_thread_links WHERE id=?", (link_row["id"],))
                else:
                    conn.execute("UPDATE news_thread_links SET ref_id=? WHERE id=?", (keep_id, link_row["id"]))
                    summary["links_repointed"] += 1
            conn.execute("DELETE FROM daily_news WHERE id=?", (r["id"],))
            summary["rows_deleted"] += 1
        summary["groups"] += 1
    conn.execute(
        "UPDATE tag_dictionary SET usage_count = "
        "(SELECT COUNT(*) FROM content_tags WHERE content_tags.tag_id = tag_dictionary.id)"
    )
    return summary


def cmd_dedupe(args: argparse.Namespace) -> None:
    init_db()
    with get_connection() as conn:
        p = preview(conn)
    print(
        f"[dedupe_news PREVIEW] {p['groups']} grup duplikat, {p['excess_rows']} baris berlebih "
        f"akan dihapus ({p['url_dated_groups']} grup tanggal-nya bisa dikoreksi dari URL, "
        f"sisanya pakai tanggal ke-scrape paling awal)."
    )
    if not args.yes:
        answer = input("\nLanjut commit? [y/N] ").strip().lower()
        if answer != "y":
            print("[dedupe_news] dibatalkan.")
            return
    with get_connection() as conn:
        s = apply(conn)
        conn.commit()
    print(
        f"[dedupe_news] selesai -- {s['groups']} grup, {s['rows_deleted']} baris dihapus, "
        f"{s['dates_corrected']} tanggal dikoreksi, {s['tags_repointed']} tag di-repoint, "
        f"{s['links_repointed']} thread link di-repoint."
    )


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Kolaps duplikat daily_news akibat bug tanggal-scrape (6 Agustus 2026)")
    p.add_argument("--yes", action="store_true", help="skip konfirmasi (untuk script/test)")
    p.set_defaults(func=cmd_dedupe)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
