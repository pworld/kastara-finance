"""Test scrapers/fundamentals_yf.py (Phase J+ Build Contract v1.3, J-4)."""
import pytest

from scrapers.fundamentals_yf import fetch_fundamentals_quarterly


@pytest.fixture(scope="module")
def bbca_fundamentals():
    return fetch_fundamentals_quarterly("BBCA", "IDX", is_financial=True)


@pytest.fixture(scope="module")
def tsla_fundamentals():
    return fetch_fundamentals_quarterly("TSLA", "US", is_financial=False)


def test_returns_structure(bbca_fundamentals):
    assert "rows" in bbca_fundamentals
    assert "source_flags" in bbca_fundamentals
    assert isinstance(bbca_fundamentals["source_flags"], dict)


def test_bbca_rows_have_columns(bbca_fundamentals):
    for row in bbca_fundamentals["rows"]:
        for col in ("quarter_end", "revenue", "net_income", "eps", "confidence"):
            assert col in row


def test_bbca_confidence_low_when_fewer_than_8_quarters(bbca_fundamentals):
    """yfinance cuma kasih ~5 kuartal (dicek live) -- konfirmasi flag
    LOW_CONFIDENCE otomatis, BUKAN ditolak (kontrak §16 poin 2)."""
    rows = bbca_fundamentals["rows"]
    if rows:
        assert len(rows) < 8
        assert all(r["confidence"] == "LOW_CONFIDENCE" for r in rows)


def test_tsla_net_interest_income_none_when_not_financial(tsla_fundamentals):
    """TSLA is_financial=False -- net_interest_income HARUS None di semua
    baris walau yfinance punya baris 'Net Interest Income' utk TSLA juga
    (dicek live, bukan NIM bank asli -- sengaja diabaikan)."""
    for row in tsla_fundamentals["rows"]:
        assert row["net_interest_income"] is None


def test_bbca_net_interest_income_populated_when_financial(bbca_fundamentals):
    """BBCA is_financial=True -- setidaknya 1 kuartal harus punya NIM terisi
    (bank selalu punya net interest income)."""
    rows = bbca_fundamentals["rows"]
    if rows:
        assert any(r["net_interest_income"] is not None for r in rows)
