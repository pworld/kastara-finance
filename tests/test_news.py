"""Test scrapers/news.py — health check RSS + impact scoring. Butuh network
(live API), sama pola dengan test_econ_calendar.py/test_positioning.py."""
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
