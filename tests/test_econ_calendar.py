"""Test scraper economic calendar (ForexFactory). Butuh network (live API)."""
import pytest

from scrapers.econ_calendar import _parse_event, fetch_econ_calendar


@pytest.fixture(scope="module")
def econ():
    return fetch_econ_calendar()


def test_returns_dict_with_items_and_flags(econ):
    assert isinstance(econ, dict)
    assert "items" in econ
    assert "source_flags" in econ
    assert isinstance(econ["source_flags"], dict)


def test_no_crash_on_failure(econ):
    # fetch_econ_calendar tidak boleh melempar; selalu ada source_flags
    assert "forexfactory_calendar" in econ["source_flags"]


def test_importance_always_valid(econ):
    for it in econ["items"]:
        assert it["importance"] in {"HIGH", "MED", "LOW"}


def test_event_date_format(econ):
    for it in econ["items"][:20]:
        assert len(it["event_date"]) == 10  # YYYY-MM-DD
        assert it["event_date"][4] == "-" and it["event_date"][7] == "-"
        assert len(it["event_time"]) == 5  # HH:MM


def test_parse_event_maps_impact_and_country():
    row = _parse_event({
        "title": "FOMC Statement",
        "country": "USD",
        "date": "2026-07-06T14:00:00-04:00",
        "impact": "High",
        "forecast": "",
        "previous": "5.00%",
    })
    assert row["event_name"] == "FOMC Statement"
    assert row["country"] == "US"
    assert row["importance"] == "HIGH"
    assert row["forecast"] is None  # string kosong dinormalisasi jadi None
    assert row["previous"] == "5.00%"
    assert row["actual"] is None


def test_parse_event_skips_incomplete():
    assert _parse_event({"title": "", "date": "2026-07-06T14:00:00-04:00"}) is None
    assert _parse_event({"title": "X", "date": None}) is None
