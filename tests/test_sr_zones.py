"""Test analysis/sr_zones.py — data SINTETIS (bukan data BTC asli) supaya
swing point/cluster/touch-nya predictable dan gampang di-assert.
"""
from analysis.sr_zones import (
    cluster_points,
    detect_zones,
    find_swing_points,
    find_touches,
    zone_bucket_key,
)


def test_find_swing_points_v_shape():
    # V-shape simetris: turun 100->80 (idx 0-20), naik 80->100 (idx 20-40).
    # window utk idx 20 (lookback=20) = seluruh array -> min global = idx 20.
    n = 41
    prices = [100.0 - i if i <= 20 else 80.0 + (i - 20) for i in range(n)]
    points = find_swing_points(prices, prices, lookback=20)
    lows = [p for p in points if p["kind"] == "low"]
    assert any(p["index"] == 20 and p["price"] == 80.0 for p in lows)


def test_find_swing_points_inverted_v_shape():
    n = 41
    prices = [100.0 + i if i <= 20 else 120.0 - (i - 20) for i in range(n)]
    points = find_swing_points(prices, prices, lookback=20)
    highs = [p for p in points if p["kind"] == "high"]
    assert any(p["index"] == 20 and p["price"] == 120.0 for p in highs)


def test_cluster_points_groups_within_tolerance():
    points = [
        {"index": 0, "price": 100.0, "kind": "low"},
        {"index": 1, "price": 100.3, "kind": "low"},   # 0.3% dari 100 -> gabung
        {"index": 2, "price": 105.0, "kind": "low"},   # 5% dari 100 -> cluster baru
        {"index": 3, "price": 105.2, "kind": "low"},   # 0.19% dari 105 -> gabung
        {"index": 4, "price": 110.0, "kind": "low"},   # 4.76% dari 105 -> cluster baru
    ]
    clusters = cluster_points(points, tolerance=0.005)
    assert len(clusters) == 3
    sizes = sorted(len(c) for c in clusters)
    assert sizes == [1, 2, 2]


def test_cluster_points_no_drift_via_chaining():
    # tiap titik "hampir" dalam toleransi ke tetangga sebelumnya, tapi kalau
    # dibandingkan ke cluster_min (bukan titik terakhir) harusnya kepecah,
    # bukan menyatu jadi 1 cluster raksasa yang creep.
    points = [{"index": i, "price": 100.0 * (1.004 ** i), "kind": "low"} for i in range(10)]
    clusters = cluster_points(points, tolerance=0.005)
    assert len(clusters) > 1


def test_find_touches_counts_episodes_not_days():
    dates = [f"d{i}" for i in range(4)]
    # candle 1-2 sama-sama di dalam zona [95,100] -> 1 episode, bukan 2
    prices = [110.0, 97.0, 96.0, 110.0]
    touches = find_touches(95.0, 100.0, dates, prices, prices, prices)
    assert len(touches) == 1
    assert touches[0]["date"] == "d1"


def test_find_touches_direction_support_and_resistance():
    dates = ["d0", "d1", "d2", "d3", "d4", "d5", "d6"]
    prices = [110.0, 97.0, 96.0, 110.0, 94.0, 97.0, 103.0]
    touches = find_touches(95.0, 100.0, dates, prices, prices, prices)
    assert len(touches) == 2
    assert touches[0]["direction"] == "support"     # datang dari atas (110)
    assert touches[1]["direction"] == "resistance"  # datang dari bawah (94)


def test_detect_zones_finds_double_bottom_support():
    # Dua dip harus berjarak > 2*lookback supaya window swing-detection
    # masing-masing (±20) tidak saling overlap/interferensi satu sama lain
    # (kalau overlap, dip yang lebih tinggi gagal lolos cek "min di window
    # sendiri" karena dip yang lebih rendah ikut masuk window-nya).
    n = 90
    prices = [150.0] * n
    prices[15] = 100.0
    prices[60] = 100.2
    dates = [f"d{i}" for i in range(n)]

    zones = detect_zones(dates, prices, prices, prices)
    matching = [z for z in zones if z["zone_lower"] <= 100.2 and z["zone_upper"] >= 100.0]
    assert len(matching) == 1
    zone = matching[0]
    assert zone["zone_type"] == "SUPPORT"
    assert zone["touch_count"] == 2
    assert zone["is_active"] == 1
    assert zone["first_seen"] == "d15"
    assert zone["last_touched"] == "d60"


def test_detect_zones_single_touch_marked_inactive():
    n = 45
    prices = [150.0] * n
    prices[20] = 100.0
    dates = [f"d{i}" for i in range(n)]

    zones = detect_zones(dates, prices, prices, prices)
    matching = [z for z in zones if 99.9 <= z["zone_lower"] <= 100.1]
    assert len(matching) == 1
    zone = matching[0]
    assert zone["touch_count"] == 1
    assert zone["is_active"] == 0  # < MIN_TOUCH_COUNT tapi TETAP disimpan (plan_b.txt §7.3)


def test_detect_zones_empty_data():
    assert detect_zones([], [], [], []) == []


def test_zone_bucket_key_stable_for_small_shift():
    k1 = zone_bucket_key("SUPPORT", 100.0, 100.2)
    k2 = zone_bucket_key("SUPPORT", 100.05, 100.25)
    assert k1 == k2


def test_zone_bucket_key_differs_for_distant_zones():
    k1 = zone_bucket_key("SUPPORT", 100.0, 100.2)
    k2 = zone_bucket_key("SUPPORT", 150.0, 150.3)
    assert k1 != k2


def test_zone_bucket_key_differs_by_type():
    k1 = zone_bucket_key("SUPPORT", 100.0, 100.2)
    k2 = zone_bucket_key("RESISTANCE", 100.0, 100.2)
    assert k1 != k2
