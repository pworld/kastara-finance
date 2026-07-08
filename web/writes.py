"""Pure functions tulis-DB untuk Phase C (dashboard write-enabled).

Dipisah dari `web/app.py` supaya testable tanpa Flask (pola sama seperti
`pipeline/add_article.py`: fungsi insert murni terpisah dari CLI/route
wrapper). Semua fungsi di sini murni CRUD manual — **tidak ada** logic
AI/LLM, tidak ada execution/trading, sesuai plan_c.txt §0.

Konvensi `reading_workspace.lens` (Panel 4 & 6, bukan enum ketat di DB):
  GEMA / LEON / AKELA / RIVAN  -> 4 lensa Panel 4
  EXTERNAL_AI                  -> catatan banding AI eksternal (opsional)
  CONFLICT                     -> conflict notes (opsional)
  SYNTHESIS                    -> paragraf sintesis Panel 6
"""
from __future__ import annotations

import sqlite3
from typing import Any

from scrapers.base import created_at

READING_LENSES = ("GEMA", "LEON", "AKELA", "RIVAN")


# ---------- Panel 2: flag key trigger ----------

def flag_key_trigger(conn: sqlite3.Connection, news_id: int, is_key: bool = True) -> bool:
    """Update daily_news.is_key_trigger by id. Return False kalau id tidak ada."""
    exists = conn.execute("SELECT 1 FROM daily_news WHERE id = ?", (news_id,)).fetchone()
    if not exists:
        return False
    conn.execute(
        "UPDATE daily_news SET is_key_trigger = ? WHERE id = ?",
        (1 if is_key else 0, news_id),
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


# ---------- Panel 6: Synthesis + Trading Journal + Prediction Log ----------

def save_synthesis(conn: sqlite3.Connection, date: str, text: str) -> int | None:
    """Synthesis Panel 6 disimpan sebagai reading_workspace lens=SYNTHESIS.
    None kalau text kosong (tidak bikin row kosong)."""
    if not text or not text.strip():
        return None
    return save_reading_entry(conn, date, "SYNTHESIS", text.strip())


def insert_trading_journal(
    conn: sqlite3.Connection, *, date: str, instrument: str, setup_type: str | None,
    entry_price: float | None, sl_price: float | None, tp1_price: float | None,
    outcome: str | None, personal_notes: str | None, lesson_learned: str | None,
) -> int:
    cur = conn.execute(
        "INSERT INTO trading_journal (date, instrument, setup_type, entry_price, "
        "sl_price, tp1_price, outcome, personal_notes, lesson_learned, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (date, instrument, setup_type, entry_price, sl_price, tp1_price,
         outcome, personal_notes, lesson_learned, created_at()),
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
