"""News scraper: RSS feeds (registry di scrapers/feeds_config.py) + rule-based
impact scoring (BUKAN AI/LLM).

Output ke daily_news: source, headline, raw_url, impact_level (HIGH/MED/LOW),
rss_summary (Addendum D §22.3 D-1 -- summary/description bawaan feed apa
adanya, HTML di-strip, NULL kalau feed tak sertakan). for_reading DEFAULT 0
(Giel flag manual nanti -- rename fungsional dari is_key_trigger, Addendum C
§21.2).

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

import re
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

from scrapers.base import keyword_matches, today_wib
from scrapers.feeds_config import FEEDS, IMPACT_KEYWORDS

DEFAULT_TIMEOUT = 10
HEADERS = {"User-Agent": "kastara-finance/0.1 (news feed health check)"}

# Addendum D §22.3 (D-1) -- simpan summary/description bawaan feed APA ADANYA
# (nol LLM, nol fetch tambahan), cuma strip HTML markup + rapikan whitespace +
# batasi panjang biar tidak membengkak di UI/prompt persona. Batas 400 char
# cukup utk 2-3 baris ringkas (§22.3 UI: "teks abu 2-3 baris").
RSS_SUMMARY_MAX_LEN = 400


def _clean_rss_summary(raw: str | None) -> str | None:
    """Strip HTML (banyak feed embed <p>/<a> di description), rapikan
    whitespace, potong ke RSS_SUMMARY_MAX_LEN. Return None kalau kosong
    setelah dibersihkan -- NULL wajar utk feed yang tak sertakan summary."""
    if not raw:
        return None
    text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    if len(text) > RSS_SUMMARY_MAX_LEN:
        text = text[:RSS_SUMMARY_MAX_LEN].rstrip() + "…"
    return text


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
                # Addendum D §22.3 (D-1): feedparser alias `description`->`summary`,
                # cek keduanya defensif. Tidak semua feed punya -> None wajar.
                "rss_summary": _clean_rss_summary(getattr(entry, "summary", None) or getattr(entry, "description", None)),
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
