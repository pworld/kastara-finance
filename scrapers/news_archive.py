"""Historical news backfill via each source's own on-site search (4 Agustus
2026) -- BUKAN RSS. `scrapers/news.py::fetch_all_news()` cuma bisa lihat
window rolling "sekarang" (RSS tidak punya jalur query balik ke tanggal
lampau) -- lihat docs/ROADMAP.md 4 Agustus 2026 utk audit lengkap kenapa
Wayback Machine & paid news API DITOLAK sebelum pendekatan ini dipilih.

Live-diverifikasi (bukan asumsi dari dokumentasi) terhadap 2 sumber:
  - CNBC Indonesia: API JSON publik `api/v2/search-result` (ditemukan lewat
    Network tab, bukan didokumentasikan) -- field `dtnewsdate` (tanggal
    asli, bukan tanggal snapshot) memungkinkan filter rentang akurat.
  - ANTARA Ekonomi: halaman search server-rendered (BeautifulSoup langsung,
    TANPA headless browser) -- tapi tanggal di listing berupa TEKS RELATIF
    ("1 jam lalu"), dikonversi ke tanggal absolut relatif ke waktu scrape,
    akurasi level-hari saja (sama seperti presisi `daily_news.date`).

5 sumber lain di `scrapers/feeds_config.py` (Investing ID, Bisnis.com, CNBC
Finance/Economy, Fed FOMC) BELUM diverifikasi -- JANGAN diasumsikan bekerja
sama seperti 2 di atas, masing-masing perlu tes langsung dulu sebelum
ditambah ke sini (lihat catatan open question di plan).

Return shape SAMA PERSIS dengan `scrapers.news.fetch_all_news()` (list of
dict {date, source, headline, raw_url, impact_level, rss_summary}) supaya
langsung bisa masuk `pipeline.run_daily.insert_news_dedup()` tanpa jalur
insert baru.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from typing import Any

from bs4 import BeautifulSoup

from scrapers.base import http_get, http_get_json
from scrapers.news import _clean_rss_summary, score_impact

CNBC_SEARCH_API = "https://www.cnbcindonesia.com/api/v2/search-result"
ANTARA_SEARCH_URL = "https://www.antaranews.com/search"


def _article_dict(date: str, source: str, headline: str, raw_url: str, summary: str | None = None) -> dict[str, Any]:
    """Bentuk dict sama seperti scrapers.news.fetch_all_news() -- impact
    scoring rule-based sama (score_impact), rss_summary HANYA utk HIGH
    (Addendum D §22.1 D3, pola sama persis scrapers/news.py)."""
    impact = score_impact(headline)
    return {
        "date": date, "source": source, "headline": headline, "raw_url": raw_url,
        "impact_level": impact,
        "rss_summary": _clean_rss_summary(summary) if impact == "HIGH" else None,
    }


def search_cnbcindonesia(
    keyword: str, date_from: str, date_to: str, *, page_size: int = 20, max_pages: int = 15, delay: float = 0.0,
) -> list[dict[str, Any]]:
    """Query API search CNBC Indonesia (idtype='1 4' = artikel+video semua
    kanal, diverifikasi live 4 Agustus 2026 lewat Network tab). API tidak
    punya param rentang tanggal -- filter `dtnewsdate` ("YYYY/MM/DD
    HH:MM:SS", tanggal terbit ASLI bukan tanggal fetch) di sisi Python.

    `isrelevance=0` = urut tanggal TERBARU DULU (diverifikasi live -- beda
    dari isrelevance=1 yang urut relevansi, jauh lebih recency-biased utk
    rentang lebar). Paginate lewat `start` offset, berhenti begitu 1 halaman
    penuh sudah lebih tua dari date_from (hasil newest-first, jadi hemat
    request drpd scan semua). API sendiri cap total di 10.000 hasil
    (diverifikasi live) -- utk keyword volume tinggi + rentang sangat lebar,
    `max_pages` mungkin habis sebelum tembus date_from; itu batas nyata
    sumbernya, bukan bug di sini. API sendiri CAP TOTAL di 10.000 hasil
    (field `total`, diverifikasi live 4 Agustus 2026) -- keyword dgn total
    >=10000 TIDAK PERNAH bisa tembus lebih jauh dari posisi ~9999, berapa
    pun `max_pages`/kesabaran diberikan (batas keras platform, bukan
    lambat). `delay` (detik) -- jeda antar-request, "santai" biar tidak
    membombardir sumbernya utk backfill dalam/lambat."""
    articles: list[dict[str, Any]] = []
    for page in range(max_pages):
        data = http_get_json(
            CNBC_SEARCH_API,
            params={"query": keyword, "idtype": "1 4", "start": page * page_size, "limit": page_size, "isrelevance": 0},
        )
        if delay:
            time.sleep(delay)
        items = (data or {}).get("data") or []
        if not items:
            break
        page_has_in_range = False
        for item in items:
            raw_date = item.get("dtnewsdate")
            if not raw_date:
                continue
            try:
                dt = datetime.strptime(raw_date, "%Y/%m/%d %H:%M:%S")
            except ValueError:
                continue
            date_str = dt.strftime("%Y-%m-%d")
            if date_str > date_to:
                continue  # lebih baru dari rentang -- lewati, jangan berhenti (halaman pertama bisa campur)
            if date_str < date_from:
                continue  # lebih tua dari rentang -- lewati item ini, tapi tandai halaman sudah masuk zona lama
            page_has_in_range = True
            headline = (item.get("strjudul") or "").strip()
            url = item.get("url") or ""
            if not headline or not url:
                continue
            articles.append(_article_dict(date_str, "CNBC Indonesia", headline, url, item.get("strringkasan")))
        oldest_on_page = min(
            (item.get("dtnewsdate") for item in items if item.get("dtnewsdate")), default=None
        )
        if oldest_on_page:
            oldest_date = datetime.strptime(oldest_on_page, "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%d")
            if oldest_date < date_from:
                break  # newest-first & sudah lewat batas bawah -- halaman berikutnya pasti lebih tua lagi
        if not page_has_in_range and page > 0:
            break
    return articles


# Konversi teks relatif Indonesia -> detik, dipakai ANTARA (search-nya tidak
# tampilkan tanggal absolut di listing, cuma "X jam/hari/minggu lalu").
_RELATIVE_UNIT_SECONDS = {"menit": 60, "jam": 3600, "hari": 86400, "minggu": 604800}

_ID_MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}


def _parse_antara_relative_date(text: str, *, now: datetime) -> str | None:
    """'1 jam lalu' / '3 hari lalu' / '2 minggu lalu' / 'kemarin' -> tanggal
    absolut 'YYYY-MM-DD' relatif ke `now` (waktu scrape). '3 Agustus 2026'
    (tanggal absolut, dipakai berita lebih lama) di-parse via nama bulan
    Indonesia. None kalau format tak dikenal -- jujur di-skip, bukan ditebak."""
    text = text.strip().lower()
    m = re.match(r"(\d+)\s+(menit|jam|hari|minggu)\s+(yang\s+)?lalu", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        dt = now - timedelta(seconds=n * _RELATIVE_UNIT_SECONDS[unit])
        return dt.strftime("%Y-%m-%d")
    if text == "kemarin":
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    m2 = re.match(r"(\d{1,2})\s+([a-z]+)\s+(\d{4})", text)
    if m2 and m2.group(2) in _ID_MONTHS:
        day, month, year = int(m2.group(1)), _ID_MONTHS[m2.group(2)], int(m2.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def search_antaranews(
    keyword: str, date_from: str, date_to: str, *, max_pages: int = 3, delay: float = 0.0,
) -> list[dict[str, Any]]:
    """Scrape halaman search ANTARA (server-rendered, diverifikasi live 4
    Agustus 2026 -- TIDAK butuh headless browser, requests+BeautifulSoup
    biasa). Hasil terbaru-dulu -- berhenti lebih awal begitu 1 halaman
    penuh sudah lebih tua dari date_from (hemat request, bukan scan semua
    halaman utk keyword umum). Paginasi ANTARA sendiri tidak reliable lewat
    ~page 100 (diverifikasi live -- mulai putar balik ke hasil live/segar),
    jadi kedalaman nyata lebih terbatas drpd CNBC. `delay` -- jeda antar-
    request (detik), "santai" biar tidak membombardir sumbernya."""
    now = datetime.now()
    articles: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        resp = http_get(ANTARA_SEARCH_URL, params={"q": keyword, "page": page})
        if delay:
            time.sleep(delay)
        soup = BeautifulSoup(resp.content, "html.parser")
        cards = soup.select("div.card__post-list")
        if not cards:
            break
        page_has_in_range = False
        for card in cards:
            link = card.select_one("a[href]")
            date_span = card.select_one("span.text-dark.text-capitalize")
            if not link or not date_span:
                continue
            date_str = _parse_antara_relative_date(date_span.get_text(), now=now)
            if not date_str:
                continue
            if date_str < date_from:
                continue
            if date_str > date_to:
                continue
            page_has_in_range = True
            headline = (link.get("title") or link.get_text()).strip()
            url = link.get("href") or ""
            if not headline or not url:
                continue
            articles.append(_article_dict(date_str, "ANTARA Ekonomi", headline, url))
        if not page_has_in_range:
            break
    return articles
