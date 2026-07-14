"""Test scraper investing.com economic calendar (pass kedua utk `actual`).

Sebagian besar test PURE (HTML snippet sintetis, tidak butuh network) --
struktur baris di-hardcode berdasarkan HTML asli yang dikonfirmasi live
(lihat docstring scrapers/investing_calendar.py). 1 test live-network
(module-scoped fixture, pola sama tests/test_idx_foreign_flow.py) di-skip
kalau investing.com unreachable/kena rate-limit saat test jalan -- bukan
gagal, karena sumber ini memang dikenal agresif soal blocking (lihat
docs/ROADMAP.md)."""
from bs4 import BeautifulSoup
import pytest

from scrapers.investing_calendar import (
    _page_event_date,
    _parse_row,
    _star_count,
    fetch_investing_actuals,
)


def _row_html(*, stars: int, country: str, name: str, act: str, cons: str = "0.2%", prev: str = "0.1%") -> BeautifulSoup:
    """Bangun 1 <tr> sintetis dgn struktur sama persis dgn investing.com asli
    (termasuk duplikat 3 svg kedua utk layout desktop, biar test _star_count
    juga menegakkan slice [:3] yang wajib)."""
    star_svgs = "".join(
        f'<svg class="{"opacity-60" if i < stars else "opacity-20"}"></svg>' for i in range(3)
    )
    html = f"""
    <tr id="1-2-{country}-0" class="datatable-v2_row__x">
      <td>
        <div class="flex !flex-row">{star_svgs}</div>
        <span data-test="flag-{country}"></span>
      </td>
      <td>
        <div class="flex !flex-row">{star_svgs}</div>
      </td>
      <td>
        <a href="https://www.investing.com/economic-calendar/{name.lower()}-1">{name}</a>
        <div class="visible flex md:hidden">
          <span>Act : {act}</span> <span>Cons : {cons}</span> <span>Prev. : {prev}</span>
        </div>
      </td>
    </tr>
    """
    return BeautifulSoup(html, "html.parser").find("tr")


def test_star_count_only_counts_first_three():
    row = _row_html(stars=3, country="US", name="CPI", act="3.5%")
    assert _star_count(row) == 3


def test_star_count_partial():
    row = _row_html(stars=1, country="US", name="Trade Balance", act="1.0B")
    assert _star_count(row) == 1


def test_parse_row_high_with_actual():
    row = _row_html(stars=3, country="US", name="Core CPI (MoM) (Jun)", act="0.3%")
    item = _parse_row(row, "2026-07-14")
    assert item == {
        "event_date": "2026-07-14", "country": "US",
        "event_name": "Core CPI (MoM) (Jun)", "actual": "0.3%",
    }


def test_parse_row_skips_non_high():
    row = _row_html(stars=2, country="US", name="Retail Sales", act="0.5%")
    assert _parse_row(row, "2026-07-14") is None


def test_parse_row_skips_empty_actual():
    row = _row_html(stars=3, country="US", name="CPI (YoY)", act="--")
    assert _parse_row(row, "2026-07-14") is None


def test_page_event_date_parses_weekday_format():
    soup = BeautifulSoup(
        '<div class="py-4 text-center font-semibold">Tuesday, July 14, 2026</div>',
        "html.parser",
    )
    assert _page_event_date(soup) == "2026-07-14"


def test_page_event_date_none_when_missing():
    soup = BeautifulSoup("<div>tidak ada tanggal di sini</div>", "html.parser")
    assert _page_event_date(soup) is None


@pytest.fixture(scope="module")
def live_result():
    return fetch_investing_actuals()


def test_live_returns_dict_with_items_and_flags(live_result):
    assert isinstance(live_result, dict)
    assert "items" in live_result
    assert "source_flags" in live_result
    assert "investing_calendar_actual" in live_result["source_flags"]


def test_live_no_crash_on_failure(live_result):
    # tidak boleh melempar; kalau investing.com block/rate-limit, items
    # kosong dan source_flags mencatat fail -- bukan exception.
    assert isinstance(live_result["items"], list)


def test_live_items_are_all_high_with_actual(live_result):
    if not live_result["items"]:
        pytest.skip("tidak ada item (investing.com unreachable/rate-limited saat test)")
    for it in live_result["items"]:
        assert it["actual"]
        assert it["country"]
        assert it["event_name"]
        assert len(it["event_date"]) == 10
