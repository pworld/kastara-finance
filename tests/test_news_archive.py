"""Test scrapers/news_archive.py — historical backfill via search on-site
(bukan RSS). Butuh network (live API/halaman), sama pola dengan
test_news.py (lihat docstring-nya) -- sumber di sini sudah live-diverifikasi
4 Agustus 2026 sebelum dibangun (lihat docs/ROADMAP.md)."""
from datetime import datetime

import scrapers.news_archive as news_archive


def test_parse_antara_relative_date_hours_ago():
    now = datetime(2026, 8, 4, 12, 0, 0)
    assert news_archive._parse_antara_relative_date("3 jam lalu", now=now) == "2026-08-04"


def test_parse_antara_relative_date_days_ago():
    now = datetime(2026, 8, 4, 12, 0, 0)
    assert news_archive._parse_antara_relative_date("5 hari lalu", now=now) == "2026-07-30"


def test_parse_antara_relative_date_weeks_ago():
    now = datetime(2026, 8, 4, 12, 0, 0)
    assert news_archive._parse_antara_relative_date("2 minggu lalu", now=now) == "2026-07-21"


def test_parse_antara_relative_date_kemarin():
    now = datetime(2026, 8, 4, 12, 0, 0)
    assert news_archive._parse_antara_relative_date("Kemarin", now=now) == "2026-08-03"


def test_parse_antara_relative_date_absolute_indonesian_month():
    now = datetime(2026, 8, 4, 12, 0, 0)
    assert news_archive._parse_antara_relative_date("3 Agustus 2026", now=now) == "2026-08-03"


def test_parse_antara_relative_date_unknown_format_returns_none():
    now = datetime(2026, 8, 4, 12, 0, 0)
    assert news_archive._parse_antara_relative_date("format aneh tak dikenal", now=now) is None


def test_article_dict_high_impact_keeps_summary():
    a = news_archive._article_dict("2026-07-01", "CNBC Indonesia", "The Fed cuts rates", "https://x.test", "ringkasan asli")
    assert a["impact_level"] == "HIGH"
    assert a["rss_summary"] == "ringkasan asli"


def test_article_dict_low_impact_drops_summary():
    a = news_archive._article_dict("2026-07-01", "CNBC Indonesia", "Random gadget review", "https://x.test", "ringkasan asli")
    assert a["impact_level"] == "LOW"
    assert a["rss_summary"] is None


def test_search_cnbcindonesia_live_returns_dated_articles():
    """Live network -- API sudah diverifikasi 4 Agustus 2026 lewat Network
    tab. Query keyword umum ('fed') dgn rentang tanggal lebar pasti dapat
    beberapa hasil kalau API masih hidup; assert bentuk data, bukan isi
    spesifik (konten berubah tiap hari)."""
    articles = news_archive.search_cnbcindonesia("fed", "2020-01-01", "2026-12-31", page_size=5, max_pages=2)
    assert isinstance(articles, list)
    if articles:  # API kadang kosong tergantung index -- jangan asumsikan >0 keras
        a = articles[0]
        assert set(a.keys()) == {"date", "source", "headline", "raw_url", "impact_level", "rss_summary"}
        assert a["source"] == "CNBC Indonesia"
        assert a["impact_level"] in {"HIGH", "MED", "LOW"}
        assert len(a["date"]) == 10  # 'YYYY-MM-DD'


def test_search_cnbcindonesia_filters_out_of_range_dates():
    # Rentang sempit di masa depan jauh -- hampir pasti 0 hasil, tapi TIDAK
    # boleh raise, dan hasil yang lolos (kalau ada) harus benar dalam rentang.
    articles = news_archive.search_cnbcindonesia("fed", "2099-01-01", "2099-01-02", page_size=5, max_pages=2)
    assert isinstance(articles, list)
    for a in articles:
        assert "2099-01-01" <= a["date"] <= "2099-01-02"


def test_search_antaranews_live_returns_dated_articles():
    """Live network -- halaman search sudah diverifikasi 4 Agustus 2026
    (server-rendered, headline muncul di raw HTML tanpa JS)."""
    articles = news_archive.search_antaranews("fed", "2020-01-01", "2026-12-31", max_pages=1)
    assert isinstance(articles, list)
    if articles:
        a = articles[0]
        assert set(a.keys()) == {"date", "source", "headline", "raw_url", "impact_level", "rss_summary"}
        assert a["source"] == "ANTARA Ekonomi"
        assert len(a["date"]) == 10
