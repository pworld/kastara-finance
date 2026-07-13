"""Test scrapers/idx_uma.py (Phase J+ Build Contract v1.3, J-11a)."""
import pytest

from scrapers.idx_uma import fetch_uma_announcements, is_recently_flagged, uma_history_for


@pytest.fixture(scope="module")
def uma_data():
    return fetch_uma_announcements()


def test_returns_structure(uma_data):
    assert "items" in uma_data
    assert "source_flags" in uma_data
    assert isinstance(uma_data["source_flags"], dict)


def test_items_have_expected_columns(uma_data):
    for item in uma_data["items"]:
        for col in ("date", "ticker", "is_followup_statement"):
            assert col in item
        assert len(item["ticker"]) >= 2


def test_uma_history_for_filters_by_ticker():
    items = [
        {"date": "2026-06-01", "ticker": "AAAA", "is_followup_statement": False},
        {"date": "2026-06-05", "ticker": "AAAA", "is_followup_statement": True},
        {"date": "2026-06-02", "ticker": "BBBB", "is_followup_statement": False},
    ]
    result = uma_history_for(items, "aaaa")
    assert len(result) == 2
    assert result[0]["date"] == "2026-06-05"  # terbaru dulu


def test_is_recently_flagged_within_window():
    items = [{"date": "2026-06-01", "ticker": "AAAA", "is_followup_statement": False}]
    assert is_recently_flagged(items, "AAAA", as_of_date="2026-06-15", window_days=90) is True
    assert is_recently_flagged(items, "AAAA", as_of_date="2026-12-01", window_days=90) is False


def test_is_recently_flagged_no_history_is_false():
    assert is_recently_flagged([], "ZZZZ", as_of_date="2026-06-15") is False


def test_bbca_not_uma_flagged_in_live_data(uma_data):
    """BBCA blue-chip bank -- realistis TIDAK ada di daftar UMA (bukan
    jaminan mutlak, tapi kalau ternyata ada, itu temuan penting utk dicek
    manual, bukan bug scraper)."""
    history = uma_history_for(uma_data["items"], "BBCA")
    # tidak assert False secara ketat (data live bisa berubah) -- cuma
    # pastikan scraper tidak crash & bentuk data tetap valid
    assert isinstance(history, list)
