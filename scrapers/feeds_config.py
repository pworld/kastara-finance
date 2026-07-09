"""Registry feed RSS. Ganti url/enabled di sini, JANGAN di news.py.

`category` dipakai utk pengelompokan (bukan impact scoring — impact
tetap murni dari IMPACT_KEYWORDS di headline, generik lintas kategori).

Semua URL di bawah DIVERIFIKASI LANGSUNG (HTTP GET + parse feedparser)
saat registry ini ditulis — bukan asumsi dari riset:
  - Kontan (`kontan.co.id/feed` DAN `/rss`) TERNYATA MATI: return halaman
    HTML homepage biasa (bozo=1, 0 entries), bukan XML/RSS, bahkan dengan
    header browser-realistis (bukan soal bot-block, memang sudah dimatikan
    penyedianya).
  - Bisnis.com: URL lama (`bisnis.com/rss/market`, `finansial.bisnis.com
    /rss`) 404. URL yang benar-benar aktif: `rss.bisnis.com` (subdomain
    beda, ditemukan lewat pencarian ulang, bukan salah satu kandidat awal).
"""
from __future__ import annotations

# ── GLOBAL MACRO (paling penting untuk forward layer) ──
FEEDS = [
    {"name": "Fed FOMC", "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
     "category": "FED", "enabled": True},
    {"name": "CNBC Finance", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
     "category": "MACRO", "enabled": True},
    {"name": "CNBC Economy", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
     "category": "MACRO", "enabled": True},
    {"name": "Investing ID", "url": "https://id.investing.com/rss/news.rss",
     "category": "MACRO", "enabled": True},

    # ── INDONESIA ──
    {"name": "CNBC Indonesia", "url": "https://www.cnbcindonesia.com/market/rss",
     "category": "ID", "enabled": True},
    {"name": "ANTARA Ekonomi", "url": "https://www.antaranews.com/rss/ekonomi",
     "category": "ID", "enabled": True},
    {"name": "Bisnis.com", "url": "https://rss.bisnis.com/",
     "category": "ID", "enabled": True},

    # ── MATI / TIDAK RELIABLE (disabled, disimpan sebagai catatan) ──
    {"name": "Reuters", "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
     "category": "MACRO", "enabled": False,
     "note": "HTTP 404 dikonfirmasi langsung — Reuters tidak menyediakan RSS "
             "publik reliable sejak ~2020. Ditutupi CNBC Finance/Economy + "
             "Investing ID."},
    {"name": "Kontan", "url": "https://www.kontan.co.id/feed",
     "category": "ID", "enabled": False,
     "note": "Dikonfirmasi mati langsung (GET + browser UA): return halaman "
             "HTML homepage, 0 entries, bukan XML. /rss (URL lama) sama "
             "matinya. Ditutupi CNBC Indonesia + ANTARA + Bisnis.com."},
]

# Keyword utk impact scoring (rule-based, BUKAN AI). Mudah ditambah.
# HIGH menang atas MED kalau headline cocok keduanya (mis. "the fed" ada
# di MED tapi headline yang mengandung "fed" polos sudah kena HIGH duluan).
IMPACT_KEYWORDS = {
    "HIGH": ["fed", "fomc", "rate cut", "rate hike", "suku bunga",
             "cpi", "inflation", "inflasi", "powell", "bank indonesia", "bi rate"],
    "MED": ["etf", "earnings", "gdp", "nasdaq", "unemployment", "ihsg",
            "rupiah", "the fed", "obligasi", "yield"],
    # sisanya -> LOW
}
