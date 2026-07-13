"""Test scrapers/idx_stock_foreign_flow.py (Phase J+ Build Contract v1.3, J-8)."""
import pytest

from scrapers.idx_stock_foreign_flow import fetch_idx_stock_foreign_flow


@pytest.fixture(scope="module")
def bbca_flow():
    return fetch_idx_stock_foreign_flow(["BBCA"])


def test_returns_structure(bbca_flow):
    assert "items" in bbca_flow
    assert "source_flags" in bbca_flow


def test_empty_tickers_returns_empty_without_network_call():
    out = fetch_idx_stock_foreign_flow([])
    assert out == {"items": [], "source_flags": {}}


def test_bbca_items_have_all_3_metrics(bbca_flow):
    """Live network -- pola sama scraper lain di project ini."""
    items = bbca_flow["items"]
    if items:
        metrics = {i["metric"] for i in items if i["instrument"] == "BBCA"}
        assert metrics == {"stock_ff_foreign_buy_vol", "stock_ff_foreign_sell_vol", "stock_ff_foreign_net_vol"}


def test_net_equals_buy_minus_sell(bbca_flow):
    by_metric = {i["metric"]: i["value"] for i in bbca_flow["items"] if i["instrument"] == "BBCA"}
    if by_metric:
        assert by_metric["stock_ff_foreign_net_vol"] == (
            by_metric["stock_ff_foreign_buy_vol"] - by_metric["stock_ff_foreign_sell_vol"]
        )


def test_ticker_not_requested_is_excluded():
    out = fetch_idx_stock_foreign_flow(["ZZZZNOTAREALTICKER"])
    assert out["items"] == []
