"""Test tools/backfill_news_archive.py — orkestrasi (dedup, preview/commit).
Mock SEARCHERS di sini (bukan live network) -- fungsi pencarian sendiri
(scrapers/news_archive.py) sudah diuji live network di test_news_archive.py.
Guard non-negotiable: backfill TIDAK PERNAH menulis for_reading=1 atau
menyentuh tabel lain -- murni insert_news_dedup() yang sudah ada."""
from db.connection import get_connection, init_db
from tools.backfill_news_archive import cmd_backfill, collect
import tools.backfill_news_archive as backfill_news_archive


def _fake_article(date, headline, source="CNBC Indonesia"):
    return {
        "date": date, "source": source, "headline": headline,
        "raw_url": f"https://x.test/{headline}", "impact_level": "HIGH", "rss_summary": None,
    }


def test_collect_dedupes_across_keywords_and_sources(monkeypatch):
    # 2 keyword sama-sama nemu artikel yang SAMA (headline identik) -- harus
    # ke-dedup jadi 1, meski datang dari 2 pencarian keyword berbeda.
    shared = _fake_article("2026-06-16", "Fed cuts rates")
    monkeypatch.setattr(backfill_news_archive, "SEARCHERS", {
        "CNBC Indonesia": lambda kw, df, dt, **kwargs: [shared],
        "ANTARA Ekonomi": lambda kw, df, dt, **kwargs: [],
    })
    monkeypatch.setattr(backfill_news_archive, "QUERY_KEYWORDS", ["fed", "rate"])
    articles = collect("2026-06-16", "2026-06-24")
    assert len(articles) == 1


def test_collect_survives_one_source_failing(monkeypatch, capsys):
    def _boom(kw, df, dt, **kwargs):
        raise RuntimeError("simulated network failure")
    ok_article = _fake_article("2026-06-17", "BI holds rate", source="ANTARA Ekonomi")
    monkeypatch.setattr(backfill_news_archive, "SEARCHERS", {
        "CNBC Indonesia": _boom,
        "ANTARA Ekonomi": lambda kw, df, dt, **kwargs: [ok_article],
    })
    monkeypatch.setattr(backfill_news_archive, "QUERY_KEYWORDS", ["fed"])
    articles = collect("2026-06-16", "2026-06-24")
    assert len(articles) == 1
    assert articles[0]["source"] == "ANTARA Ekonomi"
    assert "gagal" in capsys.readouterr().out


def test_cmd_backfill_yes_flag_commits_without_prompt(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("KASTARA_DB_PATH", str(db))
    articles = [_fake_article("2026-06-16", "Fed cuts rates"), _fake_article("2026-06-17", "BI holds rate")]
    monkeypatch.setattr(backfill_news_archive, "collect", lambda since, until, **kw: articles)

    class Args:
        since, until, yes = "2026-06-16", "2026-06-24", True
    cmd_backfill(Args())

    with get_connection(db) as conn:
        rows = conn.execute("SELECT headline, for_reading FROM daily_news ORDER BY date").fetchall()
    assert [r["headline"] for r in rows] == ["Fed cuts rates", "BI holds rate"]
    assert all(r["for_reading"] == 0 for r in rows)


def test_cmd_backfill_no_articles_inserts_nothing(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("KASTARA_DB_PATH", str(db))
    monkeypatch.setattr(backfill_news_archive, "collect", lambda since, until, **kw: [])

    class Args:
        since, until, yes = "2026-06-16", "2026-06-24", True
    cmd_backfill(Args())
    # init_db() jalan (pola sama tools lain, cheap+idempotent), tapi tidak
    # ada baris daily_news yang ke-insert krn collect() kosong.
    with get_connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM daily_news").fetchone()["n"] == 0


def test_cmd_backfill_declining_confirmation_does_not_commit(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("KASTARA_DB_PATH", str(db))
    articles = [_fake_article("2026-06-16", "Fed cuts rates")]
    monkeypatch.setattr(backfill_news_archive, "collect", lambda since, until, **kw: articles)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    class Args:
        since, until, yes = "2026-06-16", "2026-06-24", False
    cmd_backfill(Args())

    init_db(db)
    with get_connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM daily_news").fetchone()["n"] == 0
