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
# funnel, keputusan #3). N-2 (strip Reading, injeksi persona, auto-DORMANT)
# SENGAJA belum dibangun -- lihat docs/ROADMAP.md.
#
# Keputusan #5 (maks 7 thread ACTIVE) DICABUT 28 Jul 2026 -- Giel eksplisit
# minta batasan dihapus, dia sendiri yang tentukan berapa banyak & mana yang
# ACTIVE/DORMANT (lewat status field yang sudah ada, bukan sistem yang
# memblokir). Lihat docs/ROADMAP.md & docs/phase_j_build_contract_v1_3_LOCKED.md
# §20 utk catatan override.

ALLOWED_THREAD_STATUS = {"ACTIVE", "DORMANT", "CLOSED"}
ALLOWED_STANCE = {"MENDUKUNG", "KONTRA", "NETRAL"}
ALLOWED_REF_TABLES = {"daily_news", "manual_articles", "policy_tracker"}
# Ketemu 17 Jul 2026: thread baru mulai KOSONG krn suggest_thread_links()
# cuma dipanggil run_daily dgn headline yg BARU DI-FETCH hari itu -- tidak
# pernah scan ulang histori daily_news yang sudah ada. Thread yang dibuat
# siang hari ketinggalan semua berita pagi. save_thread() sekarang jalankan
# catch-up SEKALI saat dibuat (scan N hari ke belakang), biar tidak nunggu
# cron besok buat suggestion pertama muncul.
THREAD_CATCHUP_DAYS = 7
# Auto-DORMANT (Addendum C §21.8 C-2, 17 Jul 2026) -- thread ACTIVE yang tidak
# di-update (patch_thread/link baru) selama STALE_THREAD_DAYS otomatis turun
# ke DORMANT saat run_daily. Bukan hapus/CLOSED -- DORMANT tetap bisa
# diaktifkan lagi manual, cuma tidak lagi ikut hitungan 7/ACTIVE & auto-suggest.
STALE_THREAD_DAYS = 30


def _decode_thread(row: dict[str, Any]) -> dict[str, Any]:
    row["keywords"] = json.loads(row["keywords"]) if row["keywords"] else []
    row["persona_tags"] = json.loads(row["persona_tags"]) if row["persona_tags"] else []
    return row


def save_thread(
    conn: sqlite3.Connection, *, title: str, description: str | None = None,
    keywords: list[str] | None = None, persona_tags: list[str] | None = None,
    current_read: str | None = None,
) -> dict[str, Any]:
    """Buat thread baru, status ACTIVE. Guard: title wajib. Tidak ada batas
    jumlah thread ACTIVE (keputusan #5 dicabut 28 Jul 2026) -- Giel sendiri
    yang tentukan lewat status field (patch_thread). Kalau ada keywords,
    langsung catch-up scan THREAD_CATCHUP_DAYS hari ke belakang (lihat
    catatan di atas) -- thread tidak mulai dari nol kalau beritanya sudah
    ada di DB sebelum thread dibuat."""
    if not title or not title.strip():
        raise ValueError("title wajib diisi")
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
    if keywords:
        recent_news = conn.execute(
            "SELECT date, headline FROM daily_news WHERE date >= date(?, ?)",
            (now, f"-{THREAD_CATCHUP_DAYS} day"),
        ).fetchall()
        suggest_thread_links(conn, [dict(r) for r in recent_news])
    return get_thread(conn, cur.lastrowid)


def patch_thread(conn: sqlite3.Connection, thread_id: int, **fields: Any) -> dict[str, Any] | None:
    """Update subset field thread (title/current_read/status/keywords/
    persona_tags/verdict). Guard: status='CLOSED' wajib verdict non-kosong
    (vonis auditable, §20.1), title (kalau diubah) wajib non-kosong. Kalau
    keywords diubah, catch-up scan ulang (pola sama save_thread -- kata
    kunci baru mungkin cocok berita yang sudah ada di DB). Return None kalau
    thread_id tidak ada."""
    current = get_thread(conn, thread_id)
    if current is None:
        return None
    if "status" in fields and fields["status"] not in ALLOWED_THREAD_STATUS:
        raise ValueError(
            f"status '{fields['status']}' tidak dikenal -- pilihan: {'/'.join(ALLOWED_THREAD_STATUS)}"
        )
    if "title" in fields and not (fields["title"] and fields["title"].strip()):
        raise ValueError("title wajib diisi")
    new_status = fields.get("status", current["status"])
    new_verdict = fields.get("verdict", current["verdict"])
    if new_status == "CLOSED" and not (new_verdict and new_verdict.strip()):
        raise ValueError("verdict wajib diisi saat menutup thread (status=CLOSED)")
    updates = dict(fields)
    if "title" in updates:
        updates["title"] = updates["title"].strip()
    if "persona_tags" in updates:
        updates["persona_tags"] = json.dumps(updates["persona_tags"])
    if "keywords" in updates:
        new_keywords = updates["keywords"]
        updates["keywords"] = json.dumps(new_keywords)
    updates["updated_at"] = today_wib()
    cols = ", ".join(f"{k} = :{k}" for k in updates)
    conn.execute(f"UPDATE news_threads SET {cols} WHERE id = :id", {**updates, "id": thread_id})
    if "keywords" in fields and fields["keywords"] and new_status == "ACTIVE":
        recent_news = conn.execute(
            "SELECT date, headline FROM daily_news WHERE date >= date(?, ?)",
            (today_wib(), f"-{THREAD_CATCHUP_DAYS} day"),
        ).fetchall()
        suggest_thread_links(conn, [dict(r) for r in recent_news])
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


