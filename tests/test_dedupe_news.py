"""Test tools/dedupe_news.py -- cleanup duplikat daily_news akibat bug
tanggal-scrape (scrapers/news.py, fix 6 Agustus 2026). Temp DB per test
(tmp_path), BUKAN DB asli -- pola sama pipeline/backfill.py."""
from db.connection import get_connection, init_db
from tools.dedupe_news import apply, preview


def _insert_news(conn, date, source, headline, raw_url):
    cur = conn.execute(
        "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, for_reading) "
        "VALUES (?,?,?,?,?,0)",
        (date, source, headline, raw_url, "LOW"),
    )
    return cur.lastrowid


def test_preview_counts_dupe_groups_and_excess_rows(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for d in ["2026-07-14", "2026-07-15", "2026-07-16"]:
            _insert_news(conn, d, "CNBC Economy", "Dupe headline",
                         "https://www.cnbc.com/2026/07/15/dupe-article.html")
        conn.commit()
        p = preview(conn)
        assert p["groups"] == 1
        assert p["excess_rows"] == 2
        assert p["url_dated_groups"] == 1


def test_apply_collapses_group_and_uses_url_embedded_date(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for d in ["2026-07-14", "2026-07-16", "2026-07-24"]:
            _insert_news(conn, d, "CNBC Economy", "World Cup gave bars a boost",
                         "https://www.cnbc.com/2026/07/15/world-cup-economy.html")
        conn.commit()
        s = apply(conn)
        conn.commit()
        assert s["groups"] == 1
        assert s["rows_deleted"] == 2
        assert s["dates_corrected"] == 1

        rows = conn.execute("SELECT date FROM daily_news WHERE headline='World Cup gave bars a boost'").fetchall()
        assert len(rows) == 1
        assert rows[0]["date"] == "2026-07-15"  # dari URL, bukan salah satu tanggal scrape


def test_apply_falls_back_to_earliest_date_when_no_url_pattern(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for d in ["2026-07-16", "2026-06-15", "2026-07-14"]:
            _insert_news(conn, d, "ANTARA Ekonomi", "Artikel tanpa tanggal di URL",
                         "https://otomotif.antaranews.com/berita/123456/judul-artikel")
        conn.commit()
        s = apply(conn)
        conn.commit()
        # MIN(date) = 2026-06-15 SUDAH salah satu baris yang ada -- baris itu
        # jadi "keep" apa adanya (tidak perlu UPDATE date), cuma 2 duplikat
        # lain yang dihapus. dates_corrected cuma naik kalau MIN(date) belum
        # ada sebagai baris manapun (baru perlu di-UPDATE).
        assert s["rows_deleted"] == 2
        assert s["dates_corrected"] == 0
        row = conn.execute("SELECT date FROM daily_news WHERE headline='Artikel tanpa tanggal di URL'").fetchone()
        assert row["date"] == "2026-06-15"  # MIN(date) di antara duplikat


def test_apply_leaves_different_url_same_headline_untouched(tmp_path):
    """Headline generik yang berulang TAPI raw_url beda = artikel BEDA
    (bukan hasil bug scrape-ulang) -- tidak boleh dikolaps."""
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        _insert_news(conn, "2026-07-08", "ANTARA Ekonomi", "IHSG melemah ikuti bursa Asia",
                     "https://antaranews.com/berita/111/ihsg-melemah-a")
        _insert_news(conn, "2025-06-19", "ANTARA Ekonomi", "IHSG melemah ikuti bursa Asia",
                     "https://antaranews.com/berita/222/ihsg-melemah-b")
        conn.commit()
        s = apply(conn)
        conn.commit()
        assert s["groups"] == 0
        assert s["rows_deleted"] == 0
        total = conn.execute("SELECT COUNT(*) AS n FROM daily_news").fetchone()["n"]
        assert total == 2


def test_apply_repoints_content_tags_and_thread_links_without_orphans(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        id_a = _insert_news(conn, "2026-07-14", "CNBC Economy", "Tagged dupe article",
                            "https://www.cnbc.com/2026/07/15/tagged-dupe.html")
        id_b = _insert_news(conn, "2026-07-15", "CNBC Economy", "Tagged dupe article",
                            "https://www.cnbc.com/2026/07/15/tagged-dupe.html")
        conn.execute(
            "INSERT INTO tag_dictionary (canonical, facet, usage_count) VALUES ('geo:us', 'geo', 2)"
        )
        tag_id = conn.execute("SELECT id FROM tag_dictionary WHERE canonical='geo:us'").fetchone()["id"]
        # tag nempel di baris yang AKAN dihapus (id_a, tanggal salah) --
        # harus di-repoint ke baris yang dipertahankan (id_b, tanggal benar).
        conn.execute(
            "INSERT INTO content_tags (ref_table, ref_id, tag_id, source) VALUES ('daily_news', ?, ?, 'MANUAL')",
            (id_a, tag_id),
        )
        t = conn.execute(
            "INSERT INTO news_threads (title, status, created_at, updated_at) VALUES ('T', 'ACTIVE', '2026-07-01', '2026-07-01')"
        )
        thread_id = t.lastrowid
        conn.execute(
            "INSERT INTO news_thread_links (thread_id, ref_table, ref_id, link_status, linked_at) "
            "VALUES (?, 'daily_news', ?, 'SUGGESTED', '2026-07-14')",
            (thread_id, id_a),
        )
        conn.commit()

        s = apply(conn)
        conn.commit()

        assert s["tags_repointed"] == 1
        assert s["links_repointed"] == 1
        kept_id = conn.execute("SELECT id FROM daily_news WHERE headline='Tagged dupe article'").fetchone()["id"]
        assert kept_id == id_b  # baris dgn tanggal benar (dari URL) yang dipertahankan

        tag_row = conn.execute("SELECT ref_id FROM content_tags WHERE tag_id=?", (tag_id,)).fetchone()
        assert tag_row["ref_id"] == kept_id
        link_row = conn.execute("SELECT ref_id FROM news_thread_links WHERE thread_id=?", (thread_id,)).fetchone()
        assert link_row["ref_id"] == kept_id

        usage = conn.execute("SELECT usage_count FROM tag_dictionary WHERE id=?", (tag_id,)).fetchone()["usage_count"]
        assert usage == 1  # recompute dari content_tags nyata, bukan disalin


def test_apply_is_idempotent(tmp_path):
    db = tmp_path / "t.db"
    init_db(db)
    with get_connection(db) as conn:
        for d in ["2026-07-14", "2026-07-16"]:
            _insert_news(conn, d, "CNBC Economy", "Idempotent test",
                         "https://www.cnbc.com/2026/07/15/idempotent.html")
        conn.commit()
        apply(conn)
        conn.commit()
        s2 = apply(conn)
        conn.commit()
        assert s2 == {"groups": 0, "rows_deleted": 0, "dates_corrected": 0, "tags_repointed": 0, "links_repointed": 0}
