"""Pure functions tulis-DB untuk Phase C (dashboard write-enabled).

Dipisah dari `web/app.py` supaya testable tanpa Flask (pola sama seperti
`pipeline/add_article.py`: fungsi insert murni terpisah dari CLI/route
wrapper). Semua fungsi di sini murni CRUD manual — **tidak ada** logic
AI/LLM, tidak ada execution/trading, sesuai plan_c.txt §0. Pengecualian:
`save_persona_analysis()` MENYIMPAN teks yang sudah digenerate LLM (lihat
`llm/persona_analysis.py`, deviasi eksplisit dari plan_c.txt §0 utk Panel 4
4-Lensa) -- fungsi ini sendiri tetap CRUD murni (cuma tulis string ke DB),
pemanggilan LLM-nya terjadi di modul lain sebelum teksnya sampai ke sini.

Konvensi `reading_workspace.lens` (Panel 4 & 6, bukan enum ketat di DB):
  GEMA / LEON / AKELA / RIVAN  -> 4 analisa Panel 4 (AI-generated via
                                  llm/persona_analysis.py, lihat save_persona_analysis())
  EXTERNAL_AI                  -> catatan banding AI eksternal (opsional, manual)
  CONFLICT                     -> conflict notes (opsional, manual)
  SYNTHESIS                    -> paragraf sintesis Panel 6 (manual)
  OUTLOOK:<INSTRUMENT>         -> stance outlook Panel 6 (Bullish/Bearish/
                                  Neutral) per instrument, 1 baris per hari
                                  (upsert), lihat save_outlook()
"""
from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from scrapers.base import created_at, keyword_matches, today_wib

READING_LENSES = ("GEMA", "LEON", "AKELA", "RIVAN")


# ---------- Panel 2: for_reading curation (Addendum C §21.2 — renamed dari
# is_key_trigger; is_key_trigger LAMA dibiarkan beku di schema, jangan DROP,
# DB hidup, tapi tidak dibaca/ditulis lagi setelah migrasi one-time di
# db/connection.py::_migrate_columns()) ----------

def set_for_reading(conn: sqlite3.Connection, news_id: int, for_reading: bool = True) -> bool:
    """Update daily_news.for_reading by id. Return False kalau id tidak ada.
    Kurasi ("penting untuk saya, sekarang") -- beda pertanyaan dari tag
    (klasifikasi "berita ini tentang apa"), lihat docstring modul §21.0."""
    exists = conn.execute("SELECT 1 FROM daily_news WHERE id = ?", (news_id,)).fetchone()
    if not exists:
        return False
    conn.execute(
        "UPDATE daily_news SET for_reading = ? WHERE id = ?",
        (1 if for_reading else 0, news_id),
    )
    return True


def set_display_subtitle(conn: sqlite3.Connection, news_id: int, display_subtitle: str | None) -> bool:
    """Update daily_news.display_subtitle by id -- judul/catatan Giel di
    kolom TERPISAH (headline asli TIDAK PERNAH ditimpa, keputusan #3, pola
    sama literal_statement vs giel_inference). Return False kalau id tidak ada."""
    exists = conn.execute("SELECT 1 FROM daily_news WHERE id = ?", (news_id,)).fetchone()
    if not exists:
        return False
    conn.execute(
        "UPDATE daily_news SET display_subtitle = ? WHERE id = ?",
        (display_subtitle, news_id),
    )
    return True


# ---------- Panel 3: Economic Calendar actual (manual, sumber tidak sediakan) ----------

def set_econ_actual(conn: sqlite3.Connection, event_id: int, actual: str) -> bool:
    """Update econ_calendar.actual by id. ForexFactory tidak pernah kasih
    kolom ini (lihat scrapers/econ_calendar.py) -- diisi manual pas rilis
    keluar. Return False kalau id tidak ada."""
    exists = conn.execute("SELECT 1 FROM econ_calendar WHERE id = ?", (event_id,)).fetchone()
    if not exists:
        return False
    conn.execute("UPDATE econ_calendar SET actual = ? WHERE id = ?", (actual, event_id))
    return True


# ---------- Panel 3: Earnings emiten (READ-ONLY — J-15 gel.2, kontrak §19.5) ----------
# earnings_calendar diisi scraper J-7 (backfill_earnings.py), BUKAN manual --
# jadi di sini cuma read. Ditampilkan di Forward panel bareng econ_calendar
# ("sumbu waktu katalis") + jadi penegak rule "no hold through earnings" saham
# AS (kontrak §18 keputusan #3).

def list_earnings_calendar(conn: sqlite3.Connection, limit: int = 40) -> list[dict[str, Any]]:
    """Earnings emiten universe, dari 30 hari lalu s.d. mendatang (window
    mirror econ_calendar: yang barusan lewat ikut tampil supaya actual EPS-nya
    kebaca). LEFT JOIN instrument_metadata utk `market` (dipakai frontend
    bedakan aturan US vs IDX). Urut naik by tanggal."""
    rows = conn.execute(
        "SELECT e.instrument, e.earnings_date, e.eps_forecast, e.eps_actual, "
        "e.event_type, m.market "
        "FROM earnings_calendar e "
        "LEFT JOIN instrument_metadata m ON m.instrument = e.instrument "
        "WHERE e.earnings_date >= date(?, '-30 days') "
        "ORDER BY e.earnings_date ASC LIMIT ?",
        (today_wib(), limit),
    ).fetchall()
    return [dict(r) for r in rows]


def list_earnings_warnings(conn: sqlite3.Connection, within_days: int = 14) -> list[dict[str, Any]]:
    """Peringatan earnings utk posisi TERBUKA (trading_journal.outcome='ONGOING')
    yang instrumennya punya earnings mendatang dalam `within_days` hari
    (kontrak §19.5). 1 baris per instrument (earnings terdekat). `hard_rule`
    True utk saham AS -- keputusan #3: WAJIB tutup penuh sebelum earnings;
    IDX tidak punya aturan tutup-penuh (gap lebih kecil, §13.2) -> informatif."""
    today = today_wib()
    rows = conn.execute(
        "SELECT j.instrument, m.market, MIN(e.earnings_date) AS earnings_date, "
        "CAST(julianday(MIN(e.earnings_date)) - julianday(?) AS INTEGER) AS days_until "
        "FROM trading_journal j "
        "JOIN earnings_calendar e ON e.instrument = j.instrument "
        "LEFT JOIN instrument_metadata m ON m.instrument = j.instrument "
        "WHERE j.outcome = 'ONGOING' "
        "AND e.earnings_date >= ? AND e.earnings_date <= date(?, '+' || ? || ' days') "
        "GROUP BY j.instrument, m.market "
        "ORDER BY earnings_date ASC",
        (today, today, today, within_days),
    ).fetchall()
    return [{**dict(r), "hard_rule": r["market"] == "US"} for r in rows]


# ---------- Panel 3: Expectations (Layer B, Phase D — manual, tidak ada
# sumber gratis: CME FedWatch API resmi berbayar, Dot Plot rilis PDF
# kuartalan) ----------

def insert_expectation(
    conn: sqlite3.Connection, *, date: str, metric: str, value: float,
    horizon: str | None, source: str | None,
) -> int:
    cur = conn.execute(
        "INSERT INTO expectations (date, metric, value, horizon, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (date, metric, value, horizon, source, created_at()),
    )
    return cur.lastrowid