def suggest_thread_links(
    conn: sqlite3.Connection, news_items: list[dict[str, Any]], *, is_backfill: bool = False,
) -> int:
    """Untuk tiap headline BARU & tiap thread ACTIVE, DUA jalur match (§21.5
    -- tag-match TAMBAHAN, keyword TIDAK dihapus, jadi "legacy/fallback"
    persis kata kontrak, bukan diganti):
    1) keyword match (rule-based, `scrapers.base.keyword_matches`) terhadap
       `news_threads.keywords`.
    2) tag-overlap: kalau berita & thread SAMA-SAMA punya >=1 facet tag yang
       sama (`content_tags`, thread pakai ref_table='news_threads') -> match.
       Thread tanpa facet tag otomatis fallback ke keyword-only (union kosong
       tidak pernah match, tidak butuh cabang if terpisah).
    Kedua jalur INSERT ke news_thread_links SUGGESTED yang sama (idempoten
    via UNIQUE index idx_news_thread_links_dedup -- overlap keyword+tag pada
    pasangan sama tidak dobel). Dipanggil pipeline/run_daily.py SETELAH
    insert_news_dedup() (butuh row id asli daily_news) DAN SETELAH
    suggest_tags_for_news() (biar tag-match lihat tag yang baru disarankan di
    run yang sama) -- lookup row by (date, headline), natural key sama dgn
    idx_daily_news_dedup. TIDAK PERNAH set CONFIRMED (human gate, §20.0).
    `is_backfill` (F-2 §24.4, default False) -- True HANYA saat dipanggil
    dari tools/backfill_tag.py, dicatat di kolom is_backfill dipakai filter
    UI (link lahir dari backfill vs pipeline harian biasa). Return jumlah
    link baru."""
    if not news_items:
        return 0
    threads = conn.execute(
        "SELECT id, keywords FROM news_threads WHERE status = 'ACTIVE'"
    ).fetchall()
    if not threads:
        return 0
    thread_kw = {
        t["id"]: (json.loads(t["keywords"]) if t["keywords"] else []) for t in threads
    }
    thread_tag_rows = conn.execute(
        "SELECT ref_id AS thread_id, tag_id FROM content_tags WHERE ref_table = 'news_threads'"
    ).fetchall()
    thread_tags: dict[int, set[int]] = {}
    for r in thread_tag_rows:
        thread_tags.setdefault(r["thread_id"], set()).add(r["tag_id"])
    active_ids = set(thread_kw)
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
        news_tag_ids = {
            r["tag_id"] for r in conn.execute(
                "SELECT tag_id FROM content_tags WHERE ref_table = 'daily_news' AND ref_id = ?",
                (row["id"],),
            ).fetchall()
        }
        for thread_id in active_ids:
            matched = keyword_matches(headline_lower, thread_kw[thread_id]) or bool(
                news_tag_ids & thread_tags.get(thread_id, set())
            )
            if not matched:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO news_thread_links "
                "(thread_id, ref_table, ref_id, link_status, linked_at, is_backfill) "
                "VALUES (?, 'daily_news', ?, 'SUGGESTED', ?, ?)",
                (thread_id, row["id"], now, int(is_backfill)),
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


