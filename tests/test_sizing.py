"""Test analysis/sizing.py — sizing & lot quantization (Phase J+ Build
Contract v1.3 §14)."""
import pytest

from analysis.sizing import MAX_RISK_PCT, suggest_position_size


def test_max_risk_pct_is_2_5():
    """Keputusan eksplisit Giel (13 Jul 2026) -- regression guard supaya
    tidak diam-diam berubah."""
    assert MAX_RISK_PCT == 2.5


def test_idx_lot_rounds_down_never_up():
    # capital 100jt, risk 2.5% = 2.5jt budget. entry-SL jarak 1000/lembar.
    # ideal = 2500 lembar -> lot 100 -> floor(2500/100)*100 = 2500 (pas kelipatan)
    result = suggest_position_size(entry_price=6000, sl_price=5000, capital=100_000_000, lot_size=100)
    assert result["skip"] is False
    assert result["suggested_units"] == 2500
    assert result["suggested_units"] % 100 == 0
    assert result["actual_risk"] <= result["risk_budget"]


def test_idx_lot_rounds_down_when_not_exact_multiple():
    # ideal units = 2.5jt / 900 = 2777.78 -> floor ke kelipatan 100 -> 2700
    result = suggest_position_size(entry_price=6000, sl_price=5100, capital=100_000_000, lot_size=100)
    assert result["suggested_units"] == 2700
    # risiko aktual harus <= budget, TIDAK PERNAH melebihi (kontrak §14 poin 1)
    assert result["actual_risk"] <= result["risk_budget"]


def test_risk_capacity_exceeded_when_budget_below_1_lot():
    # capital kecil, jarak entry-SL besar -> ideal units < 1 lot -> SKIP
    result = suggest_position_size(entry_price=6000, sl_price=1000, capital=1_000_000, lot_size=100)
    assert result["skip"] is True
    assert result["skip_reason"] == "RISK_CAPACITY_EXCEEDED"
    assert result["suggested_units"] == 0
    assert result["actual_risk"] == 0.0


def test_us_fractional_lot_size_zero_rarely_skips():
    """Kontrak §14 poin 5: dgn IBKR fractional (lot_size<=0), rule
    RISK_CAPACITY_EXCEEDED hampir tidak pernah menyala."""
    result = suggest_position_size(entry_price=400, sl_price=380, capital=10_000, lot_size=0)
    assert result["skip"] is False
    assert result["suggested_units"] > 0
    # fractional -> tidak dibulatkan ke kelipatan apa pun
    assert result["actual_risk"] == pytest.approx(result["risk_budget"], rel=1e-9)


def test_actual_risk_never_exceeds_budget():
    """Kontrak §14 poin 1: risiko aktual <= rencana, tidak pernah sebaliknya."""
    for entry, sl, cap, lot in [
        (6000, 5000, 50_000_000, 100), (400, 350, 25_000, 1),
        (100, 90, 5_000_000, 100), (7500, 7490, 2_000_000, 100),
    ]:
        result = suggest_position_size(entry_price=entry, sl_price=sl, capital=cap, lot_size=lot)
        assert result["actual_risk"] <= result["risk_budget"] + 1e-9


def test_rejects_zero_risk_distance():
    with pytest.raises(ValueError):
        suggest_position_size(entry_price=100, sl_price=100, capital=1_000_000, lot_size=100)


def test_rejects_non_positive_capital():
    with pytest.raises(ValueError):
        suggest_position_size(entry_price=100, sl_price=90, capital=0, lot_size=100)
