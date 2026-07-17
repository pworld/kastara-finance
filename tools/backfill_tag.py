"""Tool CLI backfill tag + thread-suggest utk berita LAMA (Addendum C §21.9,
GELOMBANG C-2).

Prinsip anti-kewalahan kontrak (§21.9): backfill PER-THREAD (bukan
per-artikel/global) + batasi kedalaman waktu (`--since`) -- Giel tinjau
~20 kandidat per thread lewat NewsView/Settings sesudahnya, bukan hadapi 300
berita sekaligus. Tool ini MURNI mengumpulkan & menyarankan (rule-based,
BUKAN LLM) -- reuse langsung `suggest_tags_for_news`/`suggest_thread_links`
(tidak ada logic matching baru), keduanya SELALU menghasilkan status
SUGGESTED, TIDAK PERNAH stance/CONFIRMED/current_read (itu tetap tangan Giel).

Pakai:
    python -m tools.backfill_tag --thread-id 3 --since 2026-01-01
"""
from __future__ import annotations

import argparse

from db.connection import get_connection, init_db
from web.writes import get_thread, suggest_tags_for_news, suggest_thread_links


def backfill_thread(conn, thread_id: int, since: str) -> dict[str, int]:
    """Scan `daily_news` sejak `since` -> suggest_tags_for_news() lalu
    suggest_thread_links() (urutan sama seperti pipeline/run_daily.py, tag
    dulu baru tag-match thread). thread_id dipakai HANYA utk validasi
    keberadaan thread (guard eksplisit -- salah ketik id tidak diam-diam
    backfill 'ke mana-mana') dan pesan hasil; matching-nya sendiri tetap
    jalan ke SEMUA thread ACTIVE (perilaku suggest_thread_links yang sudah
    ada), bukan cuma thread_id ini -- kandidat yang benar-benar match thread
    LAIN pun valid, bukan noise."""
    thread = get_thread(conn, thread_id)
    if thread is None:
        raise ValueError(f"thread id {thread_id} tidak ditemukan")
    rows = conn.execute(
        "SELECT date, headline FROM daily_news WHERE date >= ? ORDER BY date", (since,)
    ).fetchall()
    news_items = [dict(r) for r in rows]
    n_tags = suggest_tags_for_news(conn, news_items)
    n_links = suggest_thread_links(conn, news_items)
    return {"thread_title": thread["title"], "news_scanned": len(news_items), "tags_suggested": n_tags, "links_suggested": n_links}


def cmd_backfill(args: argparse.Namespace) -> None:
    init_db()
    with get_connection() as conn:
        try:
            result = backfill_thread(conn, args.thread_id, args.since)
        except ValueError as exc:
            print(f"[backfill_tag] {exc}")
            return
        conn.commit()
    print(
        f"[backfill_tag] thread \"{result['thread_title']}\" -- {result['news_scanned']} berita di-scan "
        f"sejak {args.since}: {result['tags_suggested']} tag baru, {result['links_suggested']} link thread baru "
        "(semua SUGGESTED, tinjau di NewsView/ThreadDetailView)."
    )


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Kastara backfill tag + thread-suggest per-thread (Addendum C §21.9)")
    p.add_argument("--thread-id", type=int, required=True, help="scope validasi -- lihat docstring backfill_thread")
    p.add_argument("--since", required=True, help="batasi kedalaman waktu, format YYYY-MM-DD (wajib, cegah scan seluruh histori)")
    p.set_defaults(func=cmd_backfill)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
