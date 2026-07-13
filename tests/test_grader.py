"""Test analysis/grader.py — Emiten Grader engine, DRAFT v1 (Phase J+
Build Contract v1.3, Master Plan §12)."""
from analysis.grader import (
    compute_fund_score,
    compute_integrity_flags,
    compute_quadrant,
    grade_emiten,
)


def _bank_quarter(**overrides):
    base = {
        "revenue": 28_000_000_000_000.0, "net_income": 14_000_000_000_000.0,
        "net_interest_income": 21_000_000_000_000.0, "total_equity": 200_000_000_000_000.0,
        "confidence": "LOW_CONFIDENCE",
    }
    base.update(overrides)
    return base


def _corp_quarter(**overrides):
    base = {
        "revenue": 22_000_000_000.0, "net_income": 500_000_000.0,
        "operating_cash_flow": 3_000_000_000.0, "free_cash_flow": 1_000_000_000.0,
        "confidence": "LOW_CONFIDENCE",
    }
    base.update(overrides)
    return base


def test_bank_fund_score_full_marks():
    score = compute_fund_score(_bank_quarter(), is_financial=True)
    assert score == 100.0


def test_bank_fund_score_penalizes_negative_income():
    score = compute_fund_score(_bank_quarter(net_income=-1.0), is_financial=True)
    assert score == 50.0  # nii positive + equity positive tetap dapat poin, net_income & margin hilang


def test_corp_fund_score_full_marks():
    score = compute_fund_score(_corp_quarter(), is_financial=False)
    assert score == 100.0


def test_corp_fund_score_zero_when_all_negative():
    score = compute_fund_score(
        _corp_quarter(revenue=-1.0, net_income=-500_000_000.0,
                      operating_cash_flow=-1.0, free_cash_flow=-1.0),
        is_financial=False,
    )
    assert score == 0.0


def test_corp_fund_score_revenue_always_counted_if_positive():
    score = compute_fund_score(
        _corp_quarter(net_income=-1.0, operating_cash_flow=-1.0, free_cash_flow=-1.0),
        is_financial=False,
    )
    assert score == 25.0  # cuma revenue yang positif


def test_integrity_flags_low_confidence():
    flags = compute_integrity_flags(_corp_quarter(), uma_active=False)
    assert flags == ["LOW_CONFIDENCE_FUNDAMENTALS"]


def test_integrity_flags_uma_active():
    flags = compute_integrity_flags(_corp_quarter(confidence="FULL"), uma_active=True)
    assert flags == ["UMA_ACTIVE"]


def test_integrity_flags_negative_net_income_and_equity():
    flags = compute_integrity_flags(
        _bank_quarter(confidence="FULL", net_income=-1.0, total_equity=-1.0), uma_active=False,
    )
    assert "NEGATIVE_NET_INCOME" in flags
    assert "NEGATIVE_EQUITY" in flags


def test_integrity_flags_extra_flags_passthrough():
    flags = compute_integrity_flags(None, uma_active=False, extra_flags=["MANUAL_SUSPENSION_FLAG"])
    assert flags == ["MANUAL_SUSPENSION_FLAG"]


def test_quadrant_red_flag_always_avoid_regardless_of_score():
    """Kontrak §16: grader adalah REM, bukan stempel -- RED veto kuadran
    apa pun skornya."""
    assert compute_quadrant(100.0, ["UMA_ACTIVE"]) == "AVOID"
    assert compute_quadrant(0.0, ["NEGATIVE_EQUITY"]) == "AVOID"


def test_quadrant_investable_high_score_no_flags():
    assert compute_quadrant(75.0, []) == "INVESTABLE"


def test_quadrant_watch_high_score_with_orange_flag():
    assert compute_quadrant(75.0, ["LOW_CONFIDENCE_FUNDAMENTALS"]) == "WATCH"


def test_quadrant_watch_mid_score():
    assert compute_quadrant(50.0, []) == "WATCH"


def test_quadrant_speculative_low_score():
    assert compute_quadrant(25.0, []) == "SPECULATIVE"


def test_grade_emiten_no_fundamentals_data_is_speculative_not_avoid():
    """Data kosong (belum ada fundamentals) BEDA dari red flag aktif --
    tidak boleh disamakan jadi AVOID."""
    result = grade_emiten(None, is_financial=False, uma_active=False)
    assert result["fund_score"] == 0.0
    assert result["quadrant"] == "SPECULATIVE"


def test_grade_emiten_full_pipeline_bank():
    result = grade_emiten(_bank_quarter(confidence="FULL"), is_financial=True, uma_active=False)
    assert result["fund_score"] == 100.0
    assert result["integrity_flags"] == []
    assert result["quadrant"] == "INVESTABLE"