def list_expectations(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM expectations ORDER BY date DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Panel 3: Positioning (Layer C, Phase D) — COT + BTC ETF flow
# otomatis (scrapers/positioning.py) + SBN foreign flow & override ETF
# manual (sumber DJPPR tidak scrape-able reliable) ----------

def insert_positioning_manual(
    conn: sqlite3.Connection, *, date: str, instrument: str, metric: str,
    value: float, source: str | None,
) -> None:
    """Insert/override 1 row positioning. Natural key (date, instrument,
    metric) UNIQUE (idx_positioning_dedup) -> ON CONFLICT DO UPDATE, jadi
    form ini juga bisa dipakai koreksi manual atas row hasil scrape (mis.
    ETF flow yang perlu dikoreksi), bukan cuma SBN."""
    conn.execute(
        "INSERT INTO positioning (date, instrument, metric, value, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(date, instrument, metric) DO UPDATE SET "
        "value=excluded.value, source=excluded.source",
        (date, instrument, metric, value, source, created_at()),
    )


def list_positioning(conn: sqlite3.Connection, limit: int = 30) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM positioning ORDER BY date DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Panel 3: Disonansi Flag (Layer A vs Layer C, aturan sederhana,
# BUKAN AI — murni perbandingan arah/sign angka) ----------

def compute_disonansi(conn: sqlite3.Connection) -> dict[str, Any]:
    """Bandingkan stance_score terbaru (policy_tracker) vs tren cot_net_long
    DXY 14 hari terakhir (proxy arah "uang besar" makro). Return
    {'available': False} kalau data belum cukup (butuh >=1 stance_score
    DAN >=2 baris cot_net_long DXY dalam window)."""
    policy_row = conn.execute(
        "SELECT date, speaker, stance_score FROM policy_tracker "
        "WHERE stance_score IS NOT NULL ORDER BY date DESC, id DESC LIMIT 1"
    ).fetchone()
    dxy_rows = conn.execute(
        "SELECT date, value FROM positioning "
        "WHERE instrument='DXY' AND metric='cot_net_long' "
        "AND date >= date((SELECT MAX(date) FROM positioning WHERE instrument='DXY' "
        "AND metric='cot_net_long'), '-14 days') "
        "ORDER BY date ASC"
    ).fetchall()

    if not policy_row or policy_row["stance_score"] == 0 or len(dxy_rows) < 2:
        return {"available": False}

    stance = policy_row["stance_score"]
    dxy_trend = dxy_rows[-1]["value"] - dxy_rows[0]["value"]
    # Hawkish (stance>0) SEHARUSNYA searah DXY net-long naik (USD kuat);
    # dovish (stance<0) SEHARUSNYA searah DXY net-long turun. Kalau tanda
    # berlawanan -> retorika dan posisi uang besar tidak sinkron.
    flagged = (stance > 0 and dxy_trend < 0) or (stance < 0 and dxy_trend > 0)
    return {
        "available": True,
        "flagged": flagged,
        "policy_date": policy_row["date"],
        "policy_speaker": policy_row["speaker"],
        "stance_score": stance,
        "dxy_net_long_trend": dxy_trend,
        "note": (
            f"{policy_row['speaker'] or 'Speaker'} ({policy_row['date']}) stance={stance}, "
            f"DXY cot_net_long trend 14 hari={dxy_trend:+.0f}"
        ),
    }


# ---------- Panel 3: Policy Tracker (manual, independen Phase D) ----------

def insert_policy_note(
    conn: sqlite3.Connection, *, date: str, speaker: str | None, institution: str | None,
    source_url: str | None, literal_statement: str, stance_score: int | None,
    inference: str | None, inference_flag: str | None, drift_note: str | None,
) -> int:
    """Insert 1 entri policy_tracker. `inference_flag` harus TESTABLE atau
    SPEKULATIF kalau diisi (disiplin editorial Master Plan §4.2) — divalidasi
    di layer route (web/app.py), bukan di sini (fungsi ini murni tulis)."""
    cur = conn.execute(
        "INSERT INTO policy_tracker (date, speaker, institution, source_url, "
        "literal_statement, stance_score, inference, inference_flag, drift_note, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (date, speaker, institution, source_url, literal_statement, stance_score,
         inference, inference_flag, drift_note, created_at()),
    )
    return cur.lastrowid


def list_policy_notes(conn: sqlite3.Connection, limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM policy_tracker ORDER BY date DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Panel 4: Reading Workspace (4 lensa + external AI + conflict) ----------

def save_reading_entry(conn: sqlite3.Connection, date: str, lens: str, notes: str) -> int:
    """Insert 1 baris reading_workspace. Dipanggil per-lensa, bukan 1 form besar."""
    cur = conn.execute(
        "INSERT INTO reading_workspace (date, lens, notes, created_at) VALUES (?, ?, ?, ?)",
        (date, lens, notes, created_at()),
    )
    return cur.lastrowid


def save_panel4(
    conn: sqlite3.Connection, date: str, *,
    gema: str | None = None, leon: str | None = None,
    akela: str | None = None, rivan: str | None = None,
    external_ai: str | None = None, conflict: str | None = None,
) -> list[int]:
    """Simpan semua kolom Panel 4 sekaligus — 1 row per field yang TERISI
    (skip yang kosong, tidak bikin row kosong)."""
    fields = {
        "GEMA": gema, "LEON": leon, "AKELA": akela, "RIVAN": rivan,
        "EXTERNAL_AI": external_ai, "CONFLICT": conflict,
    }
    ids = []
    for lens, text in fields.items():
        if text and text.strip():
            ids.append(save_reading_entry(conn, date, lens, text.strip()))
    return ids


def list_reading_entries(conn: sqlite3.Connection, date: str) -> list[dict[str, Any]]:
    """Semua entri reading_workspace untuk 1 tanggal (buat ditampilkan ulang)."""
    rows = conn.execute(
        "SELECT * FROM reading_workspace WHERE date = ? ORDER BY id", (date,)
    ).fetchall()
    return [dict(r) for r in rows]


def save_persona_analysis(conn: sqlite3.Connection, date: str, lens: str, text: str) -> int:
    """Simpan hasil analisa AI (llm/persona_analysis.py) utk 1 persona
    (GEMA/LEON/AKELA/RIVAN). Upsert (DELETE lalu INSERT, pola sama dengan
    save_outlook) -- re-run persona yang sama di hari yang sama OVERWRITE,
    tidak numpuk duplikat di histori Panel 7 (beda dari SYNTHESIS yang
    sengaja append-only). Caller (route) yang validasi `lens` valid."""
    conn.execute(
        "DELETE FROM reading_workspace WHERE date = ? AND lens = ?", (date, lens)
    )
    return save_reading_entry(conn, date, lens, text)


# ---------- Panel 6: Synthesis + Trading Journal + Prediction Log ----------

def save_synthesis(conn: sqlite3.Connection, date: str, text: str) -> int | None:
    """Synthesis Panel 6 disimpan sebagai reading_workspace lens=SYNTHESIS.
    None kalau text kosong (tidak bikin row kosong)."""
    if not text or not text.strip():
        return None
    return save_reading_entry(conn, date, "SYNTHESIS", text.strip())


def latest_synthesis(conn: sqlite3.Connection, date: str) -> str | None:
    """Teks synthesis TERBARU utk 1 tanggal (buat auto-load Panel 6 saat
    ganti tanggal). None kalau belum ada. Synthesis append-only, jadi ambil
    id terbesar."""
    row = conn.execute(
        "SELECT notes FROM reading_workspace WHERE date = ? AND lens = 'SYNTHESIS' "
        "ORDER BY id DESC LIMIT 1", (date,),
    ).fetchone()
    return row["notes"] if row else None


# ---------- Panel 6: Outlook per instrumen (reuse reading_workspace,
# lens="OUTLOOK:<INSTRUMENT>", 1 stance per instrument per hari -> upsert) ----------

def save_outlook(conn: sqlite3.Connection, date: str, instrument: str, stance: str) -> None:
    """Simpan stance outlook (Bullish/Bearish/Neutral) utk 1 instrument di 1
    tanggal. Upsert manual (DELETE lalu INSERT) karena reading_workspace
    tidak punya UNIQUE index -> pastikan cuma 1 baris per (date, instrument)."""
    lens = f"OUTLOOK:{instrument.upper()}"
    conn.execute(
        "DELETE FROM reading_workspace WHERE date = ? AND lens = ?", (date, lens)
    )
    save_reading_entry(conn, date, lens, stance)


def list_outlook(conn: sqlite3.Connection, date: str) -> dict[str, str]:
    """Return {instrument: stance} utk 1 tanggal (buat restore dropdown Panel 6)."""
    rows = conn.execute(
        "SELECT lens, notes FROM reading_workspace WHERE date = ? AND lens LIKE 'OUTLOOK:%' "
        "ORDER BY id", (date,),
    ).fetchall()
    return {r["lens"].split(":", 1)[1]: r["notes"] for r in rows}


def insert_trading_journal(
    conn: sqlite3.Connection, *, date: str, instrument: str, setup_type: str | None,
    entry_price: float | None, sl_price: float | None, tp1_price: float | None,
    outcome: str | None, personal_notes: str | None, lesson_learned: str | None,
    planned_size: float | None = None, actual_size: float | None = None,
    skip_reason: str | None = None, return_asset_ccy: float | None = None,
    return_idr: float | None = None,
) -> int:
    """Ekstensi Phase J+ Build Contract v1.3 §14/J-13 (semua parameter baru
    OPSIONAL, backward-compatible dgn caller lama): `planned_size` dari
    `analysis/sizing.py::suggest_position_size()` (lihat `/api/sizing/
    suggest`), `actual_size` yang benar-benar dieksekusi Giel (bisa beda
    dari planned krn harga eksekusi riil), `skip_reason` kalau sinyal
    dilewati (mis. RISK_CAPACITY_EXCEEDED), `return_asset_ccy`/
    `return_idr` P&L ganda utk aset USD (kontrak §13.2)."""
    cur = conn.execute(
        "INSERT INTO trading_journal (date, instrument, setup_type, entry_price, "
        "sl_price, tp1_price, outcome, personal_notes, lesson_learned, created_at, "
        "planned_size, actual_size, skip_reason, return_asset_ccy, return_idr) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (date, instrument, setup_type, entry_price, sl_price, tp1_price,
         outcome, personal_notes, lesson_learned, created_at(),
         planned_size, actual_size, skip_reason, return_asset_ccy, return_idr),
    )
    return cur.lastrowid


def insert_prediction(
    conn: sqlite3.Connection, *, date_made: str, horizon: str, claim: str,
    confidence: int | None, basis: str | None, target_date: str,
) -> int:
    """was_actioned default 0, outcome/lesson NULL — diisi nanti via score_prediction()."""
    cur = conn.execute(
        "INSERT INTO prediction_log (date_made, horizon, claim, confidence, basis, "
        "target_date, outcome, was_actioned, lesson, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, NULL, 0, NULL, ?)",
        (date_made, horizon, claim, confidence, basis, target_date, created_at()),
    )
    return cur.lastrowid


def list_due_predictions(conn: sqlite3.Connection, as_of_date: str) -> list[dict[str, Any]]:
    """Prediksi target_date <= as_of_date yang belum di-skor (outcome IS NULL)
    -- widget 'Skor Prediksi' Panel 6."""
    rows = conn.execute(
        "SELECT * FROM prediction_log WHERE target_date <= ? AND outcome IS NULL "
        "ORDER BY target_date", (as_of_date,),
    ).fetchall()
    return [dict(r) for r in rows]


def score_prediction(conn: sqlite3.Connection, prediction_id: int, outcome: str, lesson: str | None = None) -> bool:
    """outcome: BENAR/SALAH/PARTIAL. Return False kalau id tidak ada."""
    exists = conn.execute("SELECT 1 FROM prediction_log WHERE id = ?", (prediction_id,)).fetchone()
    if not exists:
        return False
    conn.execute(
        "UPDATE prediction_log SET outcome = ?, lesson = ? WHERE id = ?",
        (outcome, lesson, prediction_id),
    )
    return True


# ---------- Panel 7: Riwayat (arsip input manual — history read-only) ----------
# Chart/news/snapshot sudah punya view historis sendiri; input manual (synthesis,
# prediksi, trading journal, 4 lensa) belum. Fungsi di bawah CUMA baca, buat
# ditampilkan sebagai jurnal/arsip di Panel 7.

def list_synthesis_log(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    """Semua entri synthesis (reading_workspace lens=SYNTHESIS) lintas tanggal,
    terbaru dulu. Append-only -> revisi muncul sebagai riwayat."""
    rows = conn.execute(
        "SELECT date, notes, created_at FROM reading_workspace WHERE lens = 'SYNTHESIS' "
        "ORDER BY date DESC, id DESC LIMIT ?", (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_predictions(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    """Seluruh track-record prediction_log (bukan cuma yang jatuh tempo),
    terbaru dulu — 'jurnal book' prediksi."""
    rows = conn.execute(
        "SELECT * FROM prediction_log ORDER BY date_made DESC, id DESC LIMIT ?", (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_trading_journal(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    """Seluruh riwayat trading_journal, terbaru dulu — 'jurnal book' entry trading."""
    rows = conn.execute(
        "SELECT * FROM trading_journal ORDER BY date DESC, id DESC LIMIT ?", (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_reading_history(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    """Riwayat 4 lensa & catatan reading (reading_workspace) lintas tanggal,
    KECUALI SYNTHESIS (punya view sendiri) & OUTLOOK:* (bukan analisa naratif).
    Terbaru dulu."""
    rows = conn.execute(
        "SELECT date, lens, notes, created_at FROM reading_workspace "
        "WHERE lens != 'SYNTHESIS' AND lens NOT LIKE 'OUTLOOK:%' "
        "ORDER BY date DESC, id ASC LIMIT ?", (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Panel 8: Universe & Grader (Phase J+ Build Contract v1.3 §19,
# J-14 Gelombang 1) — instrument_metadata + intake kandidat. Grader
# (emiten_grade/fund_score/quadrant) belum jalan (J-11), jadi kolom itu
# tampil "belum digrade" sampai modulnya dibangun -- bukan bug. ----------

INTAKE_ALLOWED_LANES = ("INVEST", "NONE")


def list_universe(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """instrument_metadata + grade TERBARU per instrumen (emiten_grade, kalau
    ada) -- Komponen A Tab 8. Correlated subquery (bukan window function)
    dipilih karena konsisten dgn gaya SQL project ini di tempat lain."""
    rows = conn.execute(
        "SELECT im.*, "
        "  (SELECT fund_score FROM emiten_grade eg WHERE eg.instrument = im.instrument "
        "     ORDER BY graded_at DESC, id DESC LIMIT 1) AS fund_score, "
        "  (SELECT quadrant FROM emiten_grade eg WHERE eg.instrument = im.instrument "
        "     ORDER BY graded_at DESC, id DESC LIMIT 1) AS quadrant, "
        "  (SELECT integrity_flags FROM emiten_grade eg WHERE eg.instrument = im.instrument "
        "     ORDER BY graded_at DESC, id DESC LIMIT 1) AS integrity_flags, "
        "  (SELECT graded_at FROM emiten_grade eg WHERE eg.instrument = im.instrument "
        "     ORDER BY graded_at DESC, id DESC LIMIT 1) AS graded_at "
        "FROM instrument_metadata im ORDER BY im.instrument"
    ).fetchall()
    return [dict(r) for r in rows]


def get_instrument_meta(conn: sqlite3.Connection, instrument: str) -> dict[str, Any] | None:
    """1 row instrument_metadata (buat badge LANE Panel 5). None kalau
    instrumen tidak ada di sana (aset makro/index BTC/GOLD/dll TIDAK punya
    row -- lane cuma berlaku utk saham individual Phase J+, badge disembunyikan)."""
    row = conn.execute(
        "SELECT * FROM instrument_metadata WHERE instrument = ?", (instrument.upper(),)
    ).fetchone()
    return dict(row) if row else None


# ---------- Lane validation (bar-replay sign-off) -- Phase J+ Build Contract
# v1.3 §13.1 poin 5 ("Engine teruji di BTC != teruji di BBRI, validasi per
# instrumen wajib sebelum lane naik ke TRADE"). Ini SATU-SATUNYA jalur yang
# boleh mengisi `lane_validated_at` / mengubah lane -- TIDAK PERNAH dipanggil
# otomatis oleh run_analysis/seed_universe/backfill manapun. Murni tindakan
# manual Giel lewat form Panel 8, setelah dia benar-benar mereview chart
# historis instrumen ybs sendiri (bukan diklaim/diasumsikan oleh kode). ----------

ALLOWED_LANES = ("TRADE", "INVEST", "BOTH", "NONE")


def validate_lane(
    conn: sqlite3.Connection, *, instrument: str, new_lane: str, evidence: str,
) -> dict[str, Any] | None:
    """Rekam hasil review bar-replay manual Giel. `evidence` WAJIB non-kosong
    (padanan `reason` di intake_log/save_grade_override) -- keputusan lane
    harus terdokumentasi kenapa, bukan sekadar toggle kosong. Return None
    kalau instrumen belum ada di instrument_metadata (harus lewat intake
    dulu, lihat save_intake_metadata)."""
    instrument = instrument.upper()
    new_lane = (new_lane or "").upper()
    if new_lane not in ALLOWED_LANES:
        raise ValueError(f"lane '{new_lane}' tidak dikenal -- pilihan: {'/'.join(ALLOWED_LANES)}")
    if not evidence or not evidence.strip():
        raise ValueError(
            "evidence wajib diisi (kontrak §13.1 poin 5 -- perubahan lane harus "
            "terdokumentasi kenapa, bukan toggle kosong)"
        )
    meta = get_instrument_meta(conn, instrument)
    if not meta:
        return None
    old_lane = meta["lane"]
    validated_at = today_wib()
    conn.execute(
        "UPDATE instrument_metadata SET lane = ?, lane_validated_at = ? WHERE instrument = ?",
        (new_lane, validated_at, instrument),
    )
    conn.execute(
        "INSERT INTO lane_validation_log (instrument, validated_at, old_lane, new_lane, evidence, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (instrument, validated_at, old_lane, new_lane, evidence.strip(), created_at()),
    )
    return {
        "instrument": instrument, "old_lane": old_lane, "new_lane": new_lane,
        "lane_validated_at": validated_at,
    }


def list_lane_validation_log(
    conn: sqlite3.Connection, instrument: str | None = None, limit: int = 200,
) -> list[dict[str, Any]]:
    """Riwayat validasi lane, terbaru dulu. Filter opsional per instrumen."""
    if instrument:
        rows = conn.execute(
            "SELECT * FROM lane_validation_log WHERE instrument = ? "
            "ORDER BY validated_at DESC, id DESC LIMIT ?",
            (instrument.upper(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM lane_validation_log ORDER BY validated_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_intake_metadata(
    conn: sqlite3.Connection, *, instrument: str, market: str, sector: str | None = None,
    asset_class: str = "equity", market_cap: float | None = None, free_float: float | None = None,
    lot_size: int | None = None, lane: str = "INVEST", is_financial: bool = False,
    has_daily_limit: bool = False, has_real_volume: bool = True,
    accounting_std: str | None = None, fx_exposure: str | None = None,
    data_as_of_rule: str | None = None,
) -> dict[str, Any]:
    """Komponen C Gelombang 1 (kontrak §19.3) -- intake kandidat baru ke
    `instrument_metadata`. Guard di LEVEL FUNGSI (bukan cuma UI): jalur intake
    HANYA boleh masuk lane INVEST/NONE, tidak pernah TRADE/BOTH langsung --
    instrumen baru wajib divalidasi bar-replay dulu (kontrak §13.1 poin 5,
    mirror assert `test_seed_universe.py::test_new_instrument_never_defaults_to_trade`).
    `lane_validated_at` SELALU NULL dari jalur ini. INSERT OR REPLACE by PK
    (instrument) -- idempotent, pola sama `pipeline/seed_universe.py`."""
    lane = (lane or "INVEST").upper()
    if lane not in INTAKE_ALLOWED_LANES:
        raise ValueError(
            f"lane '{lane}' tidak diizinkan dari jalur intake -- hanya "
            f"{'/'.join(INTAKE_ALLOWED_LANES)} (instrumen baru wajib divalidasi "
            "bar-replay dulu sebelum naik ke TRADE/BOTH, lihat kontrak §13.1 poin 5)"
        )
    row = {
        "instrument": instrument.upper(), "market": market.upper(), "asset_class": asset_class,
        "sector": sector, "market_cap": market_cap, "free_float": free_float,
        "avg_volume_20d": None, "lot_size": lot_size, "lane": lane, "lane_validated_at": None,
        "accounting_std": accounting_std, "is_financial": 1 if is_financial else 0,
        "fx_exposure": fx_exposure, "has_daily_limit": 1 if has_daily_limit else 0,
        "has_real_volume": 1 if has_real_volume else 0, "data_as_of_rule": data_as_of_rule,
        "created_at": created_at(),
    }
    cols = ", ".join(row)
    placeholders = ", ".join(f":{c}" for c in row)
    conn.execute(
        f"INSERT OR REPLACE INTO instrument_metadata ({cols}) VALUES ({placeholders})", row,
    )
    return row


# ---------- Panel 8 Komponen C Gelombang 2: Intake Kandidat penuh (Phase
# J+ Build Contract v1.3 §19.3/§16, J-12) — keputusan Giel atas kandidat
# (universe/watchlist/tolak) TERCATAT + alasan WAJIB, padanan
# prediction_log utk keputusan intake. Rubrik SAMA dgn universe existing
# (tidak ada jalur istimewa, §16) -- fungsi ini cuma CATAT keputusan,
# grade-nya sendiri dihitung run_grader() (J-11) yang sudah ada. ----------

INTAKE_DECISIONS = ("UNIVERSE", "WATCHLIST", "TOLAK")


def save_intake_decision(
    conn: sqlite3.Connection, *, instrument: str, decision: str, reason: str,
    grade_snapshot: dict[str, Any] | None = None,
) -> int:
    """Catat keputusan Giel atas kandidat intake. `reason` WAJIB non-kosong
    -- kandidat yang masuk karena hype/rekomendasi justru paling butuh
    alasan tertulis (kontrak §16: "grader adalah REM di momen tertarik,
    bukan stempel"), ditegakkan di level fungsi bukan cuma UI."""
    decision = (decision or "").upper()
    if decision not in INTAKE_DECISIONS:
        raise ValueError(
            f"decision '{decision}' tidak dikenal -- pilihan: {'/'.join(INTAKE_DECISIONS)}"
        )
    if not reason or not reason.strip():
        raise ValueError("reason wajib diisi (kontrak §16 -- tidak ada jalur istimewa tanpa alasan)")
    cur = conn.execute(
        "INSERT INTO intake_log (instrument, decided_at, decision, reason, grade_snapshot, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (instrument.upper(), today_wib(), decision, reason.strip(),
         json.dumps(grade_snapshot) if grade_snapshot else None, created_at()),
    )
    return cur.lastrowid


def list_intake_log(conn: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    """Riwayat keputusan intake, terbaru dulu."""
    rows = conn.execute(
        "SELECT * FROM intake_log ORDER BY decided_at DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Rasio prudential bank — CAR/NPL/NIM/LDR (Phase J+ §2 J7/J-6)
# MANUAL SAJA -- yfinance tidak punya field ini (dikonfirmasi saat
# prototipe G3), jadi Giel input sendiri dari laporan resmi bank (OJK/
# laporan tahunan). Kolom di `fundamentals_quarterly` yang sama (bukan
# tabel terpisah -- tetap "1 row per instrumen per kuartal"), TAPI lewat
# fungsi TERPISAH dari `upsert_fundamentals_quarterly` (backfill_
# fundamentals.py) supaya re-run scraper yfinance TIDAK PERNAH menimpa
# angka manual ini (upsert yfinance cuma SET kolom-kolom miliknya sendiri,
# tidak menyentuh car/npl_gross/nim/ldr sama sekali). ----------

def save_bank_ratios_manual(
    conn: sqlite3.Connection, *, instrument: str, quarter_end: str,
    car: float | None = None, npl_gross: float | None = None,
    nim: float | None = None, ldr: float | None = None,
) -> None:
    """UPSERT by (instrument, quarter_end). Kalau baris kuartal itu SUDAH
    ada (dari yfinance backfill_fundamentals), cuma 4 kolom ini yang
    ter-update -- revenue/net_income/dll TIDAK disentuh. Kalau belum ada,
    INSERT baris baru `source='manual'` (kuartal ini mungkin belum
    ke-backfill yfinance sama sekali)."""
    conn.execute(
        "INSERT INTO fundamentals_quarterly (instrument, quarter_end, car, npl_gross, "
        "nim, ldr, source, created_at) VALUES (?, ?, ?, ?, ?, ?, 'manual', ?) "
        "ON CONFLICT(instrument, quarter_end) DO UPDATE SET "
        "car=excluded.car, npl_gross=excluded.npl_gross, nim=excluded.nim, ldr=excluded.ldr",
        (instrument.upper(), quarter_end, car, npl_gross, nim, ldr, created_at()),
    )


def list_bank_ratios(conn: sqlite3.Connection, instrument: str, limit: int = 12) -> list[dict[str, Any]]:
    """Kuartal yang punya MINIMAL 1 rasio bank terisi, terbaru dulu."""
    rows = conn.execute(
        "SELECT quarter_end, car, npl_gross, nim, ldr, source FROM fundamentals_quarterly "
        "WHERE instrument = ? AND (car IS NOT NULL OR npl_gross IS NOT NULL "
        "OR nim IS NOT NULL OR ldr IS NOT NULL) ORDER BY quarter_end DESC LIMIT ?",
        (instrument.upper(), limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Panel 8 Komponen B — Detail Emiten (Addendum A §19.2, J-15) ----------

QUADRANTS = ("INVESTABLE", "WATCH", "SPECULATIVE", "AVOID")


def get_emiten_detail(conn: sqlite3.Connection, instrument: str) -> dict[str, Any] | None:
    """Gabungan instrument_metadata + histori fundamentals (8 kuartal
    terakhir) + grade TERBARU (integrity_flags & giel_override diurai dari
    JSON). None kalau instrumen tidak ada di instrument_metadata."""
    instrument = instrument.upper()
    meta = get_instrument_meta(conn, instrument)
    if not meta:
        return None
    fundamentals = [
        dict(r) for r in conn.execute(
            "SELECT * FROM fundamentals_quarterly WHERE instrument = ? "
            "ORDER BY quarter_end DESC LIMIT 8", (instrument,),
        ).fetchall()
    ]
    grade_row = conn.execute(
        "SELECT * FROM emiten_grade WHERE instrument = ? ORDER BY graded_at DESC, id DESC LIMIT 1",
        (instrument,),
    ).fetchone()
    grade = dict(grade_row) if grade_row else None
    if grade:
        grade["integrity_flags"] = json.loads(grade["integrity_flags"]) if grade["integrity_flags"] else []
        grade["giel_override"] = json.loads(grade["giel_override"]) if grade["giel_override"] else None
    return {"metadata": meta, "fundamentals": fundamentals, "grade": grade}


def save_grade_override(conn: sqlite3.Connection, instrument: str, quadrant: str, reason: str) -> bool:
    """Override kuadran MANUAL Giel atas grade terbaru. `reason` WAJIB
    non-kosong (kontrak §19.2: nilai mesin asli tetap terlihat, override
    ditandai terpisah, bukan menimpa). Return False kalau instrumen belum
    pernah digrade sama sekali (tidak ada baris utk di-override)."""
    quadrant = (quadrant or "").upper()
    if quadrant not in QUADRANTS:
        raise ValueError(f"quadrant '{quadrant}' tidak dikenal -- pilihan: {'/'.join(QUADRANTS)}")
    if not reason or not reason.strip():
        raise ValueError("reason wajib diisi utk override kuadran")
    instrument = instrument.upper()
    latest = conn.execute(
        "SELECT id FROM emiten_grade WHERE instrument = ? ORDER BY graded_at DESC, id DESC LIMIT 1",
        (instrument,),
    ).fetchone()
    if not latest:
        return False
    override = json.dumps({"quadrant": quadrant, "reason": reason.strip(), "overridden_at": today_wib()})
    conn.execute("UPDATE emiten_grade SET giel_override = ? WHERE id = ?", (override, latest["id"]))
    return True


# ---------- Panel 8 Komponen D — Grader Log & Kalibrasi (Addendum A §19.4, J-15) ----------

def list_grader_log(conn: sqlite3.Connection, instrument: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    """Riwayat perubahan kuadran, terbaru dulu. Filter opsional per instrumen."""
    if instrument:
        rows = conn.execute(
            "SELECT * FROM grader_log WHERE instrument = ? ORDER BY date DESC, id DESC LIMIT ?",
            (instrument.upper(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM grader_log ORDER BY date DESC, id DESC LIMIT ?", (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_grader_outcome(
    conn: sqlite3.Connection, log_id: int, *, outcome_3m: str | None = None,
    outcome_6m: str | None = None, notes: str | None = None,
) -> bool:
    """Widget 'Nilai Outcome' 3/6 bulan (pola sama score_prediction() Panel
    6). COALESCE supaya isi outcome_3m tidak menghapus outcome_6m yang
    sudah ada (dua widget independen, diisi di waktu berbeda). Return
    False kalau id tidak ada."""
    exists = conn.execute("SELECT 1 FROM grader_log WHERE id = ?", (log_id,)).fetchone()
    if not exists:
        return False
    conn.execute(
        "UPDATE grader_log SET outcome_3m = COALESCE(?, outcome_3m), "
        "outcome_6m = COALESCE(?, outcome_6m), outcome_notes = COALESCE(?, outcome_notes) "
        "WHERE id = ?",
        (outcome_3m, outcome_6m, notes, log_id),
    )
    return True


# ---------- News Threads (Addendum B §20, N-1 fondasi) ----------
# Unit penautan = THREAD, BUKAN artikel-ke-artikel (keputusan #2). Auto-suggest
# rule-based (BUKAN LLM, §20.0) TIDAK PERNAH langsung CONFIRMED -- selalu
# lewat Giel (human gate). Stance WAJIB saat CONFIRMED (anti-confirmation-
# funnel, keputusan #3). Maks 7 thread ACTIVE, ditegakkan di sini (bukan cuma
# UI, keputusan #5). N-2 (strip Reading, injeksi persona, auto-DORMANT)
# SENGAJA belum dibangun -- lihat docs/ROADMAP.md.

MAX_ACTIVE_THREADS = 7
ALLOWED_THREAD_STATUS = {"ACTIVE", "DORMANT", "CLOSED"}
ALLOWED_STANCE = {"MENDUKUNG", "KONTRA", "NETRAL"}
ALLOWED_REF_TABLES = {"daily_news", "manual_articles", "policy_tracker"}


def _decode_thread(row: dict[str, Any]) -> dict[str, Any]:
    row["keywords"] = json.loads(row["keywords"]) if row["keywords"] else []
    row["persona_tags"] = json.loads(row["persona_tags"]) if row["persona_tags"] else []
    return row


def save_thread(
    conn: sqlite3.Connection, *, title: str, description: str | None = None,
    keywords: list[str] | None = None, persona_tags: list[str] | None = None,
    current_read: str | None = None,
) -> dict[str, Any]:
    """Buat thread baru, status ACTIVE. Guard: title wajib, maks
    MAX_ACTIVE_THREADS thread ACTIVE bersamaan (keputusan #5) -- ditegakkan
    di sini, bukan cuma UI."""
    if not title or not title.strip():
        raise ValueError("title wajib diisi")
    active_count = conn.execute(
        "SELECT COUNT(*) c FROM news_threads WHERE status = 'ACTIVE'"
    ).fetchone()["c"]
    if active_count >= MAX_ACTIVE_THREADS:
        raise ValueError(
            f"sudah {MAX_ACTIVE_THREADS} thread ACTIVE -- tutup/dormant-kan satu dulu (keputusan #5)"
        )
    now = today_wib()
    row = {
        "title": title.strip(), "description": description, "current_read": current_read,
        "keywords": json.dumps(keywords or []), "persona_tags": json.dumps(persona_tags or []),
        "status": "ACTIVE", "verdict": None, "created_at": now, "updated_at": now,
    }
    cur = conn.execute(
        "INSERT INTO news_threads (title, description, keywords, current_read, persona_tags, "
        "status, verdict, created_at, updated_at) VALUES (:title, :description, :keywords, "
        ":current_read, :persona_tags, :status, :verdict, :created_at, :updated_at)",
        row,
    )
    return get_thread(conn, cur.lastrowid)


def patch_thread(conn: sqlite3.Connection, thread_id: int, **fields: Any) -> dict[str, Any] | None:
    """Update subset field thread (current_read/status/persona_tags/verdict).
    Guard: status='CLOSED' wajib verdict non-kosong (vonis auditable, §20.1).
    Return None kalau thread_id tidak ada."""
    current = get_thread(conn, thread_id)
    if current is None:
        return None
    if "status" in fields and fields["status"] not in ALLOWED_THREAD_STATUS:
        raise ValueError(
            f"status '{fields['status']}' tidak dikenal -- pilihan: {'/'.join(ALLOWED_THREAD_STATUS)}"
        )
    new_status = fields.get("status", current["status"])
    new_verdict = fields.get("verdict", current["verdict"])
    if new_status == "CLOSED" and not (new_verdict and new_verdict.strip()):
        raise ValueError("verdict wajib diisi saat menutup thread (status=CLOSED)")
    updates = dict(fields)
    if "persona_tags" in updates:
        updates["persona_tags"] = json.dumps(updates["persona_tags"])
    updates["updated_at"] = today_wib()
    cols = ", ".join(f"{k} = :{k}" for k in updates)
    conn.execute(f"UPDATE news_threads SET {cols} WHERE id = :id", {**updates, "id": thread_id})
    return get_thread(conn, thread_id)


def list_threads(conn: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    """Semua thread, terbaru diupdate dulu. Filter opsional by status."""
    sql = "SELECT * FROM news_threads"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status.upper())
    sql += " ORDER BY updated_at DESC, id DESC"
    return [_decode_thread(dict(r)) for r in conn.execute(sql, params).fetchall()]


def get_thread(conn: sqlite3.Connection, thread_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM news_threads WHERE id = ?", (thread_id,)).fetchone()
    return _decode_thread(dict(row)) if row else None


def suggest_thread_links(conn: sqlite3.Connection, news_items: list[dict[str, Any]]) -> int:
    """Untuk tiap headline BARU & tiap thread ACTIVE: keyword match (rule-
    based, `scrapers.base.keyword_matches`) -> INSERT news_thread_links
    SUGGESTED (idempoten via UNIQUE index idx_news_thread_links_dedup).
    Dipanggil pipeline/run_daily.py SETELAH insert_news_dedup() (butuh row id
    asli daily_news, bukan dict item mentah pre-insert) -- lookup by
    (date, headline), natural key sama dgn idx_daily_news_dedup. TIDAK PERNAH
    set CONFIRMED (human gate, §20.0). Return jumlah link baru."""
    if not news_items:
        return 0
    threads = conn.execute(
        "SELECT id, keywords FROM news_threads WHERE status = 'ACTIVE'"
    ).fetchall()
    thread_kw = [
        (t["id"], json.loads(t["keywords"]) if t["keywords"] else [])
        for t in threads
    ]
    thread_kw = [(tid, kws) for tid, kws in thread_kw if kws]
    if not thread_kw:
        return 0
    inserted = 0
    now = today_wib()
    for item in news_items:
        row = conn.execute(
            "SELECT id FROM daily_news WHERE date = ? AND headline = ?",
            (item["date"], item["headline"]),
        ).fetchone()
        if not row:
            continue
        headline_lower = (item["headline"] or "").lower()
        for thread_id, kws in thread_kw:
            if not keyword_matches(headline_lower, kws):
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO news_thread_links "
                "(thread_id, ref_table, ref_id, link_status, linked_at) "
                "VALUES (?, 'daily_news', ?, 'SUGGESTED', ?)",
                (thread_id, row["id"], now),
            )
            inserted += cur.rowcount
    return inserted


def confirm_thread_link(
    conn: sqlite3.Connection, link_id: int, stance: str, *, also_for_reading: bool = False,
) -> bool:
    """CONFIRM 1 link dgn stance (WAJIB, anti-confirmation-funnel keputusan
    #3). `also_for_reading=True` sekalian set daily_news.for_reading lewat
    set_for_reading() yang SUDAH ADA (reuse, bukan duplikat write path;
    param ini dulu bernama also_key_trigger sebelum Addendum C §21.2 rename).
    Return False kalau link_id tidak ada."""
    stance = (stance or "").upper()
    if stance not in ALLOWED_STANCE:
        raise ValueError(f"stance '{stance}' tidak dikenal -- pilihan: {'/'.join(ALLOWED_STANCE)}")
    link = conn.execute(
        "SELECT ref_table, ref_id FROM news_thread_links WHERE id = ?", (link_id,)
    ).fetchone()
    if not link:
        return False
    conn.execute(
        "UPDATE news_thread_links SET link_status = 'CONFIRMED', stance = ?, linked_at = ? WHERE id = ?",
        (stance, today_wib(), link_id),
    )
    if also_for_reading and link["ref_table"] == "daily_news":
        set_for_reading(conn, link["ref_id"], True)
    return True


def reject_thread_link(conn: sqlite3.Connection, link_id: int) -> bool:
    """Tolak 1 link SUGGESTED. Return False kalau link_id tidak ada."""
    exists = conn.execute("SELECT 1 FROM news_thread_links WHERE id = ?", (link_id,)).fetchone()
    if not exists:
        return False
    conn.execute("UPDATE news_thread_links SET link_status = 'REJECTED' WHERE id = ?", (link_id,))
    return True


def add_thread_link_manual(
    conn: sqlite3.Connection, thread_id: int, ref_table: str, ref_id: int,
    stance: str, note: str | None = None,
) -> dict[str, Any]:
    """Tautkan manual (utk sumber yang tak ter-auto-suggest, mis. entri
    policy_tracker atau manual_articles) -- langsung CONFIRMED (Giel sudah
    tahu stance-nya, tidak lewat SUGGESTED dulu). Guard: ref_table dikenal,
    stance wajib. Kalau pasangan (thread_id, ref_table, ref_id) sudah pernah
    ditautkan (mis. sudah SUGGESTED dari auto-suggest) -> ValueError, arahkan
    ke confirm_thread_link() pakai link_id yang sudah ada (jangan tautkan
    ulang)."""
    if ref_table not in ALLOWED_REF_TABLES:
        raise ValueError(f"ref_table '{ref_table}' tidak dikenal -- pilihan: {'/'.join(ALLOWED_REF_TABLES)}")
    stance = (stance or "").upper()
    if stance not in ALLOWED_STANCE:
        raise ValueError(f"stance '{stance}' tidak dikenal -- pilihan: {'/'.join(ALLOWED_STANCE)}")
    cur = conn.execute(
        "INSERT OR IGNORE INTO news_thread_links "
        "(thread_id, ref_table, ref_id, stance, link_status, note, linked_at) "
        "VALUES (?, ?, ?, ?, 'CONFIRMED', ?, ?)",
        (thread_id, ref_table, ref_id, stance, note, today_wib()),
    )
    if cur.rowcount == 0:
        raise ValueError(
            "link ini sudah ada (thread+sumber ini sudah pernah ditautkan) -- "
            "konfirmasi/tolak yang sudah ada lewat link_id, jangan tautkan ulang"
        )
    return {
        "id": cur.lastrowid, "thread_id": thread_id, "ref_table": ref_table, "ref_id": ref_id,
        "stance": stance, "link_status": "CONFIRMED", "note": note,
    }


def list_thread_links(
    conn: sqlite3.Connection, thread_id: int, status: str | None = None,
) -> list[dict[str, Any]]:
    """Link 1 thread + info sumber asli (date/source/headline/url), di-JOIN
    manual per ref_table (union Python-side -- lebih aman drpd dynamic-
    table-name SQL). Dipakai halaman timeline thread (§20.5)."""
    sql = (
        "SELECT id, ref_table, ref_id, stance, link_status, note, linked_at "
        "FROM news_thread_links WHERE thread_id = ?"
    )
    params: list[Any] = [thread_id]
    if status:
        sql += " AND link_status = ?"
        params.append(status.upper())
    sql += " ORDER BY linked_at ASC, id ASC"
    links = [dict(r) for r in conn.execute(sql, params).fetchall()]

    by_table: dict[str, list[int]] = {}
    for link in links:
        by_table.setdefault(link["ref_table"], []).append(link["ref_id"])

    source_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    if by_table.get("daily_news"):
        ids = by_table["daily_news"]
        placeholders = ",".join("?" for _ in ids)
        for r in conn.execute(
            f"SELECT id, date, source, headline, raw_url FROM daily_news WHERE id IN ({placeholders})", ids,
        ):
            source_by_key[("daily_news", r["id"])] = {
                "date": r["date"], "source": r["source"], "headline": r["headline"], "url": r["raw_url"],
            }
    if by_table.get("manual_articles"):
        ids = by_table["manual_articles"]
        placeholders = ",".join("?" for _ in ids)
        for r in conn.execute(
            f"SELECT id, date, source, headline, url FROM manual_articles WHERE id IN ({placeholders})", ids,
        ):
            source_by_key[("manual_articles", r["id"])] = {
                "date": r["date"], "source": r["source"], "headline": r["headline"], "url": r["url"],
            }
    if by_table.get("policy_tracker"):
        ids = by_table["policy_tracker"]
        placeholders = ",".join("?" for _ in ids)
        for r in conn.execute(
            f"SELECT id, date, speaker, institution, literal_statement, source_url "
            f"FROM policy_tracker WHERE id IN ({placeholders})", ids,
        ):
            source_by_key[("policy_tracker", r["id"])] = {
                "date": r["date"], "source": f"{r['speaker'] or ''} ({r['institution'] or ''})".strip(),
                "headline": r["literal_statement"], "url": r["source_url"],
            }

    for link in links:
        link["source_info"] = source_by_key.get((link["ref_table"], link["ref_id"]))
    return links


def attach_thread_suggestions(conn: sqlite3.Connection, news_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tempel info news_thread_links (SUGGESTED/CONFIRMED, REJECTED
    diabaikan) ke tiap row daily_news yang SUDAH di-fetch -- dipakai
    GET /api/news biar NewsView bisa render chip 'Saran: <thread>?' tanpa
    endpoint terpisah. Kalau 1 headline match >1 thread, CONFIRMED menang
    atas SUGGESTED (ORDER BY di query), sisanya diabaikan -- UI cuma
    nampilkan 1 chip per berita di N-1."""
    if not news_rows:
        return news_rows
    ids = [r["id"] for r in news_rows]
    placeholders = ",".join("?" for _ in ids)
    links = conn.execute(
        f"SELECT l.id AS link_id, l.ref_id, l.thread_id, l.stance, l.link_status, "
        f"t.title AS thread_title FROM news_thread_links l "
        f"JOIN news_threads t ON t.id = l.thread_id "
        f"WHERE l.ref_table = 'daily_news' AND l.ref_id IN ({placeholders}) "
        f"AND l.link_status != 'REJECTED' "
        f"ORDER BY l.ref_id, CASE l.link_status WHEN 'CONFIRMED' THEN 0 ELSE 1 END, l.id",
        ids,
    ).fetchall()
    by_ref: dict[int, dict[str, Any]] = {}
    for r in links:
        by_ref.setdefault(r["ref_id"], dict(r))
    for row in news_rows:
        link = by_ref.get(row["id"])
        row["thread_link"] = {
            "link_id": link["link_id"], "thread_id": link["thread_id"],
            "thread_title": link["thread_title"], "stance": link["stance"],
            "link_status": link["link_status"],
        } if link else None
    return news_rows


# ---------- Faceted Tagging (Addendum C §21, GELOMBANG C-1 fondasi) ----------
# Tag menjawab "berita ini TENTANG apa" (klasifikasi, objektif, controlled
# vocabulary) -- BEDA pertanyaan dari for_reading (kurasi, subjektif, di atas).
# Rule-based di sini pun murni validasi tata bahasa, BUKAN LLM (konsisten
# filosofi impact scoring §21.0). C-2 (auto-suggest tag, feed manual ke
# persona, tag-based thread matching) SENGAJA belum dibangun -- lihat
# docs/ROADMAP.md.

ALLOWED_FACETS = {"geo", "org", "who", "sym", "theme", "sec"}
ALLOWED_CONTENT_TAG_REF_TABLES = {"daily_news", "manual_articles", "news_threads"}
_TAG_VALUE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _validate_tag_grammar(canonical: str) -> str:
    """Tata bahasa tag (§21.1): "facet:value", facet dari ALLOWED_FACETS,
    value lowercase+hyphen (tanpa spasi/karakter lain), `sym:` WAJIB
    region-prefix (mis. "id-bbca" -- dideteksi lewat keberadaan hyphen,
    membedakan dari ticker polos tanpa region spt "bbca"). Return facet
    (dipakai caller, single source of truth -- bukan param terpisah yang
    bisa mismatch dgn canonical). Raise ValueError kalau melanggar."""
    canonical = (canonical or "").strip()
    if ":" not in canonical:
        raise ValueError(f"tag '{canonical}' harus format facet:value (mis. 'who:warsh')")
    facet, _, value = canonical.partition(":")
    if facet not in ALLOWED_FACETS:
        raise ValueError(f"facet '{facet}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_FACETS))}")
    if not value or not _TAG_VALUE_RE.match(value):
        raise ValueError(
            f"value tag '{value}' tidak valid -- lowercase, hyphen (bukan spasi), "
            "tanpa karakter lain (mis. 'rate-policy', bukan 'Rate Policy'/'rate_policy')"
        )
    if facet == "sym" and "-" not in value:
        raise ValueError(
            f"sym:{value} wajib region-prefix (mis. 'sym:id-bbca'/'sym:us-tsla'), "
            "bukan ticker polos tanpa region"
        )
    return facet


def _decode_tag(row: dict[str, Any]) -> dict[str, Any]:
    row["aliases"] = json.loads(row["aliases"]) if row["aliases"] else []
    return row


def create_tag(
    conn: sqlite3.Connection, canonical: str, aliases: list[str] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Tambah tag baru ke kamus. Facet DIDERIVE dari canonical (bukan param
    terpisah) -- satu-satunya pintu nambah kamus (§21.3 "+ buat tag baru").
    Guard: tata bahasa (lihat _validate_tag_grammar) + UNIQUE canonical."""
    canonical = canonical.strip().lower()
    facet = _validate_tag_grammar(canonical)
    now = today_wib()
    cur = conn.execute(
        "INSERT OR IGNORE INTO tag_dictionary "
        "(canonical, facet, aliases, description, usage_count, created_at) "
        "VALUES (?, ?, ?, ?, 0, ?)",
        (canonical, facet, json.dumps(aliases or []), description, now),
    )
    if cur.rowcount == 0:
        raise ValueError(f"tag '{canonical}' sudah ada di kamus")
    return _decode_tag(dict(conn.execute(
        "SELECT * FROM tag_dictionary WHERE id = ?", (cur.lastrowid,)
    ).fetchone()))


def list_tags(conn: sqlite3.Connection, facet: str | None = None) -> list[dict[str, Any]]:
    """Semua tag di kamus, terpakai dulu. Filter opsional by facet."""
    sql = "SELECT * FROM tag_dictionary"
    params: list[Any] = []
    if facet:
        sql += " WHERE facet = ?"
        params.append(facet)
    sql += " ORDER BY usage_count DESC, canonical ASC"
    return [_decode_tag(dict(r)) for r in conn.execute(sql, params).fetchall()]


def resolve_tag(conn: sqlite3.Connection, name_or_alias: str) -> dict[str, Any] | None:
    """Cari tag by canonical EXACT match, atau by alias (JSON array
    containment). Vocab kecil di awal -- Python-side loop cukup, tidak perlu
    index alias terpisah."""
    name_or_alias = (name_or_alias or "").strip().lower()
    row = conn.execute(
        "SELECT * FROM tag_dictionary WHERE canonical = ?", (name_or_alias,)
    ).fetchone()
    if row:
        return _decode_tag(dict(row))
    for r in conn.execute("SELECT * FROM tag_dictionary").fetchall():
        aliases = json.loads(r["aliases"]) if r["aliases"] else []
        if name_or_alias in aliases:
            return _decode_tag(dict(r))
    return None


def apply_tag(
    conn: sqlite3.Connection, ref_table: str, ref_id: int, tag_name: str, source: str = "MANUAL",
) -> dict[str, Any]:
    """Pasang 1 tag ke 1 konten (berita/artikel/thread). Guard: ref_table
    dikenal, tag harus SUDAH ada di kamus (resolve_tag -- "buat dulu" alur
    §21.3), dedup (INSERT OR IGNORE + rowcount check, pola
    add_thread_link_manual). Naikkan usage_count (dipakai review kuartalan
    §21.7)."""
    if ref_table not in ALLOWED_CONTENT_TAG_REF_TABLES:
        raise ValueError(
            f"ref_table '{ref_table}' tidak dikenal -- pilihan: "
            f"{'/'.join(sorted(ALLOWED_CONTENT_TAG_REF_TABLES))}"
        )
    tag = resolve_tag(conn, tag_name)
    if tag is None:
        raise ValueError(f"tag '{tag_name}' tidak ditemukan di kamus -- buat dulu")
    now = today_wib()
    cur = conn.execute(
        "INSERT OR IGNORE INTO content_tags (ref_table, ref_id, tag_id, source, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (ref_table, ref_id, tag["id"], source, now),
    )
    if cur.rowcount == 0:
        raise ValueError(f"tag '{tag['canonical']}' sudah terpasang di konten ini")
    conn.execute(
        "UPDATE tag_dictionary SET usage_count = usage_count + 1 WHERE id = ?", (tag["id"],)
    )
    return {
        "id": cur.lastrowid, "ref_table": ref_table, "ref_id": ref_id,
        "tag_id": tag["id"], "canonical": tag["canonical"], "facet": tag["facet"], "source": source,
    }


def remove_tag(conn: sqlite3.Connection, content_tag_id: int) -> bool:
    """Lepas 1 tag dari 1 konten by content_tags.id (bukan usage_count
    dikurangi -- histori pemakaian tetap dihitung naik, konsisten dgn
    grader_log/prediction_log yang juga append-only utk audit trail)."""
    exists = conn.execute("SELECT 1 FROM content_tags WHERE id = ?", (content_tag_id,)).fetchone()
    if not exists:
        return False
    conn.execute("DELETE FROM content_tags WHERE id = ?", (content_tag_id,))
    return True


def list_content_tags(conn: sqlite3.Connection, ref_table: str, ref_id: int) -> list[dict[str, Any]]:
    """Semua tag terpasang di 1 konten spesifik (dipakai halaman detail)."""
    rows = conn.execute(
        "SELECT c.id, c.tag_id, c.source, c.created_at, t.canonical, t.facet "
        "FROM content_tags c JOIN tag_dictionary t ON t.id = c.tag_id "
        "WHERE c.ref_table = ? AND c.ref_id = ? ORDER BY t.facet, t.canonical",
        (ref_table, ref_id),
    ).fetchall()
    return [dict(r) for r in rows]


def attach_content_tags(conn: sqlite3.Connection, ref_table: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tempel tag ke SEKUMPULAN row sekaligus (mis. daftar berita) -- 1 query
    batch, bukan N+1. Mirrors attach_thread_suggestions()'s shape. Set
    row["tags"] = [{id, canonical, facet}, ...] per row -- `id` (content_tags
    PK, BUKAN tag_id) disertakan supaya UI bisa panggil remove_tag() langsung
    tanpa query tambahan."""
    if not rows:
        return rows
    ids = [r["id"] for r in rows]
    placeholders = ",".join("?" for _ in ids)
    tagged = conn.execute(
        f"SELECT c.id, c.ref_id, t.canonical, t.facet FROM content_tags c "
        f"JOIN tag_dictionary t ON t.id = c.tag_id "
        f"WHERE c.ref_table = ? AND c.ref_id IN ({placeholders}) "
        f"ORDER BY c.ref_id, t.facet, t.canonical",
        [ref_table, *ids],
    ).fetchall()
    by_ref: dict[int, list[dict[str, Any]]] = {}
    for r in tagged:
        by_ref.setdefault(r["ref_id"], []).append(
            {"id": r["id"], "canonical": r["canonical"], "facet": r["facet"]}
        )
    for row in rows:
        row["tags"] = by_ref.get(row["id"], [])
    return rows
