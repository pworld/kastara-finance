"""News scraper: RSS feeds + rule-based impact scoring (BUKAN AI/LLM).

Output ke daily_news: source, headline, raw_url, impact_level (HIGH/MED/LOW).
is_key_trigger DEFAULT 0 (Giel flag manual nanti).

Acceptance:
  - Dedup by headline (jangan masuk 2x untuk headline sama)
  - impact_level selalu salah satu HIGH/MED/LOW
"""
from __future__ import annotations

import re
from typing import Any

import feedparser

from scrapers.base import SourceFlags, safe_call, today_wib

# RSS feeds (verifikasi aktif saat implementasi; kalau mati -> skip + log).
RSS_FEEDS = {
    "Reuters Business": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
    "CNBC Finance": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "CNBC Economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "Fed Press": "https://www.federalreserve.gov/feeds/press_all.xml",
    "CNBC Indonesia": "https://www.cnbcindonesia.com/market/rss",
    "Bisnis.com Market": "https://www.bisnis.com/rss/market",
    "Kontan": "https://www.kontan.co.id/rss",
}

# Keyword scoring — mudah ditambah. Case-insensitive substring match.
HIGH_KEYWORDS = [
    "fed", "rate", "fomc", "cpi", "bi rate", "inflation",
    "rate cut", "rate hike", "suku bunga",
]
MED_KEYWORDS = ["etf", "earnings", "gdp", "unemployment", "nasdaq"]


def _matches(text: str, keywords: list[str]) -> bool:
    """True kalau salah satu keyword muncul sebagai kata utuh (word boundary).

    Pakai \\b supaya 'rate' tidak match 'moderate'/'separate', tapi frasa
    multi-kata seperti 'rate cut' tetap cocok.
    """
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", text):
            return True
    return False


def score_impact(headline: str) -> str:
    """Return 'HIGH' | 'MED' | 'LOW' berdasar keyword rule-based."""
    h = (headline or "").lower()
    if _matches(h, HIGH_KEYWORDS):
        return "HIGH"
    if _matches(h, MED_KEYWORDS):
        return "MED"
    return "LOW"


def _parse_feed(name: str, url: str) -> list[dict[str, Any]]:
    """Parse satu feed -> list item {source, headline, raw_url, impact_level}."""
    parsed = feedparser.parse(url)
    if getattr(parsed, "bozo", 0) and not parsed.entries:
        raise ValueError(f"feed gagal/kosong: {name}")
    items: list[dict[str, Any]] = []
    for entry in parsed.entries:
        headline = (getattr(entry, "title", "") or "").strip()
        if not headline:
            continue
        items.append({
            "source": name,
            "headline": headline,
            "raw_url": getattr(entry, "link", "") or "",
            "impact_level": score_impact(headline),
        })
    return items


def fetch_news(date: str | None = None) -> dict[str, Any]:
    """Return dict: 'items' (list, sudah dedup) + 'date' + 'source_flags'."""
    date = date or today_wib()
    flags = SourceFlags()
    seen: set[str] = set()
    items: list[dict[str, Any]] = []

    for name, url in RSS_FEEDS.items():
        feed_items = safe_call(
            f"rss_{name}", lambda u=url, n=name: _parse_feed(n, u), flags, default=[]
        )
        for it in feed_items or []:
            key = it["headline"].lower()
            if key in seen:
                continue
            seen.add(key)
            it["date"] = date
            items.append(it)

    return {"date": date, "items": items, "source_flags": flags.as_dict()}


if __name__ == "__main__":
    out = fetch_news()
    print(f"{len(out['items'])} headline (dedup). flags={out['source_flags']}")
    for it in out["items"][:10]:
        print(f"  [{it['impact_level']:>4}] {it['source']}: {it['headline'][:80]}")
