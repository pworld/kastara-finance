"""Manual article tool — isi `manual_articles` untuk riset historis.

Kenapa ini ada: RSS (`scrapers/news.py`) cuma nampilin berita TERKINI — tidak
ada cara narik headline lama (2010 dst) dari RSS, itu keterbatasan struktural
sumbernya. `manual_articles` adalah jalur yang memang didesain (Master Plan
§4.1) untuk artikel historis/penting yang kamu temukan & kurasi sendiri.

Pakai:
    # Tambah artikel
    python -m pipeline.add_article add --date 2015-06-19 --source CNBC \\
        --url "https://..." --headline "Fed hints at rate hike" \\
        --notes "Titik balik penting buat DXY tahun itu" \\
        --tags fed,rate,dxy --key-event

    # Isi full_text dari file (opsional, buat artikel panjang)
    python -m pipeline.add_article add --date 2015-06-19 --source CNBC \\
        --headline "..." --text-file artikel.txt

    # Cari lagi buat riset ("apa yang saya pikirkan saat DXY breakout Maret 2026")
    python -m pipeline.add_article list --tag dxy
    python -m pipeline.add_article list --from 2015-01-01 --to 2015-12-31
    python -m pipeline.add_article list --search "rate hike"

Dedup: BUKAN dedup ketat kayak daily_news (di sini re-visit artikel yang sama
dengan catatan baru itu wajar/valid). Kalau URL sudah pernah ada, tool cuma
KASIH TAHU + minta konfirmasi (atau --yes), bukan blok otomatis.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

from db.connection import get_connection, init_db
from scrapers.base import created_at, today_wib


def _read_full_text(text: str | None, text_file: str | None) -> str | None:
    if text_file:
        return Path(text_file).read_text(encoding="utf-8")
    return text


def find_similar(conn: sqlite3.Connection, url: str | None, date: str, headline: str) -> list[dict[str, Any]]:
    """Cari entri yang mirip (URL sama, atau date+headline sama) — buat warning, bukan blok."""
    rows: list[sqlite3.Row] = []
    if url:
        rows += conn.execute(
            "SELECT id, date, source, headline, url FROM manual_articles WHERE url = ?",
            (url,),
        ).fetchall()
    rows += conn.execute(
        "SELECT id, date, source, headline, url FROM manual_articles "
        "WHERE date = ? AND headline = ? AND (url IS NULL OR url != ?)",
        (date, headline, url or ""),
    ).fetchall()
    seen_ids: set[int] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        if r["id"] in seen_ids:
            continue
        seen_ids.add(r["id"])
        out.append(dict(r))
    return out


def insert_article(
    conn: sqlite3.Connection,
    *,
    date: str,
    source: str | None,
    url: str | None,
    headline: str,
    full_text: str | None,
    personal_notes: str | None,
    tags: str | None,
    is_key_event: bool,
) -> int:
    cur = conn.execute(
        "INSERT INTO manual_articles "
        "(date, source, url, headline, full_text, personal_notes, tags, "
        "is_key_event, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (date, source, url, headline, full_text, personal_notes, tags,
         1 if is_key_event else 0, created_at()),
    )
    return cur.lastrowid


def search_articles(
    conn: sqlite3.Connection,
    *,
    tag: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    keyword: str | None = None,
    key_event_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if tag:
        where.append("(',' || tags || ',') LIKE ?")
        params.append(f"%,{tag},%")
    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to)
    if keyword:
        where.append("(headline LIKE ? OR personal_notes LIKE ? OR full_text LIKE ?)")
        params += [f"%{keyword}%"] * 3
    if key_event_only:
        where.append("is_key_event = 1")

    sql = "SELECT id, date, source, headline, url, tags, is_key_event FROM manual_articles"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def cmd_add(args: argparse.Namespace) -> None:
    init_db()
    date = args.date or today_wib()
    full_text = _read_full_text(args.text, args.text_file)
    tags = args.tags.strip() if args.tags else None

    with get_connection() as conn:
        similar = find_similar(conn, args.url, date, args.headline)
        if similar:
            print(f"[add_article] Ditemukan {len(similar)} entri mirip (bukan blok, cuma info):")
            for s in similar:
                print(f"    id={s['id']} {s['date']} [{s['source']}] {s['headline'][:70]}")
            if not args.yes:
                ans = input("\nTetap tambah entri baru? [y/N] ").strip().lower()
                if ans != "y":
                    print("[add_article] Dibatalkan.")
                    return

        new_id = insert_article(
            conn,
            date=date, source=args.source, url=args.url, headline=args.headline,
            full_text=full_text, personal_notes=args.notes, tags=tags,
            is_key_event=args.key_event,
        )
        conn.commit()
    print(f"[add_article] OK — tersimpan id={new_id} ({date}: {args.headline[:70]})")


def cmd_list(args: argparse.Namespace) -> None:
    init_db()
    with get_connection() as conn:
        rows = search_articles(
            conn, tag=args.tag, date_from=args.date_from, date_to=args.date_to,
            keyword=args.search, key_event_only=args.key_event, limit=args.limit,
        )
    if not rows:
        print("[add_article] Tidak ada hasil.")
        return
    print(f"[add_article] {len(rows)} hasil:")
    for r in rows:
        flag = " ⭐" if r["is_key_event"] else ""
        tag_str = f" #{r['tags']}" if r["tags"] else ""
        print(f"  id={r['id']:<4} {r['date']} [{r['source'] or '-'}]{flag} {r['headline']}{tag_str}")
        if r["url"]:
            print(f"        {r['url']}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Kastara manual_articles tool (riset historis)")
    sub = p.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Tambah artikel manual")
    p_add.add_argument("--date", help="YYYY-MM-DD (default: hari ini WIB)")
    p_add.add_argument("--source", help="mis. CNBC, Reuters, Kontan")
    p_add.add_argument("--url", help="link artikel (opsional)")
    p_add.add_argument("--headline", required=True)
    p_add.add_argument("--text", help="isi artikel singkat (inline)")
    p_add.add_argument("--text-file", help="path file teks artikel panjang")
    p_add.add_argument("--notes", help="catatan/interpretasi pribadi")
    p_add.add_argument("--tags", help="comma-separated, mis. fed,rate,dxy")
    p_add.add_argument("--key-event", action="store_true", help="flag sebagai event penting")
    p_add.add_argument("--yes", action="store_true", help="skip konfirmasi duplikat")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="Cari/lihat artikel tersimpan")
    p_list.add_argument("--tag", help="filter exact tag (salah satu dari comma-separated)")
    p_list.add_argument("--from", dest="date_from", help="YYYY-MM-DD")
    p_list.add_argument("--to", dest="date_to", help="YYYY-MM-DD")
    p_list.add_argument("--search", help="cari di headline/notes/full_text")
    p_list.add_argument("--key-event", action="store_true", help="cuma yang di-flag key event")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_list)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
