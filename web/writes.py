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
  OUTLOOK:<INSTRUMENT>         -> stance outlook Panel 6 (Bullish/Bearish/
                                  Neutral) per instrument, 1 baris per hari
                                  (upsert), lihat save_outlook()
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
