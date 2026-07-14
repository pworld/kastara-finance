"""Cron KEDUA (sore/malam), TERPISAH dari pipeline/run_daily.py (pagi).

Tujuan: isi `econ_calendar.actual` utk event HIGH-importance yang sudah
di-scrape ForexFactory (forecast/previous) tapi actual-nya masih kosong --
lihat scrapers/investing_calendar.py utk alasan kenapa perlu sumber kedua
dan kenapa scraper ini SENGAJA dipisah dari run_daily (bukan ditambah jadi
1x GET lagi di run_daily -- lihat docs/ROADMAP.md soal dampak "grab semua
cron 2x": tidak perlu, dan menambah risiko block ke scraper IDX yang lain).

TIDAK menyentuh run_daily.py ataupun jadwal paginya sama sekali.

Matching: investing.com (event_date halaman, country, event_name, actual)
dicocokkan ke baris econ_calendar existing yang importance='HIGH' DAN
actual IS NULL, dibatasi country sama + event_date dalam +-1 hari (jaga-jaga
beda zona waktu antara "hari ini" versi investing.com vs WIB, lihat catatan
di scrapers/investing_calendar.py). Nama event dicocokkan FUZZY (bukan exact
match) karena 2 sumber ini pakai istilah berbeda utk event yang sama (mis.
ForexFactory "CPI y/y" vs investing.com "CPI (YoY) (Jun)") -- pakai
difflib.SequenceMatcher atas nama yang sudah dinormalisasi (lowercase, buang
parenthetical, buang tanda baca).

SENGAJA KONSERVATIF: kalau tidak ada kandidat yang cukup mirip (skor <
MATCH_THRESHOLD), atau ada 2+ kandidat dengan skor sama-sama tinggi
(ambigu), event itu DI-SKIP -- lebih baik actual tetap kosong (bisa diisi
manual lewat dashboard) daripada salah tempel actual ke event yang salah.
Ditulis lewat web/writes.py::set_econ_actual() yang sudah ada, bukan bikin
write path baru.

Jalankan:
    python -m pipeline.run_investing_actual
"""
from __future__ import annotations

import difflib
import re
import sqlite3
from typing import Any

from db.connection import get_connection, init_db
from scrapers.investing_calendar import fetch_investing_actuals
from web.writes import set_econ_actual

MATCH_THRESHOLD = 0.5
DATE_WINDOW_DAYS = 1

_PAREN_RE = re.compile(r"\(([^)]*)\)")
_PUNCT_RE = re.compile(r"[^a-z0-9 ]")
_PERIOD_ALIASES = {"m/m", "mom", "y/y", "yoy", "q/q", "qoq"}


def _normalize_name(name: str) -> str:
    """Lowercase + samakan istilah antar sumber, biar "CPI (MoM) (Jun)"
    (investing.com) vs "CPI m/m" (ForexFactory) bisa dibandingkan apple-to-
    apple oleh SequenceMatcher.

    PENTING: parenthetical TIDAK bisa dibuang begitu saja -- investing.com
    naruh penanda periode ("(MoM)"/"(YoY)"/"(QoQ)") di DALAM kurung, sementara
    bulan rilis ("(Jun)") juga di dalam kurung. Kalau semua kurung dibuang
    rata, "CPI (MoM)" dan "CPI (YoY)" jadi sama-sama "cpi" -- persis
    penyebab kandidat "CPI m/m" vs "CPI y/y" ForexFactory jadi TIE (skor
    sama) dan ke-skip padahal ada match yang benar (ketemu pas verifikasi
    live run pertama). Solusi: normalisasi "m/m"/"y/y"/"q/q" ke "mom"/"yoy"/
    "qoq" DULU, lalu buka tiap kurung -- isinya dipertahankan HANYA kalau
    salah satu dari 3 penanda periode itu, selain itu (nama bulan/kuartal)
    dibuang seperti biasa."""
    name = name.lower()
    name = name.replace("m/m", "mom").replace("y/y", "yoy").replace("q/q", "qoq")

    def _paren_repl(m: re.Match) -> str:
        inner = m.group(1).strip().lower()
        return f" {inner} " if inner in _PERIOD_ALIASES else " "

    name = _PAREN_RE.sub(_paren_repl, name)
    name = _PUNCT_RE.sub(" ", name)
    return " ".join(name.split())


def _find_candidates(conn: sqlite3.Connection, event_date: str, country: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT id, event_name FROM econ_calendar "
        "WHERE importance = 'HIGH' AND actual IS NULL AND country = ? "
        "AND event_date BETWEEN date(?, ?) AND date(?, ?)",
        (country, event_date, f"-{DATE_WINDOW_DAYS} day", event_date, f"+{DATE_WINDOW_DAYS} day"),
    ).fetchall()
    return [dict(r) for r in rows]


def _best_match(target_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return kandidat terbaik kalau skornya lolos threshold DAN tidak
    ambigu (tidak ada kandidat lain dengan skor sama tinggi). None kalau
    tidak ada yang cukup yakin -- SENGAJA konservatif, lihat docstring modul."""
    norm_target = _normalize_name(target_name)
    scored = sorted(
        (
            (difflib.SequenceMatcher(None, norm_target, _normalize_name(c["event_name"])).ratio(), c)
            for c in candidates
        ),
        key=lambda pair: pair[0], reverse=True,
    )
    if not scored or scored[0][0] < MATCH_THRESHOLD:
        return None
    if len(scored) > 1 and scored[1][0] == scored[0][0]:
        return None  # ambigu, skip
    return scored[0][1]


def run_investing_actual(db_path=None) -> dict[str, Any]:
    """Jalankan pass kedua: fetch investing.com HIGH+actual, cocokkan &
    UPDATE econ_calendar yang match. Return ringkasan. Tidak pernah raise
    (scraper sudah non-crashing; matching di sini juga defensif)."""
    init_db(db_path)
    fetched = fetch_investing_actuals()
    items = fetched["items"]

    matched = 0
    skipped_no_match = 0
    with get_connection(db_path) as conn:
        for it in items:
            candidates = _find_candidates(conn, it["event_date"], it["country"])
            best = _best_match(it["event_name"], candidates)
            if best is None:
                skipped_no_match += 1
                continue
            if set_econ_actual(conn, best["id"], it["actual"]):
                matched += 1
            else:
                skipped_no_match += 1
        conn.commit()

    summary = {
        "fetched": len(items),
        "matched": matched,
        "skipped_no_match": skipped_no_match,
        "source_flags": fetched["source_flags"],
    }
    _print_summary(summary)
    return summary


def _print_summary(s: dict[str, Any]) -> None:
    print("\n===== RINGKASAN investing.com actual pass =====")
    print(f"  di-fetch (HIGH ber-actual) : {s['fetched']}")
    print(f"  matched & tersimpan        : {s['matched']}")
    print(f"  di-skip (tidak match)      : {s['skipped_no_match']}")
    print("  flags:")
    for k, v in sorted(s["source_flags"].items()):
        mark = {"ok": "✓", "fail": "✗", "skip": "·"}.get(v, "?")
        print(f"    {mark} {k} = {v}")
    print("================================================\n")


if __name__ == "__main__":
    run_investing_actual()
