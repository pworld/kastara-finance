"""Test analysis/signals.py — data sintetis, verifikasi R:R math dan aturan
breakout/retest dari Master Plan §3.
"""
import pytest

from analysis.signals import MIN_RR, SL_BUFFER, detect_signals


def _zone(lower, upper, active=1):
    return {"zone_lower": lower, "zone_upper": upper, "zone_type": "RESISTANCE", "is_active": active}


def test_breakout_then_retest_full_sequence():
    zones = [_zone(100.0, 102.0), _zone(115.0, 117.0)]
    dates = ["d0", "d1", "d2"]
    closes = [95.0, 103.0, 101.0]
    highs = closes[:]
    lows = closes[:]
    volumes = [100.0, 200.0, 90.0]      # d1 ratio=2.0 (breakout), d2 ratio=0.9 (hadir)
    volume_mas = [100.0, 100.0, 100.0]

    signals = detect_signals(dates, closes, highs, lows, volumes, volume_mas, zones)

    breakouts = [s for s in signals if s["signal_type"] == "BREAKOUT"]
    retests = [s for s in signals if s["signal_type"] == "RETEST"]
    assert len(breakouts) == 1
    assert breakouts[0]["date"] == "d1"
    assert breakouts[0]["entry_price"] is None  # belum entry, baru breakout

    assert len(retests) == 1
    r = retests[0]
    assert r["date"] == "d2"
    assert r["entry_price"] == 101.0
    assert r["sl_price"] == pytest.approx(100.0 * (1 - SL_BUFFER))
    assert r["tp1_price"] == 115.0  # resistance aktif terdekat di atas entry
    expected_rr = (115.0 - 101.0) / (101.0 - 100.0 * (1 - SL_BUFFER))
    assert r["rr_ratio"] == pytest.approx(expected_rr)
    assert r["is_valid"] == 1  # rr > MIN_RR
    assert r["volume_confirmed"] == 1


def test_low_rr_marked_invalid_but_still_recorded():
    # TP1 dekat -> R:R < 1.5, TAPI row TETAP di-return (plan_b.txt §3.3:
    # bukan silent-drop), is_valid=0.
    zones = [_zone(100.0, 102.0), _zone(103.0, 104.0)]
    dates = ["d0", "d1", "d2"]
    closes = [95.0, 103.5, 101.0]
    highs = closes[:]
    lows = closes[:]
    volumes = [100.0, 200.0, 90.0]
    volume_mas = [100.0, 100.0, 100.0]

    signals = detect_signals(dates, closes, highs, lows, volumes, volume_mas, zones)
    retests = [s for s in signals if s["signal_type"] == "RETEST"]
    assert len(retests) == 1
    r = retests[0]
    assert r["rr_ratio"] is not None
    assert r["rr_ratio"] < MIN_RR
    assert r["is_valid"] == 0


def test_breakout_without_retest_yet_only_one_signal():
    zones = [_zone(100.0, 102.0)]
    dates = ["d0", "d1", "d2"]
    closes = [95.0, 103.0, 104.0]  # breakout lalu lanjut naik, tidak pernah retest
    highs = closes[:]
    lows = closes[:]
    volumes = [100.0, 200.0, 200.0]
    volume_mas = [100.0, 100.0, 100.0]

    signals = detect_signals(dates, closes, highs, lows, volumes, volume_mas, zones)
    assert len(signals) == 1
    assert signals[0]["signal_type"] == "BREAKOUT"


def test_no_breakout_without_volume_confirmation():
    zones = [_zone(100.0, 102.0)]
    dates = ["d0", "d1"]
    closes = [95.0, 103.0]  # close di atas resistance TAPI volume TIDAK breakout
    highs = closes[:]
    lows = closes[:]
    volumes = [100.0, 110.0]     # ratio 1.1, tidak > 1.5
    volume_mas = [100.0, 100.0]

    signals = detect_signals(dates, closes, highs, lows, volumes, volume_mas, zones)
    assert signals == []


def test_no_tp1_available_rr_none_still_recorded():
    # Cuma 1 zona resistance (yang ditembus) -> tidak ada TP1 di atasnya.
    zones = [_zone(100.0, 102.0)]
    dates = ["d0", "d1", "d2"]
    closes = [95.0, 103.0, 101.0]
    highs = closes[:]
    lows = closes[:]
    volumes = [100.0, 200.0, 90.0]
    volume_mas = [100.0, 100.0, 100.0]

    signals = detect_signals(dates, closes, highs, lows, volumes, volume_mas, zones)
    retests = [s for s in signals if s["signal_type"] == "RETEST"]
    assert len(retests) == 1
    assert retests[0]["tp1_price"] is None
    assert retests[0]["rr_ratio"] is None
    assert retests[0]["is_valid"] == 0


def test_ignores_inactive_zones():
    zones = [_zone(100.0, 102.0, active=0)]
    dates = ["d0", "d1"]
    closes = [95.0, 103.0]
    highs = closes[:]
    lows = closes[:]
    volumes = [100.0, 200.0]
    volume_mas = [100.0, 100.0]

    assert detect_signals(dates, closes, highs, lows, volumes, volume_mas, zones) == []


def test_empty_zones_returns_empty():
    assert detect_signals([], [], [], [], [], [], []) == []


def test_signal_dict_never_contains_giel_approved_key():
    # Modul ini PURE, tidak pernah set giel_approved -- itu urusan
    # pipeline/run_analysis.py saat INSERT (hardcode 0, lihat regression
    # test di test_run_analysis.py). Guard di sini: key itu memang tidak
    # ada sama sekali di output modul ini (desain lebih ketat dari sekadar
    # "selalu 0").
    zones = [_zone(100.0, 102.0)]
    dates = ["d0", "d1"]
    closes = [95.0, 103.0]
    highs = closes[:]
    lows = closes[:]
    volumes = [100.0, 200.0]
    volume_mas = [100.0, 100.0]
    signals = detect_signals(dates, closes, highs, lows, volumes, volume_mas, zones)
    for s in signals:
        assert "giel_approved" not in s
