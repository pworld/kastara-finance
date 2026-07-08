"""Test manual_articles CLI: insert, dedup warning (bukan blok), search."""
from db.connection import get_connection, init_db
from pipeline.add_article import find_similar, insert_article, search_articles


def test_insert_and_search_roundtrip(tmp_path):
    db = tmp_path / "articles.db"
    init_db(db)
    with get_connection(db) as conn:
        new_id = insert_article(
            conn, date="2015-06-19", source="CNBC", url="https://x.test/a",
            headline="Fed hints at rate hike", full_text=None,
            personal_notes="Titik balik DXY", tags="fed,rate,dxy",
            is_key_event=True,
        )
        conn.commit()
        assert new_id > 0

        results = search_articles(conn, tag="dxy")
        assert len(results) == 1
        assert results[0]["headline"] == "Fed hints at rate hike"
        assert results[0]["is_key_event"] == 1


def test_search_by_date_range(tmp_path):
    db = tmp_path / "articles.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_article(conn, date="2010-01-01", source="A", url=None,
                        headline="Old news", full_text=None, personal_notes=None,
                        tags=None, is_key_event=False)
        insert_article(conn, date="2020-01-01", source="B", url=None,
                        headline="New news", full_text=None, personal_notes=None,
                        tags=None, is_key_event=False)
        conn.commit()

        results = search_articles(conn, date_from="2015-01-01", date_to="2025-01-01")
        assert len(results) == 1
        assert results[0]["headline"] == "New news"


def test_search_by_keyword(tmp_path):
    db = tmp_path / "articles.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_article(conn, date="2020-01-01", source=None, url=None,
                        headline="BI rate decision surprises market", full_text=None,
                        personal_notes=None, tags=None, is_key_event=False)
        insert_article(conn, date="2020-01-02", source=None, url=None,
                        headline="Unrelated headline", full_text=None,
                        personal_notes=None, tags=None, is_key_event=False)
        conn.commit()

        results = search_articles(conn, keyword="rate decision")
        assert len(results) == 1
        assert "rate decision" in results[0]["headline"]


def test_find_similar_detects_same_url_not_blocking(tmp_path):
    db = tmp_path / "articles.db"
    init_db(db)
    with get_connection(db) as conn:
        insert_article(conn, date="2015-06-19", source="CNBC", url="https://x.test/a",
                        headline="Fed hints at rate hike", full_text=None,
                        personal_notes=None, tags=None, is_key_event=False)
        conn.commit()

        similar = find_similar(conn, "https://x.test/a", "2015-06-19", "Fed hints at rate hike")
        assert len(similar) == 1

        # find_similar cuma info, tidak ada constraint DB yang blok insert kedua
        insert_article(conn, date="2015-06-19", source="CNBC", url="https://x.test/a",
                        headline="Fed hints at rate hike (revisit)", full_text=None,
                        personal_notes="catatan baru", tags=None, is_key_event=False)
        conn.commit()

        total = conn.execute("SELECT COUNT(*) FROM manual_articles").fetchone()[0]
        assert total == 2


def test_find_similar_empty_when_no_match(tmp_path):
    db = tmp_path / "articles.db"
    init_db(db)
    with get_connection(db) as conn:
        similar = find_similar(conn, "https://none.test", "2020-01-01", "Nothing here")
        assert similar == []
