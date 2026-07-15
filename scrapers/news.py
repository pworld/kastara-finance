"""News scraper: RSS feeds (registry di scrapers/feeds_config.py) + rule-based
impact scoring (BUKAN AI/LLM).

Output ke daily_news: source, headline, raw_url, impact_level (HIGH/MED/LOW).
is_key_trigger DEFAULT 0 (Giel flag manual nanti).

Health check per feed tiap run (`check_feed_health`) — pola sama dengan
`source_flags` API di Phase A: feed mati harus KELIHATAN tiap run lewat
`health_report`, bukan jadi backlog tersembunyi yang baru ketahuan
seminggu kemudian.

Acceptance:
  - Dedup by headline (jangan masuk 2x untuk headline sama)
  - impact_level selalu salah satu HIGH/MED/LOW
  - Feed mati -> di-skip, dicatat di health_report, TIDAK menghentikan
    feed lain (tidak pernah raise ke pemanggil)
"""
from __future__ import annotations

from typing import Any

import feedparser
import requests

from scrapers.base import keyword_matches, today_wib
from scrapers.feeds_config import FEEDS, IMPACT_KEYWORDS

DEFAULT_TIMEOUT = 10
HEADERS = {"User-Agent": "kastara-finance/0.1 (news feed health check)"}


def score_impact(headline: str) -> str:
    """Return 'HIGH' | 'MED' | 'LOW' berdasar keyword rule-based.
    HIGH menang atas MED kalau headline cocok keduanya."""
    h = (headline or "").lower()
    if keyword_matches(h, IMPACT_KEYWORDS["HIGH"]):
        return "HIGH"
    if keyword_matches(h, IMPACT_KEYWORDS["MED"]):
        return "MED"
    return "LOW"


def check_feed_health(url: str) -> tuple[str, str, list[Any]]:
    """Cek 1 feed: ('ok'|'dead', reason, entries). TIDAK PERNAH raise.

    'dead' kalau: request gagal, status != 200, parse gagal (bozo tanpa
    entries), atau 0 entry. 'ok' kalau parse sukses DAN ada >= 1 entry.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        return "dead", f"{type(exc).__name__}: {exc}", []

    if resp.status_code != 200:
        return "dead", f"HTTP {resp.status_code}", []

    parsed = feedparser.parse(resp.content)
    if not parsed.entries:
        reason = "parse gagal / bukan RSS valid" if getattr(parsed, "bozo", 0) else "0 entry"
        return "dead", reason, []

    return "ok", "", parsed.entries


def fetch_all_news(target_date: str | None = None) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Loop semua FEEDS enabled=True. Return (articles, health_report).

    articles: list {date, source, headline, raw_url, impact_level}, sudah
    dedup by headline (case-insensitive).
    health_report: {feed_name: "ok"|"dead"} untuk SEMUA feed enabled.
    """
    target_date = target_date or today_wib()
    health_report: dict[str, str] = {}
    seen: set[str] = set()
    articles: list[dict[str, Any]] = []

    for feed in FEEDS:
        if not feed.get("enabled"):
            continue
        name, url = feed["name"], feed["url"]
        status, reason, entries = check_feed_health(url)
        health_report[name] = status
        if status == "dead":
            print(f"[news] feed mati: {name} ({reason})")
            continue
        for entry in entries:
            headline = (getattr(entry, "title", "") or "").strip()
            if not headline:
                continue
            key = headline.lower()
            if key in seen:
                continue
            seen.add(key)
            articles.append({
                "date": target_date,
                "source": name,
                "headline": headline,
                "raw_url": getattr(entry, "link", "") or "",
                "impact_level": score_impact(headline),
            })

    return articles, health_report


if __name__ == "__main__":
    items, health = fetch_all_news()
    n_ok = sum(1 for v in health.values() if v == "ok")
    n_dead = sum(1 for v in health.values() if v == "dead")
    dead_names = [name for name, status in health.items() if status == "dead"]
    print(f"{len(items)} headline (dedup). RSS: {n_ok} ok, {n_dead} dead"
          + (f" → {dead_names}" if dead_names else ""))
    for it in items[:10]:
        print(f"  [{it['impact_level']:>4}] {it['source']}: {it['headline'][:80]}")
