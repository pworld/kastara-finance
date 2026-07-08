"""Regresi: KASTARA_DB_PATH berupa path Windows UNC harus di-map ke native WSL.

Bug asal: nilai '\\\\wsl.localhost\\Ubuntu\\home\\...\\x.db' dianggap relatif
(karena backslash bukan separator di Linux) lalu di-join ke PROJECT_ROOT ->
bikin file sampah bernama literal dengan backslash.
"""
from pathlib import Path

from db.connection import PROJECT_ROOT, _resolve_db_path


def test_unc_wsl_localhost_to_native():
    raw = "\\\\wsl.localhost\\Ubuntu\\home\\prame\\LOCAL\\kastara-finance\\kastara-finance.db"
    assert _resolve_db_path(raw) == Path(
        "/home/prame/LOCAL/kastara-finance/kastara-finance.db"
    )


def test_unc_wsl_dollar_to_native():
    raw = "\\\\wsl$\\Ubuntu\\home\\prame\\a.db"
    assert _resolve_db_path(raw) == Path("/home/prame/a.db")


def test_posix_absolute_unchanged():
    assert _resolve_db_path("/tmp/x.db") == Path("/tmp/x.db")


def test_relative_joined_to_project_root():
    assert _resolve_db_path("kastara-finance.db") == PROJECT_ROOT / "kastara-finance.db"
