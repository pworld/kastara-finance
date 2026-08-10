"""Test scrapers/news.py — health check RSS + impact scoring. Butuh network
(live API), sama pola dengan test_econ_calendar.py/test_positioning.py."""
import time

import scrapers.news as news
from scrapers.feeds_config import FEEDS

FED_FOMC_URL = next(f["url"] for f in FEEDS if f["name"] == "Fed FOMC")


def test_check_feed_health_valid_feed():
    status, reason, entries = news.check_feed_health(FED_FOMC_URL)
    assert status == "ok"
    assert reason == ""
    assert len(entries) > 0


def test_check_feed_health_404_no_raise():
    status, reason, entries = news.check_feed_health(
        "https://www.federalreserve.gov/this-path-does-not-exist-404.xml"
    )
    assert status == "dead"
    assert "404" in reason
    assert entries == []


def test_check_feed_health_not_rss():
    status, reason, entries = news.check_feed_health("https://example.com")
    assert status == "dead"
    assert entries == []


def test_score_impact_high():
    assert news.score_impact("Fed cuts rates 25bps") == "HIGH"
    assert news.score_impact("Bank Indonesia holds rates steady") == "HIGH"
    assert news.score_impact("BI rate decision today") == "HIGH"


def test_score_impact_low():
    assert news.score_impact("Random tech gadget review") == "LOW"


def test_score_impact_med():
    assert news.score_impact("Bitcoin ETF inflows rise") == "MED"


def test_score_impact_always_valid():
    for h in ["", "random headline", "GDP data", "FOMC minutes"]:
        assert news.score_impact(h) in {"HIGH", "MED", "LOW"}


def test_fetch_all_news_dedup_same_headline_across_feeds(monkeypatch):
    # 2 "feed" berbeda nama tapi URL SAMA -> headline yang sama pasti
    # muncul di keduanya, cara deterministik nguji dedup tanpa mock HTTP.
    fake_feeds = [
        {"name": "FeedA", "url": FED_FOMC_URL, "category": "FED", "enabled": True},
        {"name": "FeedB", "url": FED_FOMC_URL, "category": "FED", "enabled": True},
    ]
    monkeypatch.setattr(news, "FEEDS", fake_feeds)
    articles, health_report = news.fetch_all_news()

    headlines = [a["headline"].lower() for a in articles]
    assert len(headlines) == len(set(headlines)), "ada headline duplikat"
    assert health_report == {"FeedA": "ok", "FeedB": "ok"}
    for a in articles:
        assert a["impact_level"] in {"HIGH", "MED", "LOW"}


def test_fetch_all_news_continues_when_one_feed_dead(monkeypatch):
    fake_feeds = [
        {"name": "Good", "url": FED_FOMC_URL, "category": "FED", "enabled": True},
        {"name": "Dead", "url": "https://example.com", "category": "FED", "enabled": True},
        {"name": "Disabled", "url": "https://example.com", "category": "FED", "enabled": False},
    ]
    monkeypatch.setattr(news, "FEEDS", fake_feeds)
    articles, health_report = news.fetch_all_news()

    assert health_report == {"Good": "ok", "Dead": "dead"}
    assert "Disabled" not in health_report
    assert len(articles) > 0
    assert all(a["source"] == "Good" for a in articles)


# ---------- rss_summary (Addendum D §22.3, D-1) ----------

def test_fetch_all_news_includes_rss_summary_key():
    """Live feed -- tiap artikel WAJIB punya key rss_summary (None wajar
    kalau feed tak sertakan summary, tapi key-nya sendiri harus selalu ada)."""
    articles, _ = news.fetch_all_news()
    assert articles, "harusnya ada artikel dari feed live"
    for a in articles:
        assert "rss_summary" in a
        assert a["rss_summary"] is None or isinstance(a["rss_summary"], str)


def test_clean_rss_summary_none_and_empty():
    assert news._clean_rss_summary(None) is None
    assert news._clean_rss_summary("") is None
    assert news._clean_rss_summary("   ") is None


def test_clean_rss_summary_strips_html_and_whitespace():
    assert news._clean_rss_summary("<p>Hello  <b>world</b></p>\n\n") == "Hello world"


def test_clean_rss_summary_truncates_long_text():
    long_text = "x" * 500
    result = news._clean_rss_summary(long_text)
    assert len(result) == news.RSS_SUMMARY_MAX_LEN + 1  # +1 utk karakter "…"
    assert result.endswith("…")


class _FakeEntry:
    def __init__(self, title, summary):
        self.title = title
        self.link = "https://x.test"
        self.summary = summary


