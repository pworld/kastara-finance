"""S&R zone detector (Phase B) — swing high/low, clustering, touch count.

Keputusan yang dikunci di plan_b.txt §7 (review Giel):
  §7.1 Swing point lookback SIMETRIS (window [i-20, i+20]) — titik baru
       terkonfirmasi 20 hari SETELAHNYA (lag alami), lebih akurat untuk
       review pagi (bukan real-time trading).
  §7.3 Zona dengan touch_count < 2 TETAP disimpan (is_active=0) — histori
       zona kandidat berguna buat riset/tuning nanti.
  §7.4 Natural key UPSERT: bucket relatif (grid log-scale) berbasis
       tolerance clustering yang sama (0.5%) — supaya re-run yang
       menggeser batas zona sedikit (data baru masuk) tetap dianggap
       zona yang SAMA. Fungsi `zone_bucket_key()` di bawah; pemakaian
       aktual (cari zona existing utk UPDATE) ada di pipeline/run_analysis.py.

Modul ini PURE (tidak baca/tulis DB) — supaya gampang ditest dengan data
sintetis. Baca dari DB + tulis (UPSERT) ada di pipeline/run_analysis.py.
"""
from __future__ import annotations

import math
from typing import Any

SWING_LOOKBACK = 20
CLUSTER_TOLERANCE = 0.005  # ±0.5%
MIN_TOUCH_COUNT = 2


def find_swing_points(highs: list[float], lows: list[float], lookback: int = SWING_LOOKBACK) -> list[dict[str, Any]]:
    """Titik i adalah swing high kalau high[i] adalah MAX di window
    [i-lookback, i+lookback] (simetris — lihat plan_b.txt §7.1); swing low
    analog pakai MIN. Return list {'index', 'price', 'kind': 'high'|'low'}.
    """
    n = len(highs)
    points: list[dict[str, Any]] = []
    for i in range(n):
        lo = max(0, i - lookback)
        hi = min(n, i + lookback + 1)
        if highs[i] == max(highs[lo:hi]):
            points.append({"index": i, "price": highs[i], "kind": "high"})
        if lows[i] == min(lows[lo:hi]):
            points.append({"index": i, "price": lows[i], "kind": "low"})
    return points


def cluster_points(points: list[dict[str, Any]], tolerance: float = CLUSTER_TOLERANCE) -> list[list[dict[str, Any]]]:
    """Kelompokkan swing point yang harganya dalam `tolerance` relatif satu
    sama lain jadi 1 cluster. Dibandingkan ke harga PALING RENDAH di cluster
    (bukan titik terakhir yang masuk) supaya cluster tidak "creep"/melebar
    tanpa batas lewat rantai perbandingan berturut-turut.
    """
    if not points:
        return []
    sorted_points = sorted(points, key=lambda p: p["price"])
    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [sorted_points[0]]
    for p in sorted_points[1:]:
        cluster_min = min(pt["price"] for pt in current)
        if (p["price"] - cluster_min) / cluster_min <= tolerance:
            current.append(p)
        else:
            clusters.append(current)
            current = [p]
    clusters.append(current)
    return clusters


def find_touches(
    zone_lower: float, zone_upper: float,
    dates: list[str], highs: list[float], lows: list[float], closes: list[float],
) -> list[dict[str, Any]]:
    """Cari episode 'sentuhan' harga ke zona (candle low/high overlap zona).
    Episode berturut-turut (harga tetap di dalam zona beberapa hari) dihitung
    SEKALI, bukan per-hari. Tiap touch dicatat arah pendekatannya
    (support = dari atas, resistance = dari bawah) berdasar close candle
    SEBELUM masuk zona — dipakai buat vote zone_type mayoritas.
    """
    touches: list[dict[str, Any]] = []
    in_zone = False
    for i in range(len(dates)):
        touching = lows[i] <= zone_upper and highs[i] >= zone_lower
        if touching and not in_zone:
            direction = None
            if i > 0:
                if closes[i - 1] > zone_upper:
                    direction = "support"
                elif closes[i - 1] < zone_lower:
                    direction = "resistance"
            touches.append({"date": dates[i], "direction": direction})
            in_zone = True
        elif not touching:
            in_zone = False
    return touches


def detect_zones(
    dates: list[str], highs: list[float], lows: list[float], closes: list[float],
    lookback: int = SWING_LOOKBACK, tolerance: float = CLUSTER_TOLERANCE,
) -> list[dict[str, Any]]:
    """Pipeline penuh (pure, tanpa DB): swing points -> cluster -> zona.

    Return list of dict siap di-UPSERT ke sr_zones:
      zone_lower, zone_upper, touch_count, zone_type, first_seen,
      last_touched, is_active (0/1 -- touch_count < MIN_TOUCH_COUNT = 0,
      TETAP masuk list ini, bukan dibuang -- plan_b.txt §7.3).
    """
    swing_points = find_swing_points(highs, lows, lookback)
    if not swing_points:
        return []

    zones: list[dict[str, Any]] = []
    for cluster in cluster_points(swing_points, tolerance):
        prices = [p["price"] for p in cluster]
        zone_lower, zone_upper = min(prices), max(prices)
        touches = find_touches(zone_lower, zone_upper, dates, highs, lows, closes)
        if not touches:
            continue  # tidak seharusnya terjadi (titik cluster sendiri = touch), guard aja

        support_votes = sum(1 for t in touches if t["direction"] == "support")
        resistance_votes = sum(1 for t in touches if t["direction"] == "resistance")
        zone_type = "SUPPORT" if support_votes >= resistance_votes else "RESISTANCE"

        zones.append({
            "zone_lower": zone_lower,
            "zone_upper": zone_upper,
            "touch_count": len(touches),
            "zone_type": zone_type,
            "first_seen": touches[0]["date"],
            "last_touched": touches[-1]["date"],
            "is_active": 1 if len(touches) >= MIN_TOUCH_COUNT else 0,
        })
    return zones


def zone_bucket_key(zone_type: str, zone_lower: float, zone_upper: float, tolerance: float = CLUSTER_TOLERANCE) -> str:
    """Natural key stabil untuk UPSERT (plan_b.txt §7.4) — snap midpoint zona
    ke grid relatif (log-scale, step ~`tolerance`) supaya zona yang sama
    tetap ke-match walau zone_lower/zone_upper geser dikit antar-run.
    """
    midpoint = (zone_lower + zone_upper) / 2
    bucket = round(math.log(midpoint) / math.log(1 + tolerance))
    return f"{zone_type}:{bucket}"
