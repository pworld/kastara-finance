"""Test scraper positioning (CFTC COT + farside BTC ETF flow). Butuh network (live API)."""
import pytest

from scrapers.positioning import (
    _parse_farside_number,
    _parse_farside_table,
    fetch_btc_etf_flow,
    fetch_cot_positioning,
    fetch_positioning,
)


@pytest.fixture(scope="module")
def positioning():
    return fetch_positioning()


def test_returns_dict_with_items_and_flags(positioning):
    assert isinstance(positioning, dict)
    assert "items" in positioning
    assert "source_flags" in positioning


def test_no_crash_and_flags_present(positioning):
    flags = positioning["source_flags"]
    for key in ("cot_btc", "cot_dxy", "cot_gold", "cot_sp500", "farside_btc_etf"):
        assert key in flags
        assert flags[key] in {"ok", "fail"}


def test_items_have_expected_shape(positioning):
    for it in positioning["items"]:
        assert set(it) == {"date", "instrument", "metric", "value", "source"}
        assert len(it["date"]) == 10 and it["date"][4] == "-"
        assert isinstance(it["value"], float)


def test_cot_positioning_covers_all_instruments():
    rows, flags = fetch_cot_positioning()
    instruments = {r["instrument"] for r in rows}
    # kalau semua sumber CFTC ok, harus dapat ke-4 instrument
    if all(flags.as_dict().get(f"cot_{i.lower()}") == "ok" for i in ("BTC", "DXY", "GOLD", "SP500")):
        assert instruments == {"BTC", "DXY", "GOLD", "SP500"}


def test_btc_etf_flow_recent_days():
    rows, flags = fetch_btc_etf_flow()
    if flags.as_dict().get("farside_btc_etf") == "ok":
        assert len(rows) > 0
        assert all(r["instrument"] == "BTC" and r["metric"] == "etf_net_flow" for r in rows)


# ---------- Parsing helpers (unit-level, tanpa network) ----------

def test_parse_farside_number():
    assert _parse_farside_number("209.4") == 209.4
    assert _parse_farside_number("(44.5)") == -44.5
    assert _parse_farside_number("1,119.9") == 1119.9
    assert _parse_farside_number("-") is None
    assert _parse_farside_number("") is None


def test_parse_farside_table_skips_header_and_footer_rows():
    html = """
    <table>
      <tr><td></td><td>Total</td></tr>
      <tr><td></td><td>IBIT</td></tr>
      <tr><td>06 Jul 2026</td><td>209.4</td><td>265.7</td></tr>
      <tr><td>07 Jul 2026</td><td>54.8</td><td>21.5</td></tr>
      <tr><td>Total</td><td>60,258</td><td>51,419</td></tr>
      <tr><td>Average</td><td>96.9</td><td>82.7</td></tr>
    </table>
    """
    rows = _parse_farside_table(html)
    assert rows == [
        {"date": "2026-07-06", "total_flow_musd": 265.7},
        {"date": "2026-07-07", "total_flow_musd": 21.5},
    ]


def test_parse_farside_table_raises_when_no_table():
    with pytest.raises(ValueError):
        _parse_farside_table("<html><body>no table here</body></html>")