def set_link_milestone(conn: sqlite3.Connection, link_id: int, is_milestone: bool) -> bool:
    """Toggle milestone 1 link CONFIRMED (F-2 §24.4, Lapis 2) -- SELALU
    manual (Giel yang menilai tautan mana yang mengubah arah narasi),
    TIDAK PERNAH otomatis. Boleh dipasang/dilepas di link mana pun (tidak
    dibatasi cuma CONFIRMED di level guard -- toggle salah pilih gampang
    dibalik, tidak perlu blokir keras). Return False kalau link_id tidak
    ada."""
    exists = conn.execute("SELECT 1 FROM news_thread_links WHERE id = ?", (link_id,)).fetchone()
    if not exists:
        return False
    conn.execute(
        "UPDATE news_thread_links SET is_milestone = ? WHERE id = ?",
        (int(bool(is_milestone)), link_id),
    )
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
    table-name SQL). Dipakai halaman timeline thread (§20.5). F-2 (§24.4)
    tambah `is_milestone`/`is_backfill` (dipakai toggle & filter) + `tags`
    (facet tag berita asal, HANYA utk daily_news/manual_articles --
    policy_tracker memang tidak masuk ALLOWED_CONTENT_TAG_REF_TABLES,
    jujur tampil array kosong bukan error)."""
    sql = (
        "SELECT id, ref_table, ref_id, stance, link_status, note, linked_at, "
        "is_milestone, is_backfill FROM news_thread_links WHERE thread_id = ?"
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

    tags_by_key: dict[tuple[str, int], list[str]] = {}
    for taggable in ("daily_news", "manual_articles"):
        ids = by_table.get(taggable)
        if not ids:
            continue
        placeholders = ",".join("?" for _ in ids)
        for r in conn.execute(
            f"SELECT c.ref_id, t.canonical FROM content_tags c "
            f"JOIN tag_dictionary t ON t.id = c.tag_id "
            f"WHERE c.ref_table = ? AND c.ref_id IN ({placeholders})",
            [taggable, *ids],
        ):
            tags_by_key.setdefault((taggable, r["ref_id"]), []).append(r["canonical"])

    for link in links:
        link["source_info"] = source_by_key.get((link["ref_table"], link["ref_id"]))
        link["is_milestone"] = bool(link["is_milestone"])
        link["is_backfill"] = bool(link["is_backfill"])
        link["tags"] = tags_by_key.get((link["ref_table"], link["ref_id"]), [])
    return links


def merge_thread(conn: sqlite3.Connection, from_id: int, into_id: int) -> dict[str, Any]:
    """Gabung 2 thread yang ternyata narasi sama/tumpang tindih (ketemu 24
    Jul 2026 -- kandidat seed §21.12 vs thread real punya topik sama, mis.
    "Rezim Warsh Hawkish" (seed, cuma punya facet tags) vs "Rezim Warsh
    Dovish" (real, punya link+riwayat). Giel eksplisit: JANGAN cuma
    close/dormant-kan salah satu (itu DIAM-DIAM buang datanya) -- gabung
    beneran, `from_id` hilang, semua `news_thread_links` DAN `content_tags`
    (facet tags thread, ref_table='news_threads') milik `from_id` pindah ke
    `into_id`. `keywords`/`persona_tags` di-UNION (bukan ditimpa) supaya
    auto-suggest tetap jalan dari kedua sisi. `title`/`description`/
    `current_read`/`status`/`verdict` milik `into_id` TIDAK disentuh --
    dua thread bisa punya `current_read` yang malah BERLAWANAN (persis
    kasus Warsh Hawkish vs Dovish), auto-gabung teks editorial itu akan
    menyuntik bias tanpa sepengetahuan Giel; caller tampilkan `from`'s
    current_read di response biar Giel bisa copy-paste manual kalau perlu.
    Return thread `into_id` setelah digabung (decoded)."""
    if from_id == into_id:
        raise ValueError("tidak bisa merge thread ke dirinya sendiri")
    src = get_thread(conn, from_id)
    dst = get_thread(conn, into_id)
    if src is None or dst is None:
        raise ValueError("thread from_id/into_id tidak ditemukan")

    # 1) news_thread_links -- re-point, dedup-aware (UNIQUE(thread_id,
    # ref_table, ref_id) idx_news_thread_links_dedup). Kalau tabrakan
    # (pasangan ref_table+ref_id yang sama sudah tertaut ke into_id juga),
    # punya into_id yang menang -- baris from_id yang jadi redundan dihapus.
    from_links = conn.execute(
        "SELECT ref_table, ref_id, stance, link_status, note, linked_at, is_milestone, is_backfill "
        "FROM news_thread_links WHERE thread_id = ?", (from_id,),
    ).fetchall()
    for r in from_links:
        conn.execute(
            "INSERT OR IGNORE INTO news_thread_links "
            "(thread_id, ref_table, ref_id, stance, link_status, note, linked_at, is_milestone, is_backfill) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (into_id, r["ref_table"], r["ref_id"], r["stance"], r["link_status"], r["note"], r["linked_at"],
             r["is_milestone"], r["is_backfill"]),
        )
    conn.execute("DELETE FROM news_thread_links WHERE thread_id = ?", (from_id,))

    # 2) content_tags (facet tags thread sendiri, ref_table='news_threads')
    # -- pola sama merge_tag(): INSERT OR IGNORE dulu (idx_content_tags_dedup),
    # baris from_id yang jadi redundan dihapus setelahnya.
    from_tags = conn.execute(
        "SELECT tag_id, source, created_at FROM content_tags "
        "WHERE ref_table = 'news_threads' AND ref_id = ?", (from_id,),
    ).fetchall()
    for r in from_tags:
        conn.execute(
            "INSERT OR IGNORE INTO content_tags (ref_table, ref_id, tag_id, source, created_at) "
            "VALUES ('news_threads', ?, ?, ?, ?)",
            (into_id, r["tag_id"], r["source"], r["created_at"]),
        )
    conn.execute("DELETE FROM content_tags WHERE ref_table = 'news_threads' AND ref_id = ?", (from_id,))

    # 3) keywords/persona_tags -- UNION, bukan ditimpa (auto-suggest tetap
    # jalan dari kata kunci KEDUA thread, bukan cuma salah satu).
    merged_keywords = list(dict.fromkeys([*dst["keywords"], *src["keywords"]]))
    merged_persona_tags = list(dict.fromkeys([*dst["persona_tags"], *src["persona_tags"]]))
    conn.execute(
        "UPDATE news_threads SET keywords = ?, persona_tags = ?, updated_at = ? WHERE id = ?",
        (json.dumps(merged_keywords), json.dumps(merged_persona_tags), today_wib(), into_id),
    )

    conn.execute("DELETE FROM news_threads WHERE id = ?", (from_id,))
    merged = get_thread(conn, into_id)
    merged["merged_from_current_read"] = src["current_read"]
    return merged


def attach_thread_suggestions(conn: sqlite3.Connection, news_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tempel SEMUA news_thread_links non-REJECTED ke tiap row daily_news yang
    SUDAH di-fetch -- dipakai GET /api/news biar NewsView bisa render chip
    'Saran: <thread>?' tanpa endpoint terpisah. Ketemu 17 Jul 2026: dulu cuma
    1 link 'pemenang' per berita (CONFIRMED > SUGGESTED) ditempel -- Giel
    tidak bisa lihat/ubah/lepas thread lain yang juga match berita yang sama.
    Sekarang tempel array `thread_links` (semua link non-REJECTED, CONFIRMED
    duluan), UI yang render banyak chip sekaligus."""
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
    by_ref: dict[int, list[dict[str, Any]]] = {}
    for r in links:
        by_ref.setdefault(r["ref_id"], []).append(dict(r))
    for row in news_rows:
        row["thread_links"] = [
            {
                "link_id": link["link_id"], "thread_id": link["thread_id"],
                "thread_title": link["thread_title"], "stance": link["stance"],
                "link_status": link["link_status"],
            }
            for link in by_ref.get(row["id"], [])
        ]
    return news_rows


# ---------- Faceted Tagging (Addendum C §21, GELOMBANG C-1 fondasi) ----------
# Tag menjawab "berita ini TENTANG apa" (klasifikasi, objektif, controlled
# vocabulary) -- BEDA pertanyaan dari for_reading (kurasi, subjektif, di atas).
# Rule-based di sini pun murni validasi tata bahasa, BUKAN LLM (konsisten
# filosofi impact scoring §21.0). C-2 (auto-suggest tag, feed manual ke
# persona, tag-based thread matching) SENGAJA belum dibangun -- lihat
# docs/ROADMAP.md.

ALLOWED_FACETS = {"geo", "org", "who", "sym", "theme", "sec"}
ALLOWED_CONTENT_TAG_REF_TABLES = {"daily_news", "manual_articles", "news_threads", "secondary_opinions"}
_TAG_VALUE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Simbol global/makro yang TIDAK ambigu lintas market (tidak butuh region-
# prefix) -- ketemu 17 Jul 2026 saat seed_tags.py jalan: kontrak §21.1 sendiri
# mencontohkan "sym:btc"/"sym:xau" TANPA prefix di daftar vocabulary-nya,
# padahal kalimat aturan di baris yang sama bilang "wajib region-prefix" --
# kontradiksi kecil di teks kontrak. Resolusi: WAJIB region-prefix cuma utk
# TICKER SAHAM (ambigu antar-bursa, itu tujuan asli aturan -- "BBCA" bisa
# banyak arti), simbol makro/indeks/kripto global di allowlist ini dikecualikan.
_GLOBAL_SYM_EXEMPT = {"btc", "eth", "xau", "dxy", "us10y", "vix", "sp500", "idx"}


def _validate_tag_grammar(canonical: str) -> str:
    """Tata bahasa tag (§21.1): "facet:value", facet dari ALLOWED_FACETS,
    value lowercase+hyphen (tanpa spasi/karakter lain), `sym:` WAJIB
    region-prefix KECUALI simbol global/makro di `_GLOBAL_SYM_EXEMPT` (mis.
    "id-bbca" -- dideteksi lewat keberadaan hyphen, membedakan dari ticker
    polos tanpa region spt "bbca"; tapi "sym:btc"/"sym:dxy"/dst TIDAK butuh
    prefix, tidak ambigu lintas market). Return facet (dipakai caller, single
    source of truth -- bukan param terpisah yang bisa mismatch dgn canonical).
    Raise ValueError kalau melanggar."""
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
    if facet == "sym" and "-" not in value and value not in _GLOBAL_SYM_EXEMPT:
        raise ValueError(
            f"sym:{value} wajib region-prefix (mis. 'sym:id-bbca'/'sym:us-tsla'), "
            "bukan ticker polos tanpa region -- kecuali simbol global/makro "
            f"({'/'.join(sorted(_GLOBAL_SYM_EXEMPT))})"
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


def confirm_tag(conn: sqlite3.Connection, content_tag_id: int) -> bool:
    """Terima 1 tag SUGGESTED jadi MANUAL (checkbox "ceklis" di NewsView) --
    tag auto-suggest sudah terpasang di content_tags sejak insert, ini cuma
    ubah source supaya UI berhenti tandai '?'/dashed. Idempoten: no-op kalau
    sudah MANUAL, tetap return True selama baris ada."""
    exists = conn.execute("SELECT 1 FROM content_tags WHERE id = ?", (content_tag_id,)).fetchone()
    if not exists:
        return False
    conn.execute("UPDATE content_tags SET source = 'MANUAL' WHERE id = ?", (content_tag_id,))
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
    row["tags"] = [{id, canonical, facet, source}, ...] per row -- `id`
    (content_tags PK, BUKAN tag_id) disertakan supaya UI bisa panggil
    remove_tag() langsung tanpa query tambahan. `source` (MANUAL/SUGGESTED,
    Addendum C §21.9 GELOMBANG C-2) disertakan sejak suggest_tags_for_news()
    ada -- UI bedakan visual tag yang Giel ketik sendiri vs auto-suggest."""
    if not rows:
        return rows
    ids = [r["id"] for r in rows]
    placeholders = ",".join("?" for _ in ids)
    tagged = conn.execute(
        f"SELECT c.id, c.ref_id, c.source, t.canonical, t.facet FROM content_tags c "
        f"JOIN tag_dictionary t ON t.id = c.tag_id "
        f"WHERE c.ref_table = ? AND c.ref_id IN ({placeholders}) "
        f"ORDER BY c.ref_id, t.facet, t.canonical",
        [ref_table, *ids],
    ).fetchall()
    by_ref: dict[int, list[dict[str, Any]]] = {}
    for r in tagged:
        by_ref.setdefault(r["ref_id"], []).append(
            {"id": r["id"], "canonical": r["canonical"], "facet": r["facet"], "source": r["source"]}
        )
    for row in rows:
        row["tags"] = by_ref.get(row["id"], [])
    return rows


# ---------- Settings -> Tag & Thread Management (Addendum C §21.11, C-1 gap
# ditutup 17 Jul 2026) -- kurasi lambat/reflektif, TERPISAH dari command-
# palette News/Reading yang cepat (§21.11 prinsip "capture cepat, curate
# lambat"). merge_tag/delete_tag SENGAJA tidak ada di NewsView -- operasi ini
# butuh konteks penuh kamus (usage_count, tag lain yang mirip), bukan aksi
# 1-klik saat baca berita. ----------

def update_tag(
    conn: sqlite3.Connection, tag_id: int, *, description: str | None = None,
    facet: str | None = None,
) -> dict[str, Any]:
    """Koreksi description/facet tag yang sudah ada (bukan ganti canonical --
    itu domain merge_tag). Guard: tag harus ada, facet baru (kalau diisi)
    harus dikenal."""
    current = conn.execute("SELECT * FROM tag_dictionary WHERE id = ?", (tag_id,)).fetchone()
    if current is None:
        raise ValueError(f"tag id {tag_id} tidak ditemukan")
    if facet is not None and facet not in ALLOWED_FACETS:
        raise ValueError(f"facet '{facet}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_FACETS))}")
    updates: dict[str, Any] = {}
    if description is not None:
        updates["description"] = description
    if facet is not None:
        updates["facet"] = facet
    if updates:
        cols = ", ".join(f"{k} = :{k}" for k in updates)
        conn.execute(f"UPDATE tag_dictionary SET {cols} WHERE id = :id", {**updates, "id": tag_id})
    return _decode_tag(dict(conn.execute("SELECT * FROM tag_dictionary WHERE id = ?", (tag_id,)).fetchone()))


def delete_tag(conn: sqlite3.Connection, tag_id: int, force: bool = False) -> bool:
    """Hapus tag dari kamus. Guard: kalau masih terpakai (usage_count > 0)
    DAN force=False -> ValueError (cegah hapus diam-diam yang meninggalkan
    content_tags yatim tanpa Giel sadar dampaknya). force=True hapus tag
    DAN semua content_tags yang menunjuknya sekaligus (bukan cuma kamusnya)."""
    row = conn.execute("SELECT usage_count FROM tag_dictionary WHERE id = ?", (tag_id,)).fetchone()
    if row is None:
        return False
    if row["usage_count"] > 0 and not force:
        raise ValueError(
            f"tag masih dipakai {row['usage_count']} kali -- pakai force=true kalau yakin"
        )
    conn.execute("DELETE FROM content_tags WHERE tag_id = ?", (tag_id,))
    conn.execute("DELETE FROM tag_dictionary WHERE id = ?", (tag_id,))
    return True


def merge_tag(conn: sqlite3.Connection, from_id: int, into_id: int) -> dict[str, Any]:
    """Gabung 2 tag duplikat (mis. `us-fed` ke `org:fed`) -- operasi yang
    MUSTAHIL dilakukan inline di News (§21.11). `from_id` jadi alias
    `into_id`: semua content_tags re-point (dedup-aware -- baris yang sudah
    ditag `into` tidak diduplikasi, baris `from` yang jadi redundan setelah
    re-point dihapus), canonical `from` masuk `aliases` `into` (referensi lama
    tetap resolve lewat resolve_tag), `usage_count` `into` dihitung ULANG dari
    content_tags aktual (bukan dijumlah -- re-point bisa collide & tidak
    nambah baris baru, jumlah naif akan salah)."""
    if from_id == into_id:
        raise ValueError("tidak bisa merge tag ke dirinya sendiri")
    src = conn.execute("SELECT * FROM tag_dictionary WHERE id = ?", (from_id,)).fetchone()
    dst = conn.execute("SELECT * FROM tag_dictionary WHERE id = ?", (into_id,)).fetchone()
    if src is None or dst is None:
        raise ValueError("tag from_id/into_id tidak ditemukan")
    # Re-point tiap content_tags baris dari from -> into. INSERT OR IGNORE
    # dulu (kena UNIQUE(ref_table, ref_id, tag_id) kalau baris itu sudah
    # ditag `into` juga -- diam-diam diabaikan, itu yang diinginkan), baru
    # hapus baris `from` yang sekarang redundan.
    from_rows = conn.execute(
        "SELECT ref_table, ref_id, source, created_at FROM content_tags WHERE tag_id = ?", (from_id,)
    ).fetchall()
    for r in from_rows:
        conn.execute(
            "INSERT OR IGNORE INTO content_tags (ref_table, ref_id, tag_id, source, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (r["ref_table"], r["ref_id"], into_id, r["source"], r["created_at"]),
        )
    conn.execute("DELETE FROM content_tags WHERE tag_id = ?", (from_id,))
    dst_aliases = json.loads(dst["aliases"]) if dst["aliases"] else []
    if src["canonical"] not in dst_aliases:
        dst_aliases.append(src["canonical"])
    for alias in (json.loads(src["aliases"]) if src["aliases"] else []):
        if alias not in dst_aliases:
            dst_aliases.append(alias)
    new_usage = conn.execute(
        "SELECT COUNT(*) AS n FROM content_tags WHERE tag_id = ?", (into_id,)
    ).fetchone()["n"]
    conn.execute(
        "UPDATE tag_dictionary SET aliases = ?, usage_count = ? WHERE id = ?",
        (json.dumps(dst_aliases), new_usage, into_id),
    )
    conn.execute("DELETE FROM tag_dictionary WHERE id = ?", (from_id,))
    return _decode_tag(dict(conn.execute("SELECT * FROM tag_dictionary WHERE id = ?", (into_id,)).fetchone()))


def list_orphan_tags(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Tag yang dibuat tapi tak pernah dipakai (usage_count=0) -- kandidat
    hapus di review kuartalan (§21.7/§21.11)."""
    rows = conn.execute(
        "SELECT * FROM tag_dictionary WHERE usage_count = 0 ORDER BY created_at DESC"
    ).fetchall()
    return [_decode_tag(dict(r)) for r in rows]


# ---------- Addendum C, GELOMBANG C-2 (17 Jul 2026, Giel override 2-minggu-
# tunggu §21.8 -- "Section 21 & C-1/C-2. FINAL"). ----------

def suggest_tags_for_news(conn: sqlite3.Connection, news_items: list[dict[str, Any]]) -> int:
    """Auto-suggest tag rule-based (BUKAN LLM, §21.9) ke headline BARU:
    untuk tiap tag di kamus, keyword pool = aliases + value-nya sendiri
    (hyphen->spasi, mis. "rate-policy" -> "rate policy") di-match ke headline
    (`keyword_matches`, sama fungsi yg dipakai suggest_thread_links). Match ->
    INSERT content_tags source='SUGGESTED' (idempoten via
    idx_content_tags_dedup). usage_count naik HANYA saat insert baru beneran
    (rowcount check, pola sama apply_tag). Mirrors suggest_thread_links()'s
    shape persis -- dipanggil pipeline/run_daily.py SETELAH insert_news_dedup
    (butuh row id asli), SEBELUM suggest_thread_links (biar tag-match §21.5
    lihat tag yang baru saja disarankan di run yang sama). Return jumlah tag
    baru terpasang."""
    if not news_items:
        return 0
    tags = conn.execute("SELECT id, canonical, aliases FROM tag_dictionary").fetchall()
    tag_pool = []
    for t in tags:
        value = t["canonical"].split(":", 1)[1] if ":" in t["canonical"] else t["canonical"]
        aliases = json.loads(t["aliases"]) if t["aliases"] else []
        pool = [*aliases, value.replace("-", " ")]
        tag_pool.append((t["id"], pool))
    if not tag_pool:
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
        for tag_id, pool in tag_pool:
            if not keyword_matches(headline_lower, pool):
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO content_tags (ref_table, ref_id, tag_id, source, created_at) "
                "VALUES ('daily_news', ?, ?, 'SUGGESTED', ?)",
                (row["id"], tag_id, now),
            )
            if cur.rowcount:
                conn.execute(
                    "UPDATE tag_dictionary SET usage_count = usage_count + 1 WHERE id = ?", (tag_id,)
                )
                inserted += 1
    return inserted


def _stance_composition(rows: list[Any]) -> dict[str, int]:
    composition = {"MENDUKUNG": 0, "KONTRA": 0, "NETRAL": 0}
    for r in rows:
        if r["stance"] in composition:
            composition[r["stance"]] = r["n"]
    return composition


def thread_stats(conn: sqlite3.Connection, thread_id: int) -> dict[str, Any]:
    """1 thread: komposisi stance link CONFIRMED, jumlah SUGGESTED pending,
    umur (hari), + blok ringkasan kepala thread F-2 (§24.4): tren 30 hari
    (komposisi CONFIRMED yang linked_at-nya dalam 30 hari terakhir --
    "ke mana arahnya belakangan", bukan cuma rasio total), shift_warning
    (True kalau mayoritas stance 30 hari BEDA dari mayoritas keseluruhan --
    sinyal komposisi bergeser), jumlah milestone, & ringkasan opini sekunder
    (reuse thread_opinion_summary(), F1 tetap tidak tersentuh). Dipisah dari
    get_thread() -- get_thread tetap murah untuk polling ThreadIndexView/
    NewsView, ini dipanggil Settings & ThreadDetailView (jarang, lebih
    berat)."""
    stance_rows = conn.execute(
        "SELECT stance, COUNT(*) AS n FROM news_thread_links "
        "WHERE thread_id = ? AND link_status = 'CONFIRMED' GROUP BY stance",
        (thread_id,),
    ).fetchall()
    composition = _stance_composition(stance_rows)
    trend_rows = conn.execute(
        "SELECT stance, COUNT(*) AS n FROM news_thread_links "
        "WHERE thread_id = ? AND link_status = 'CONFIRMED' "
        "AND linked_at >= date('now', '-30 day') GROUP BY stance",
        (thread_id,),
    ).fetchall()
    trend_30d = _stance_composition(trend_rows)

    def _majority(comp: dict[str, int]) -> str | None:
        nonzero = {k: v for k, v in comp.items() if v > 0}
        if not nonzero:
            return None
        top = max(nonzero.values())
        leaders = [k for k, v in nonzero.items() if v == top]
        return leaders[0] if len(leaders) == 1 else None

    overall_majority = _majority(composition)
    trend_majority = _majority(trend_30d)
    shift_warning = bool(
        overall_majority and trend_majority and overall_majority != trend_majority
    )
    pending = conn.execute(
        "SELECT COUNT(*) AS n FROM news_thread_links WHERE thread_id = ? AND link_status = 'SUGGESTED'",
        (thread_id,),
    ).fetchone()["n"]
    milestone_count = conn.execute(
        "SELECT COUNT(*) AS n FROM news_thread_links WHERE thread_id = ? "
        "AND link_status = 'CONFIRMED' AND is_milestone = 1", (thread_id,),
    ).fetchone()["n"]
    age_row = conn.execute(
        "SELECT CAST(julianday('now') - julianday(created_at) AS INTEGER) AS age_days "
        "FROM news_threads WHERE id = ?", (thread_id,),
    ).fetchone()
    return {
        "thread_id": thread_id, "composition": composition, "trend_30d": trend_30d,
        "shift_warning": shift_warning, "pending_suggested": pending,
        "milestone_count": milestone_count,
        "opinions": thread_opinion_summary(conn, thread_id),
        "age_days": age_row["age_days"] if age_row and age_row["age_days"] is not None else 0,
    }


def list_threads_with_stats(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """list_threads() + thread_stats per baris + active_count global (sama
    di tiap baris -- cara termurah nampilkan jumlah thread ACTIVE tanpa
    endpoint kedua) + facet tags thread sendiri (reuse attach_content_tags,
    ref_table 'news_threads' -- sudah ada di ALLOWED_CONTENT_TAG_REF_TABLES,
    thread rows punya "id" field sama seperti daily_news rows jadi langsung
    kompatibel tanpa fungsi baru). Dipakai Settings Tab Threads saja (mahal
    dibanding list_threads biasa -- N+1 query kecil, tapi jumlah thread masih
    kecil di praktiknya jadi aman)."""
    threads = list_threads(conn)
    active_count = conn.execute(
        "SELECT COUNT(*) AS n FROM news_threads WHERE status = 'ACTIVE'"
    ).fetchone()["n"]
    for t in threads:
        stats = thread_stats(conn, t["id"])
        t.update({k: v for k, v in stats.items() if k != "thread_id"})
        t["active_count"] = active_count
    return attach_content_tags(conn, "news_threads", threads)


def auto_dormant_stale_threads(conn: sqlite3.Connection, stale_days: int = STALE_THREAD_DAYS) -> int:
    """Thread ACTIVE yang tidak di-update (patch_thread atau link baru bumps
    updated_at) selama `stale_days` -> otomatis DORMANT (bukan hapus/CLOSED,
    tetap bisa diaktifkan manual). Dipanggil run_daily.py, cheap, fits ritme
    harian yang sudah ada. Return jumlah thread yang di-DORMANT-kan."""
    cur = conn.execute(
        "UPDATE news_threads SET status = 'DORMANT', updated_at = ? "
        "WHERE status = 'ACTIVE' AND updated_at < date('now', ?)",
        (today_wib(), f"-{stale_days} day"),
    )
    return cur.rowcount


# ---------- Holdings / Portfolio tracker (docs/universe_portfolio_restructure_v1.md
# §4, Langkah 4, 3 Aug 2026) -- manual entry, TIDAK ADA API broker (kontrak
# §15). `book` (TRADE/INVEST) adalah paspor uang, WAJIB -- ditegakkan di sini
# (bukan cuma constraint NOT NULL di schema, biar error-nya jelas dibaca).
# Guard lanjutan (konversi book terkunci, indikator basi, flag TRADE tanpa
# jurnal) SENGAJA belum di sini -- itu Langkah 6, urutan garapan sendiri. ----------

ALLOWED_BOOK = {"TRADE", "INVEST"}
ALLOWED_CURRENCY = {"IDR", "USD", "SGD"}

# Langkah 5 (3 Aug 2026, §4.3 "Alokasi vs SOP"): kategori EKSPLISIT dipilih
# Giel per holding (bukan ditebak dari instrument -- keputusan sadar Giel
# saat diminta pilih antara guess-otomatis vs field manual, lihat ROADMAP).
# Target % dari Investment SOP v4.1 (30/20/20/15/15); KAS_IDR target 0% --
# dry powder yang tidak ditempatkan itu SENGAJA diberi target 0, bukan
# "kategori lain", biar langsung kelihatan sebagai penyimpangan.
ALLOWED_SOP_CATEGORY = {"SAHAM_IHSG", "EMAS", "CRYPTO", "VALAS", "GLOBAL_EQ", "KAS_IDR"}
SOP_TARGET_PCT = {
    "SAHAM_IHSG": 30.0, "EMAS": 20.0, "CRYPTO": 20.0,
    "VALAS": 15.0, "GLOBAL_EQ": 15.0, "KAS_IDR": 0.0,
}


def create_holding(
    conn: sqlite3.Connection, *, instrument: str, provider: str, book: str,
    quantity: float, unit: str, sop_category: str, avg_price: float | None = None,
    currency: str = "IDR", opened_at: str | None = None,
    linked_journal_id: int | None = None, notes: str | None = None,
) -> dict[str, Any]:
    """Catat 1 holding baru. Guard: instrument/provider/unit wajib non-kosong,
    book harus TRADE/INVEST (paspor uang -- kontrak §21.11 style enum
    validation), sop_category harus salah satu dari 6 kategori Investment SOP
    v4.1 (dipilih Giel eksplisit di form -- BUKAN ditebak dari instrument/
    currency, keputusan sadar krn tebakan otomatis rawan salah utk kasus tak
    terduga spt reksadana index luar negeri), currency harus IDR/USD/SGD,
    quantity harus > 0. Form input minimal (Langkah 4) -- linked_journal_id
    BOLEH kosong sekalipun book=TRADE (flag "TRADE tanpa jurnal" itu Langkah
    6, bukan blocker di sini)."""
    if not instrument or not instrument.strip():
        raise ValueError("instrument wajib diisi")
    if not provider or not provider.strip():
        raise ValueError("provider wajib diisi")
    if book not in ALLOWED_BOOK:
        raise ValueError(f"book '{book}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_BOOK))}")
    if not unit or not unit.strip():
        raise ValueError("unit wajib diisi")
    if quantity is None or quantity <= 0:
        raise ValueError("quantity harus > 0")
    if currency not in ALLOWED_CURRENCY:
        raise ValueError(f"currency '{currency}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_CURRENCY))}")
    if sop_category not in ALLOWED_SOP_CATEGORY:
        raise ValueError(f"sop_category '{sop_category}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_SOP_CATEGORY))}")
    now = today_wib()
    row = {
        "instrument": instrument.strip().upper(), "provider": provider.strip(), "book": book,
        "quantity": quantity, "unit": unit.strip(), "avg_price": avg_price, "currency": currency,
        "opened_at": opened_at or now, "last_updated": now, "linked_journal_id": linked_journal_id,
        "notes": notes, "is_closed": 0, "created_at": now, "sop_category": sop_category,
    }
    cur = conn.execute(
        "INSERT INTO holdings (instrument, provider, book, quantity, unit, avg_price, "
        "currency, opened_at, last_updated, linked_journal_id, notes, is_closed, created_at, "
        "sop_category) "
        "VALUES (:instrument, :provider, :book, :quantity, :unit, :avg_price, :currency, "
        ":opened_at, :last_updated, :linked_journal_id, :notes, :is_closed, :created_at, "
        ":sop_category)",
        row,
    )
    row["id"] = cur.lastrowid
    return row


def list_holdings(
    conn: sqlite3.Connection, *, book: str | None = None, provider: str | None = None,
    include_closed: bool = False,
) -> list[dict[str, Any]]:
    """Semua holdings, terbaru dulu. Filter opsional by book/provider; default
    sembunyikan yang is_closed=1 (posisi yang sudah ditutup, bukan dihapus)."""
    sql = "SELECT * FROM holdings WHERE 1=1"
    params: list[Any] = []
    if not include_closed:
        sql += " AND is_closed = 0"
    if book:
        sql += " AND book = ?"
        params.append(book.upper())
    if provider:
        sql += " AND provider = ?"
        params.append(provider)
    sql += " ORDER BY provider, instrument"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def compute_portfolio_allocation(conn: sqlite3.Connection) -> dict[str, Any]:
    """Alokasi vs SOP + Per Mata Uang (§4.3), 1 fungsi 1 basis konversi biar
    dua breakdown ini konsisten. Nilai tiap holding = quantity * avg_price
    dikonversi ke IDR-equivalent: IDR apa adanya, USD dikali `usd_idr`
    TERBARU dari daily_market (reuse data yang sudah ada, bukan scraper
    baru). SGD TIDAK dikonversi -- app ini tidak punya sumber kurs SGD sama
    sekali -- dan holding tanpa avg_price/sop_category (mis. holding lama
    sebelum kolom ini ada) juga tidak bisa dihitung nilainya. Keduanya
    masuk `excluded` dgn alasan, BUKAN diam-diam dilewati -- alokasi yang
    dihitung dari data yang diam-diam tidak lengkap adalah alokasi bohong
    (prinsip yang sama dgn indikator basi §4.4)."""
    rows = list_holdings(conn)
    usd_idr_row = conn.execute(
        "SELECT usd_idr FROM daily_market WHERE usd_idr IS NOT NULL ORDER BY date DESC LIMIT 1"
    ).fetchone()
    usd_idr_rate = usd_idr_row["usd_idr"] if usd_idr_row else None

    by_category: dict[str, float] = {c: 0.0 for c in ALLOWED_SOP_CATEGORY}
    by_currency: dict[str, float] = {}
    excluded: list[dict[str, Any]] = []
    total_idr = 0.0

    for h in rows:
        if h["avg_price"] is None:
            excluded.append({"instrument": h["instrument"], "provider": h["provider"], "reason": "avg_price kosong"})
            continue
        if not h["sop_category"] or h["sop_category"] not in ALLOWED_SOP_CATEGORY:
            excluded.append({"instrument": h["instrument"], "provider": h["provider"], "reason": "sop_category belum diisi"})
            continue
        value_native = h["quantity"] * h["avg_price"]
        if h["currency"] == "IDR":
            value_idr = value_native
        elif h["currency"] == "USD" and usd_idr_rate:
            value_idr = value_native * usd_idr_rate
        else:
            excluded.append({
                "instrument": h["instrument"], "provider": h["provider"],
                "reason": "SGD belum ada sumber kurs" if h["currency"] == "SGD" else "kurs USD/IDR tidak tersedia",
            })
            continue
        by_category[h["sop_category"]] += value_idr
        by_currency[h["currency"]] = by_currency.get(h["currency"], 0.0) + value_idr
        total_idr += value_idr

    def pct(v: float) -> float:
        return round(v / total_idr * 100, 1) if total_idr > 0 else 0.0

    categories = [
        {
            "category": c, "value_idr": round(by_category[c], 2), "pct": pct(by_category[c]),
            "target_pct": SOP_TARGET_PCT[c], "delta_pct": round(pct(by_category[c]) - SOP_TARGET_PCT[c], 1),
        }
        for c in sorted(ALLOWED_SOP_CATEGORY, key=lambda c: -SOP_TARGET_PCT[c])
    ]
    currencies = [
        {"currency": cur, "value_idr": round(v, 2), "pct": pct(v)}
        for cur, v in sorted(by_currency.items(), key=lambda kv: -kv[1])
    ]
    return {
        "total_idr": round(total_idr, 2), "usd_idr_rate": usd_idr_rate,
        "by_category": categories, "by_currency": currencies, "excluded": excluded,
    }


# ---------- Holdings Langkah 6: guard book-conversion + log (§4.4, 3 Aug 2026) ----------
# "book wajib" (poin 1, §4.4) sudah ditegakkan sejak Langkah 4 (create_holding
# raise ValueError kalau book bukan TRADE/INVEST) -- tidak ada perubahan
# tambahan di sini utk itu. Indikator basi & flag TRADE-tanpa-jurnal murni
# computed di frontend dari field yang sudah dikembalikan list_holdings()
# (last_updated, book, linked_journal_id) -- tidak perlu logic baru di sini.

STALE_HOLDING_DAYS = 30


def convert_holding_book(
    conn: sqlite3.Connection, holding_id: int, new_book: str, reason: str,
) -> dict[str, Any]:
    """SATU-SATUNYA jalur ubah `book` -- bukan lewat edit biasa (memang belum
    ada edit field lain sama sekali di Langkah 4-6, jadi ini juga satu-
    satunya mutasi holding selain create). Guard: holding harus ada,
    new_book harus TRADE/INVEST DAN beda dari book sekarang, reason wajib
    non-kosong. Diblokir kalau posisi instrumen ini SEDANG RUGI (avg_price
    vs close terbaru di asset_ohlcv) -- §4.4: "konversi paspor saat merah
    selalu punya satu motif: menghindari mengakui salah". Kalau instrumen
    TIDAK ada di asset_ohlcv (emas fisik/gram, cash, dll) -- P&L tidak bisa
    diverifikasi, konversi DIIZINKAN (data bolong = ditunda/dicatat jujur,
    BUKAN dianggap rugi/untung diam-diam) tapi dicatat jelas di pnl_check."""
    row = conn.execute("SELECT * FROM holdings WHERE id = ?", (holding_id,)).fetchone()
    if not row:
        raise ValueError("holding tidak ditemukan")
    if new_book not in ALLOWED_BOOK:
        raise ValueError(f"book '{new_book}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_BOOK))}")
    if new_book == row["book"]:
        raise ValueError(f"holding ini sudah book={new_book}, tidak ada yang dikonversi")
    if not reason or not reason.strip():
        raise ValueError("alasan wajib diisi")

    pnl_check = "tidak diverifikasi (instrumen tidak ada di asset_ohlcv)"
    if row["avg_price"] is not None:
        price_row = conn.execute(
            "SELECT close FROM asset_ohlcv WHERE instrument = ? ORDER BY date DESC LIMIT 1",
            (row["instrument"],),
        ).fetchone()
        if price_row and price_row["close"] is not None:
            unrealized = (price_row["close"] - row["avg_price"]) * row["quantity"]
            if unrealized < 0:
                raise ValueError(
                    f"posisi {row['instrument']} sedang rugi (unrealized {unrealized:.2f} "
                    f"{row['currency']}) -- konversi book diblokir saat rugi (§4.4)"
                )
            pnl_check = f"terverifikasi untung (unrealized {unrealized:.2f} {row['currency']})"

    now = today_wib()
    conn.execute("UPDATE holdings SET book = ?, last_updated = ? WHERE id = ?", (new_book, now, holding_id))
    conn.execute(
        "INSERT INTO holding_book_conversion_log "
        "(holding_id, from_book, to_book, reason, pnl_check, converted_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (holding_id, row["book"], new_book, reason.strip(), pnl_check, now),
    )
    return {
        "id": holding_id, "instrument": row["instrument"], "from_book": row["book"],
        "to_book": new_book, "pnl_check": pnl_check,
    }


def list_holding_conversions(conn: sqlite3.Connection, limit: int = 200) -> list[dict[str, Any]]:
    """Riwayat konversi book, terbaru dulu -- join nama instrument dari
    holdings biar tidak cuma nampilin holding_id mentah."""
    rows = conn.execute(
        "SELECT l.*, h.instrument, h.provider FROM holding_book_conversion_log l "
        "JOIN holdings h ON h.id = l.holding_id "
        "ORDER BY l.converted_at DESC, l.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------- Secondary Opinions -- Addendum F §24, F-1 (3 Aug 2026) ----------
# F1 (terkunci): lapisan TERPISAH dari bukti thread -- TIDAK ADA kolom stance
# di sini, dan TIDAK ADA fungsi apa pun di file ini yang membaca tabel ini
# untuk menghitung komposisi MENDUKUNG/KONTRA/NETRAL (itu murni
# news_thread_links, lihat thread_stats()/list_threads_with_stats() di
# atas). Guard ini ditegaskan lewat test, bukan cuma komentar -- lihat
# test_secondary_opinion_never_leaks_into_thread_stats.

ALLOWED_SOURCE_TYPE = {"VIDEO", "BOOK", "PAPER", "PODCAST", "REPORT", "OTHER"}
ALLOWED_TESTABLE = {"TESTABLE", "SPEKULATIF"}
# F-2 (§24.4, 4 Aug 2026) -- klasifikasi eksplisit relasi opini thd pandangan
# Giel, dipakai blok ringkasan kepala thread + digest persona. Opsional
# (nullable) -- lihat catatan di schema.sql, tidak ditebak dari teks bebas.
ALLOWED_RELATION_TO_VIEW = {"SEJALAN", "MENANTANG"}


def create_secondary_opinion(
    conn: sqlite3.Connection, *, source_type: str, source_ref: str, my_summary: str,
    core_claim: str, testable: str, author: str | None = None, my_stance: str | None = None,
    conflict_of_interest: str | None = None, thread_id: int | None = None,
    relation_to_view: str | None = None,
) -> dict[str, Any]:
    """Catat 1 opini sekunder. Guard: source_type ∈ ALLOWED_SOURCE_TYPE,
    source_ref/my_summary/core_claim wajib non-kosong (F2: yang disimpan
    destilasi Giel, bukan transkrip -- makanya my_summary & core_claim
    wajib, bukan opsional), testable ∈ {TESTABLE, SPEKULATIF} (F3, wajib
    diisi -- tidak ada default netral supaya Giel selalu sadar
    membedakannya). thread_id opsional (F1: menempel ke thread, bukan
    tautan bukti) -- kalau diisi, thread-nya harus benar-benar ada.
    relation_to_view opsional (F-2) -- kalau diisi, harus ∈
    ALLOWED_RELATION_TO_VIEW; kosong = jujur "belum diklasifikasi", bukan
    error (opini boleh dicatat dulu, diklasifikasi belakangan)."""
    if source_type not in ALLOWED_SOURCE_TYPE:
        raise ValueError(f"source_type '{source_type}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_SOURCE_TYPE))}")
    if not source_ref or not source_ref.strip():
        raise ValueError("source_ref wajib diisi")
    if not my_summary or not my_summary.strip():
        raise ValueError("my_summary wajib diisi (destilasi kamu sendiri, bukan transkrip mentah)")
    if not core_claim or not core_claim.strip():
        raise ValueError("core_claim wajib diisi")
    if testable not in ALLOWED_TESTABLE:
        raise ValueError(f"testable '{testable}' tidak dikenal -- pilihan: {'/'.join(sorted(ALLOWED_TESTABLE))}")
    if thread_id is not None:
        exists = conn.execute("SELECT 1 FROM news_threads WHERE id = ?", (thread_id,)).fetchone()
        if not exists:
            raise ValueError(f"thread_id {thread_id} tidak ditemukan")
    if relation_to_view and relation_to_view not in ALLOWED_RELATION_TO_VIEW:
        raise ValueError(
            f"relation_to_view '{relation_to_view}' tidak dikenal -- pilihan: "
            f"{'/'.join(sorted(ALLOWED_RELATION_TO_VIEW))}"
        )
    now = today_wib()
    row = {
        "source_type": source_type, "source_ref": source_ref.strip(), "author": author,
        "my_summary": my_summary.strip(), "core_claim": core_claim.strip(), "testable": testable,
        "my_stance": my_stance, "conflict_of_interest": conflict_of_interest,
        "relation_to_view": relation_to_view or None,
        "thread_id": thread_id, "created_at": now,
    }
    cur = conn.execute(
        "INSERT INTO secondary_opinions (source_type, source_ref, author, my_summary, core_claim, "
        "testable, my_stance, conflict_of_interest, relation_to_view, thread_id, created_at) "
        "VALUES (:source_type, :source_ref, :author, :my_summary, :core_claim, :testable, "
        ":my_stance, :conflict_of_interest, :relation_to_view, :thread_id, :created_at)",
        row,
    )
    row["id"] = cur.lastrowid
    return row


def list_secondary_opinions(conn: sqlite3.Connection, *, thread_id: int | None = None) -> list[dict[str, Any]]:
    """Semua opini sekunder, terbaru dulu. Filter opsional by thread_id --
    dipakai rak "Opini Sekunder" di halaman thread (§24.3)."""
    sql = "SELECT * FROM secondary_opinions"
    params: list[Any] = []
    if thread_id is not None:
        sql += " WHERE thread_id = ?"
        params.append(thread_id)
    sql += " ORDER BY created_at DESC, id DESC"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def thread_opinion_summary(conn: sqlite3.Connection, thread_id: int) -> dict[str, Any]:
    """Ringkas opini sekunder 1 thread jadi {total, sejalan, menantang,
    unclassified} (F-2 §24.4) -- dipakai blok ringkasan kepala thread &
    digest persona. `relation_to_view` NULL dihitung jujur sebagai
    unclassified, TIDAK ditebak masuk salah satu sisi (F1 tetap berlaku:
    fungsi ini TIDAK PERNAH menyentuh news_thread_links/stance thread)."""
    rows = conn.execute(
        "SELECT relation_to_view, COUNT(*) AS n FROM secondary_opinions "
        "WHERE thread_id = ? GROUP BY relation_to_view", (thread_id,),
    ).fetchall()
    summary = {"total": 0, "sejalan": 0, "menantang": 0, "unclassified": 0}
    for r in rows:
        summary["total"] += r["n"]
        if r["relation_to_view"] == "SEJALAN":
            summary["sejalan"] = r["n"]
        elif r["relation_to_view"] == "MENANTANG":
            summary["menantang"] = r["n"]
        else:
            summary["unclassified"] += r["n"]
    return summary


# ---------- Telegram bot /status (5 Agustus 2026) ----------

def telegram_status_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """Ringkas kondisi pipeline utk command Telegram /status -- dipakai
    Giel cek "cron beneran jalan gak" dari HP tanpa buka dashboard (motivasi
    asli fitur bot ini, lihat ROADMAP.md 4/5 Agustus 2026). `daily_market`
    jadi sumber "kapan run_daily terakhir" krn diisi tiap run (beda dari
    daily_news yang bisa nol baris di hari sepi). Tiap tabel (daily_market,
    asset_ohlcv, daily_news) dicek TANGGAL TERBARUNYA SENDIRI-SENDIRI --
    BUKAN diasumsikan selalu sinkron -- supaya "berita ketinggalan tapi
    market ok" (atau sebaliknya) kelihatan, bukan tersembunyi di balik satu
    tanggal gabungan."""
    market_row = conn.execute(
        "SELECT date, created_at, source_flags FROM daily_market ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if not market_row:
        return {"last_date": None}
    flags = json.loads(market_row["source_flags"]) if market_row["source_flags"] else {}
    fail_names = sorted(k for k, v in flags.items() if v == "fail")
    news_row = conn.execute(
        "SELECT date, COUNT(*) AS n FROM daily_news GROUP BY date ORDER BY date DESC LIMIT 1"
    ).fetchone()
    ohlcv_row = conn.execute(
        "SELECT date, COUNT(*) AS n FROM asset_ohlcv GROUP BY date ORDER BY date DESC LIMIT 1"
    ).fetchone()
    econ_upcoming = conn.execute(
        "SELECT COUNT(*) AS n FROM econ_calendar WHERE event_date >= ?", (today_wib(),),
    ).fetchone()["n"]
    pending_signals = conn.execute(
        "SELECT COUNT(*) AS n FROM trade_signals WHERE approved = 0"
    ).fetchone()["n"]
    pending_links = conn.execute(
        "SELECT COUNT(*) AS n FROM news_thread_links WHERE link_status = 'SUGGESTED'"
    ).fetchone()["n"]
    return {
        "last_date": market_row["date"],
        "created_at": market_row["created_at"],
        "sources_ok": sum(1 for v in flags.values() if v == "ok"),
        "sources_fail": len(fail_names),
        "sources_fail_names": fail_names,
        "sources_skip": sum(1 for v in flags.values() if v == "skip"),
        "daily_market_date": market_row["date"],
        "daily_news_date": news_row["date"] if news_row else None,
        "daily_news_count": news_row["n"] if news_row else 0,
        "asset_ohlcv_date": ohlcv_row["date"] if ohlcv_row else None,
        "asset_ohlcv_count": ohlcv_row["n"] if ohlcv_row else 0,
        "econ_upcoming": econ_upcoming,
        "pending_signals": pending_signals,
        "pending_thread_links": pending_links,
    }
