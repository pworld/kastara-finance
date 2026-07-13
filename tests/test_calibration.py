"""Test analysis/calibration.py — kalibrasi per-market (Phase J+ Build
Contract v1.3 §13, J-3)."""
import pytest

from analysis.calibration import idx_price_fraction, idx_zone_tolerance_pct


def test_idx_price_fraction_tiers():
    """Peraturan Nomor II-A BEI (dikonfirmasi riset publik), bukan tebakan."""
    assert idx_price_fraction(150) == 1
    assert idx_price_fraction(199.99) == 1
    assert idx_price_fraction(200) == 2
    assert idx_price_fraction(499) == 2
    assert idx_price_fraction(500) == 5
    assert idx_price_fraction(1999) == 5
    assert idx_price_fraction(2000) == 10
    assert idx_price_fraction(4999) == 10
    assert idx_price_fraction(5000) == 25
    assert idx_price_fraction(6175) == 25  # harga BBCA nyata (2026-07-10)


def test_idx_zone_tolerance_pct_bbca_price_range():
    # BBCA ~Rp6000-8000 -> fraksi 25, 2 ticks = Rp50
    pct = idx_zone_tolerance_pct(6175)
    assert pct == pytest.approx(50 / 6175)
    # sedikit lebih lebar dari default BTC 0.5% -- diharapkan, bukan bug
    assert pct > 0.005


def test_idx_zone_tolerance_pct_scales_with_ticks_param():
    tight = idx_zone_tolerance_pct(6175, ticks=1)
    wide = idx_zone_tolerance_pct(6175, ticks=4)
    assert wide == pytest.approx(tight * 4)


def test_idx_zone_tolerance_pct_rejects_non_positive_price():
    with pytest.raises(ValueError):
        idx_zone_tolerance_pct(0)
