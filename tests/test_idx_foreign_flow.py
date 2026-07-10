"""Test IDX foreign flow scraper. Butuh network (live API + Cloudflare bypass
lewat curl_cffi). Pola sama tests/test_crypto.py -- live, bukan mock."""
import pytest

from scrapers.idx_foreign_flow import fetch_idx_foreign_flow

EXPECTED_METRICS = {
    "ihsg_ff_foreign_foreign", "ihsg_ff_foreign_domestic",
    "ihsg_ff_domestic_foreign", "foreign_net_buy_value",
}


@pytest.fixture(scope="module")
def flow():
    # Bulan yang sudah lengkap (bukan bulan berjalan -- data hari ini sering
    # belum terbit saat pipeline jalan, lihat catatan di scraper).
    return fetch_idx_foreign_flow("2026-06-15")


def test_returns_dict_with_items_and_flags(flow):
    assert isinstance(flow, dict)
    assert "items" in flow
    assert "source_flags" in flow
    assert isinstance(flow["source_flags"], dict)


def test_no_crash_on_failure(flow):
    # tidak boleh melempar; kalau Cloudflare/network gagal, items kosong
    # dan source_flags mencatat fail -- bukan exception.
    assert isinstance(flow["items"], list)


def test_items_have_expected_shape(flow):
    if not flow["items"]:
        pytest.skip("tidak ada item (IDX/Cloudflare unreachable saat test)")
    for item in flow["items"]:
        assert item["instrument"] == "IHSG"
        assert item["metric"] in EXPECTED_METRICS
        assert isinstance(item["value"], (int, float))
        assert item["source"] == "idx_digital_statistic"


def test_all_four_metrics_present_per_date(flow):
    if not flow["items"]:
        pytest.skip("tidak ada item (IDX/Cloudflare unreachable saat test)")
    by_date: dict[str, set[str]] = {}
    for item in flow["items"]:
        by_date.setdefault(item["date"], set()).add(item["metric"])
    # setidaknya 1 tanggal punya ke-4 metric lengkap (F2F/F2D/D2F/net)
    assert any(EXPECTED_METRICS.issubset(metrics) for metrics in by_date.values())


def test_net_buy_formula_correct(flow):
    """Foreign Net Buy = domesticForeign (D2F) - foreignDomestic (F2D) --
    koreksi eksplisit atas library referensi yang salah baca field ini."""
    if not flow["items"]:
        pytest.skip("tidak ada item (IDX/Cloudflare unreachable saat test)")
    by_date_metric = {(it["date"], it["metric"]): it["value"] for it in flow["items"]}
    checked = 0
    for date, metric in list(by_date_metric):
        if metric != "foreign_net_buy_value":
            continue
        f2d = by_date_metric.get((date, "ihsg_ff_foreign_domestic"))
        d2f = by_date_metric.get((date, "ihsg_ff_domestic_foreign"))
        if f2d is None or d2f is None:
            continue
        assert by_date_metric[(date, metric)] == pytest.approx(d2f - f2d)
        checked += 1
    assert checked > 0
