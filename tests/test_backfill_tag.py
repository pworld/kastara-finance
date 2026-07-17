"""Test tools/backfill_tag.py — Addendum C §21.9 (GELOMBANG C-2).

Guard non-negotiable: backfill MURNI mengumpulkan & menyarankan (rule-based),
TIDAK PERNAH menulis stance/CONFIRMED/current_read -- itu tetap tangan Giel.
"""
from db.connection import get_connection, init_db
from web.writes import create_tag, save_thread
from tools.backfill_tag import backfill_thread


def _seed_news(conn, **overrides):
    defaults = {
        "date": "2026-01-15", "source": "CNBC", "headline": "Warsh signals hawkish stance",
        "raw_url": "https://x.test", "impact_level": "HIGH", "for_reading": 0,
    }
    defaults.update(overrides)
    cur = conn.execute(
        "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
        "for_reading, created_at) VALUES (:date, :source, :headline, :raw_url, "
        ":impact_level, :for_reading, '')",
        defaults,
    )
    return cur.lastrowid


def test_backfill_thread_unknown_id_raises(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        try:
            backfill_thread(conn, 999, "2026-01-01")
            assert False, "harusnya raise ValueError"
        except ValueError as exc:
            assert "tidak ditemukan" in str(exc)


def test_backfill_thread_scopes_by_since_date(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Rezim Warsh", keywords=["warsh"])
        _seed_news(conn, headline="Warsh signals hawkish stance", date="2026-01-15")
        _seed_news(conn, headline="Warsh spoke long ago", date="2020-01-01")
        conn.commit()
        result = backfill_thread(conn, thread["id"], "2026-01-01")
        assert result["news_scanned"] == 1
        assert result["links_suggested"] == 1


def test_backfill_thread_never_writes_stance_or_confirmed(tmp_path):
    """Backfill hanya SUGGESTED -- stance/link_status CONFIRMED/current_read
    thread TIDAK PERNAH ditulis oleh fungsi ini (§21.9, HARAM diotomasi)."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        thread = save_thread(conn, title="Rezim Warsh", keywords=["warsh"], current_read="belum ada bacaan")
        create_tag(conn, "who:warsh")
        _seed_news(conn, headline="Warsh signals hawkish stance", date="2026-01-15")
        conn.commit()
        backfill_thread(conn, thread["id"], "2026-01-01")
        conn.commit()

        links = conn.execute(
            "SELECT link_status, stance FROM news_thread_links WHERE thread_id = ?", (thread["id"],)
        ).fetchall()
        assert links, "harusnya ada link tersaran"
        for link in links:
            assert link["link_status"] == "SUGGESTED"
            assert link["stance"] is None

        tags = conn.execute(
            "SELECT source FROM content_tags WHERE ref_table = 'daily_news'"
        ).fetchall()
        assert tags, "harusnya ada tag tersaran"
        assert all(t["source"] == "SUGGESTED" for t in tags)

        unchanged = conn.execute(
            "SELECT current_read FROM news_threads WHERE id = ?", (thread["id"],)
        ).fetchone()
        assert unchanged["current_read"] == "belum ada bacaan"