def test_rss_summary_only_populated_for_high_impact(monkeypatch):
    """Giel: "ringkasan berita only for news with high" -- MED/LOW tidak
    pernah dapat rss_summary sama sekali, meski feed-nya sendiri sertakan
    summary (bukan cuma disembunyikan di UI, benar-benar tidak disimpan)."""
    fake_entries = [
        _FakeEntry("Fed cuts rates 25bps", "Ringkasan berita HIGH ini harus muncul."),
        _FakeEntry("Random tech gadget review", "Ringkasan berita LOW ini TIDAK boleh muncul."),
    ]
    monkeypatch.setattr(news, "FEEDS", [{"name": "Fake", "url": "https://fake.test", "category": "TEST", "enabled": True}])
    monkeypatch.setattr(news, "check_feed_health", lambda url: ("ok", "", fake_entries))

    articles, _ = news.fetch_all_news()
    by_headline = {a["headline"]: a for a in articles}

    assert by_headline["Fed cuts rates 25bps"]["impact_level"] == "HIGH"
    assert by_headline["Fed cuts rates 25bps"]["rss_summary"] == "Ringkasan berita HIGH ini harus muncul."

    assert by_headline["Random tech gadget review"]["impact_level"] == "LOW"
    assert by_headline["Random tech gadget review"]["rss_summary"] is None


# ---------- _entry_date (6 Agustus 2026, laporan Giel "berita beberapa
# hari lalu dianggap hari ini pas diseeding") ----------
# Dulu SEMUA artikel di-stamp `target_date` (tanggal scrape), abai tanggal
# terbit asli feed. Kalau cron telat & baru catch-up hari ini, headline yg
# sebenarnya beberapa hari lalu (tapi masih ada di window rolling RSS)
# ke-stamp seolah baru terbit HARI INI. Fix: baca published_parsed/
# updated_parsed (feedparser, UTC struct_time) kalau ada.

class _FakeEntryWithDate:
    def __init__(self, title, published_parsed=None, updated_parsed=None):
        self.title = title
        self.link = "https://x.test"
        self.summary = None
        if published_parsed is not None:
            self.published_parsed = published_parsed
        if updated_parsed is not None:
            self.updated_parsed = updated_parsed


def test_entry_date_uses_published_parsed_converted_to_wib():
    # 2026-08-01 20:00 UTC -> 2026-08-02 03:00 WIB (UTC+7) -- lewat batas
    # hari, sengaja dipilih supaya konversi tanggal beneran teruji, bukan
    # kebetulan sama krn UTC dan WIB masih di hari yang sama.
    struct = time.strptime("2026-08-01 20:00:00", "%Y-%m-%d %H:%M:%S")
    entry = _FakeEntryWithDate("Test", published_parsed=struct)
    assert news._entry_date(entry, fallback="2026-08-06") == "2026-08-02"


def test_entry_date_falls_back_to_updated_parsed_when_no_published():
    struct = time.strptime("2026-07-30 10:00:00", "%Y-%m-%d %H:%M:%S")
    entry = _FakeEntryWithDate("Test", updated_parsed=struct)
    assert news._entry_date(entry, fallback="2026-08-06") == "2026-07-30"


def test_entry_date_falls_back_to_scrape_date_when_neither_present():
    entry = _FakeEntryWithDate("Test")
    assert news._entry_date(entry, fallback="2026-08-06") == "2026-08-06"


def test_fetch_all_news_uses_real_publish_date_not_scrape_date(monkeypatch):
    """Regression langsung utk laporan Giel -- feed dgn entry bertanggal
    beberapa hari lalu HARUS masuk daily_news dgn tanggal ASLI itu, BUKAN
    tanggal scrape (`target_date`), meski fetch_all_news() dipanggil HARI
    INI (mis. cron telat lalu catch-up)."""
    old_struct = time.strptime("2026-08-01 06:00:00", "%Y-%m-%d %H:%M:%S")
    fake_entries = [_FakeEntryWithDate("Old headline from days ago", published_parsed=old_struct)]
    monkeypatch.setattr(news, "FEEDS", [{"name": "Fake", "url": "https://fake.test", "category": "TEST", "enabled": True}])
    monkeypatch.setattr(news, "check_feed_health", lambda url: ("ok", "", fake_entries))

    articles, _ = news.fetch_all_news(target_date="2026-08-06")
    assert len(articles) == 1
    assert articles[0]["date"] == "2026-08-01"
    assert articles[0]["date"] != "2026-08-06"
