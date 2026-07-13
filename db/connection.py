"""SQLite connection helpers untuk Kastara Finance.

Pakai:
    from db.connection import get_connection, init_db
    init_db()                       # buat semua tabel kalau belum ada
    with get_connection() as conn:  # ... query
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Root project = parent dari folder db/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"

# Daftar tabel yang HARUS ada setelah init_db (untuk verifikasi/test).
EXPECTED_TABLES = [
    "daily_market",
    "asset_ohlcv",
    "daily_news",
    "econ_calendar",
    "reading_workspace",
    "trade_signals",
    "sr_zones",
    "manual_articles",
    "trading_journal",
    "prediction_log",
    "asset_context_weight",
    "expectations",
    "positioning",
    "policy_tracker",
    "instrument_metadata",
    "fundamentals_quarterly",
    "earnings_calendar",
    "sector_benchmark",
    "emiten_grade",
    "grader_log",
    "intake_log",
]


def _resolve_db_path(raw: str) -> Path:
    """Terjemahkan nilai KASTARA_DB_PATH ke path yang benar di lingkungan ini.

    Menangani kasus Windows meski app jalan di dalam WSL:
    - UNC WSL '\\\\wsl.localhost\\<distro>\\home\\...' atau '\\\\wsl$\\<distro>\\...'
      -> path native Linux '/home/...' (menunjuk FILE YANG SAMA).
    - Path absolut Windows 'C:\\...' -> dibiarkan apa adanya.
    - Path absolut POSIX '/...' -> apa adanya.
    - Path relatif -> relatif ke root project.
    """
    s = raw.strip().replace("\\", "/")
    # UNC WSL -> native Linux path
    m = re.match(r"^//wsl(?:\.localhost|\$)/[^/]+/(.*)$", s, re.IGNORECASE)
    if m:
        return Path("/" + m.group(1))
    # Drive Windows (C:/...) -> absolut, biarkan
    if re.match(r"^[A-Za-z]:/", s):
        return Path(s)
    p = Path(s)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


def get_db_path() -> Path:
    """Lokasi file SQLite. Override via env KASTARA_DB_PATH, default kastara-finance.db."""
    raw = os.getenv("KASTARA_DB_PATH", "kastara-finance.db") or "kastara-finance.db"
    return _resolve_db_path(raw)


def get_connection(db_path: str | os.PathLike | None = None) -> sqlite3.Connection:
    """Buka koneksi SQLite dengan row_factory dict-like + foreign keys on.

    - journal_mode=DELETE (default SQLite): dipilih SADAR, bukan lupa
      di-set. Sempat pakai WAL, tapi WAL butuh shared-memory (-shm) yang
      tidak reliable lintas boundary Windows<->WSL (mis. DBeaver di Windows
      akses file lewat \\\\wsl.localhost\\... yang secara efektif network
      share/9P dari sisi Windows) -> WAL malah bikin SQLITE_BUSY yang sama,
      cuma ganti bentuk. DELETE mode + busy_timeout lebih predictable untuk
      pola akses ini. Tulisan kita (pipeline/dashboard) singkat (<1 detik),
      jadi trade-off exclusive-lock saat commit kecil.
    - busy_timeout=5000: kalau ada lock singkat, TUNGGU s/d 5 detik dan
      retry otomatis, bukan langsung error 'database is locked'. Ini cuma
      berlaku untuk koneksi yang dibuka lewat get_connection() ini
      (proses Python kita) -- client lain (DBeaver dll) yang connect
      langsung ke file perlu set busy_timeout di driver-nya sendiri kalau
      mau retry serupa.
    """
    path = Path(db_path) if db_path is not None else get_db_path()
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA journal_mode = DELETE;")
    return conn


# Kolom yang ditambahkan ke tabel yang SUDAH ADA setelah rilis awal (`CREATE
# TABLE IF NOT EXISTS` di schema.sql tidak menambah kolom ke DB lama yang
# sudah punya data -- perlu ALTER TABLE eksplisit, idempotent lewat cek
# PRAGMA table_info dulu). Tambah entri baru di sini tiap kali schema.sql
# dapat kolom baru di tabel existing.
_COLUMN_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "daily_market": [
        ("btc_oi_aggregate", "REAL"),
        ("btc_liq_long_24h", "REAL"),
        ("btc_liq_short_24h", "REAL"),
    ],
    "trading_journal": [
        ("planned_size", "REAL"),
        ("actual_size", "REAL"),
        ("skip_reason", "TEXT"),
        ("return_asset_ccy", "REAL"),
        ("return_idr", "REAL"),
    ],
    "policy_tracker": [
        ("sector_tags", "TEXT"),
    ],
    "asset_context_weight": [
        ("level", "TEXT"),
    ],
    "fundamentals_quarterly": [
        ("car", "REAL"),
        ("npl_gross", "REAL"),
        ("nim", "REAL"),
        ("ldr", "REAL"),
    ],
    "emiten_grade": [
        ("giel_override", "TEXT"),
    ],
    "grader_log": [
        ("outcome_3m", "TEXT"),
        ("outcome_6m", "TEXT"),
        ("outcome_notes", "TEXT"),
    ],
}


def _migrate_columns(conn: sqlite3.Connection) -> None:
    for table, columns in _COLUMN_MIGRATIONS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for col, coltype in columns:
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
                if table == "asset_context_weight" and col == "level":
                    # Row lama (Phase B) semuanya level instrumen (belum ada
                    # konsep index/sector saat itu) -- backfill biar lookup
                    # pewarisan (instrument->sector->index) tidak salah
                    # anggap NULL sebagai "index" atau ke-skip begitu saja.
                    conn.execute(
                        "UPDATE asset_context_weight SET level = 'INSTRUMENT' "
                        "WHERE level IS NULL"
                    )


def init_db(db_path: str | os.PathLike | None = None) -> Path:
    """Buat semua tabel dari schema.sql (idempotent). Return path db."""
    path = Path(db_path) if db_path is not None else get_db_path()
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection(path) as conn:
        conn.executescript(ddl)
        _migrate_columns(conn)
        conn.commit()
    return path


def list_tables(db_path: str | os.PathLike | None = None) -> list[str]:
    """Daftar nama tabel yang ada di db."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [r["name"] for r in rows]


if __name__ == "__main__":
    target = init_db()
    tables = list_tables()
    print(f"init_db OK -> {target}")
    print(f"{len(tables)} tabel: {', '.join(tables)}")
