"""Seed asset_context_weight — pembobotan driver per aset (Master Plan §4.3).

BTC dulu (plan_b.txt §7.7), lalu GOLD/SP500/IHSG/USDIDR/USDJPY (Phase F+
expansion, Master Plan §10) — bobot persis contoh di §4.3 utk kategori
FOREX (rate_differential/trade_balance), notes disesuaikan per pasangan
mata uang (USDIDR = BI vs Fed + neraca dagang RI, USDJPY = BOJ vs Fed +
neraca dagang Jepang-AS).

Idempotent: cek (instrument, driver) dulu, skip kalau sudah ada — bukan
INSERT OR IGNORE (tabel ini tidak punya UNIQUE index), jadi dedup manual.

Pakai:
    python -m pipeline.seed_context_weight
"""
from __future__ import annotations

from db.connection import get_connection, init_db

BTC_WEIGHTS = [
    ("net_liquidity", "HIGH", "Driver utama BTC — WALCL-RRP-TGA"),
    ("etf_flow", "HIGH", "Net flow ETF spot BTC, belum ada scraper otomatis (Phase D)"),
    ("fear_greed", "MED", "Sentimen pasar crypto, sudah ada di daily_market"),
    ("dxy", "MED", "Kekuatan dolar, korelasi negatif historis dgn BTC"),
]

GOLD_WEIGHTS = [
    ("real_yield", "HIGH", "Real yield (US10Y - ekspektasi inflasi) — opportunity cost pegang gold"),
    ("dxy", "HIGH", "Kekuatan dolar, korelasi negatif historis dgn gold"),
    ("geopolitik", "MED", "Safe-haven demand saat tensi geopolitik naik — dibaca manual, bukan scraper"),
]

SP500_WEIGHTS = [
    ("earnings", "HIGH", "Earnings season — dibaca manual dari kalender/berita, bukan scraper"),
    ("fed_path", "HIGH", "Arah kebijakan Fed (FedWatch/Dot Plot — expectations)"),
    ("net_liquidity", "MED", "WALCL-RRP-TGA, sama driver dgn BTC tapi bobot lebih rendah utk equity"),
]

IHSG_WEIGHTS = [
    ("sbn_foreign_flow", "HIGH", "Arah dana asing di SBN — proxy sentimen asing ke pasar Indonesia"),
    ("usd_idr", "HIGH", "Pelemahan/penguatan rupiah — sensitif utk saham lokal"),
    ("bi_rate", "HIGH", "Arah suku bunga BI"),
    ("komoditas", "MED", "Harga komoditas ekspor (CPO, batubara, dll) — dibaca manual"),
]

# FOREX generik per Master Plan §4.3 -- dipakai utk USDIDR.
FOREX_WEIGHTS = [
    ("rate_differential", "HIGH", "Selisih suku bunga BI vs Fed — driver utama carry/forex"),
    ("trade_balance", "MED", "Neraca dagang Indonesia — tekanan struktural rupiah"),
]

# FOREX generik per Master Plan §4.3 -- dipakai utk USDJPY (BOJ notorious
# ultra-dovish relatif Fed -> rate differential jadi driver dominan carry
# trade JPY).
USDJPY_WEIGHTS = [
    ("rate_differential", "HIGH", "Selisih suku bunga BOJ vs Fed — driver utama carry trade JPY"),
    ("trade_balance", "MED", "Neraca dagang Jepang-AS — tekanan struktural yen"),
]

# Phase J+ (Build Contract v1.3, J-10) -- level='INSTRUMENT' saja utk sekarang
# (BUKAN pewarisan index->sector->instrument penuh spt disinggung kontrak §3 --
# butuh desain lookup fallback terpisah, di luar scope seed manual ini).
BBCA_WEIGHTS = [
    ("ihsg_foreign_flow", "HIGH",
     "Arah dana asing ke saham IDX — emiten besar seperti BBCA sering jadi "
     "proxy sentimen asing thd IHSG, bukan cuma level-index"),
    ("bi_rate", "HIGH", "Arah suku bunga BI — langsung pengaruhi NIM/margin bunga bank"),
    ("usd_idr", "MED", "Stabilitas rupiah — sentimen makro lebih luas, bukan driver langsung "
     "earnings bank domestik"),
    ("sector_fundamentals", "MED",
     "Kondisi sektor perbankan (kredit, NPL industri) — dibaca manual, belum ada scraper otomatis"),
]

TSLA_WEIGHTS = [
    ("fed_path", "HIGH", "Arah kebijakan Fed — saham growth/high-multiple sensitif ke suku bunga AS"),
    ("earnings", "HIGH",
     "Earnings season & guidance — volatilitas TSLA historis besar di sekitar rilis earnings"),
    ("net_liquidity", "MED", "WALCL-RRP-TGA, driver sama dgn BTC/SP500 tapi bobot growth-stock spesifik"),
    ("dxy", "MED", "Kekuatan dolar — pengaruh tidak langsung lewat sentimen risk-on/off growth stock"),
]


def seed_instrument(conn, instrument: str, weights: list[tuple[str, str, str]]) -> int:
    """Insert (instrument, driver, weight, notes) kalau (instrument, driver)
    belum ada. Return jumlah baris baru."""
    inserted = 0
    for driver, weight, notes in weights:
        exists = conn.execute(
            "SELECT 1 FROM asset_context_weight WHERE instrument = ? AND driver = ?",
            (instrument, driver),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            "INSERT INTO asset_context_weight (instrument, driver, weight, notes) "
            "VALUES (?, ?, ?, ?)",
            (instrument, driver, weight, notes),
        )
        inserted += 1
    return inserted


def main() -> None:
    init_db()
    targets = [
        ("BTC", BTC_WEIGHTS), ("GOLD", GOLD_WEIGHTS), ("SP500", SP500_WEIGHTS),
        ("IHSG", IHSG_WEIGHTS), ("USDIDR", FOREX_WEIGHTS), ("USDJPY", USDJPY_WEIGHTS),
        ("BBCA", BBCA_WEIGHTS), ("TSLA", TSLA_WEIGHTS),
    ]
    with get_connection() as conn:
        for instrument, weights in targets:
            n = seed_instrument(conn, instrument, weights)
            print(f"[seed_context_weight] {instrument}: {n} baris baru ditambah.")
        conn.commit()


if __name__ == "__main__":
    main()
