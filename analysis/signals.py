"""Breakout + retest signal detector + R:R calculator (Phase B).

Aturan dari Master Plan §3 "Entry Rules" (semua harus terpenuhi):
  1. S&R valid (dari analysis/sr_zones.py, zone_type=RESISTANCE, is_active)
  2. BREAKOUT: daily close > zone_upper + volume > MA (is_breakout_volume)
  3. RETEST: harga balik ke zona (bekas resistance) + close > zone_lower
     (konfirmasi) + volume hadir/tidak sepi (is_volume_present, >=80%)
  4. ENTRY = close candle retest konfirmasi
  5. SL = di bawah zone_lower (buffer kecil, lihat SL_BUFFER di bawah)
  6. TP1 = resistance aktif terdekat berikutnya di atas entry; R:R dihitung;
     minimum 1:1.5 -- kalau kurang, TETAP disimpan is_valid=0 (bukan
     silent-drop, plan_b.txt §3.3)

Keputusan yang dikunci di plan_b.txt §7 (review Giel):
  §7.5 Breakout tanpa retest disimpan sebagai row trade_signals TERPISAH
       (signal_type=BREAKOUT, kolom harga NULL) -- state "menunggu retest"
       hidup di DB (dicek ulang tiap run oleh pipeline/run_analysis.py),
       BUKAN di memory/state proses.

Modul ini PURE (tidak baca/tulis DB) -- baca histori + zona aktif, keluarkan
list event sinyal. Baca dari DB + tulis (INSERT, dedup by pipeline) ada di
pipeline/run_analysis.py.
"""
from __future__ import annotations

from typing import Any

from analysis.indicators import is_breakout_volume, is_volume_present, volume_ratio

MIN_RR = 1.5

# SL_BUFFER: seberapa jauh SL diletakkan DI BAWAH zone_lower. Tidak ada
# angka eksplisit di Master Plan untuk ini -- dipilih konsisten dengan
# CLUSTER_TOLERANCE (0.5%) di analysis/sr_zones.py supaya tidak menambah
# "angka ajaib" baru tanpa alasan. Bisa disesuaikan kalau Giel mau beda.
SL_BUFFER = 0.005


def _next_resistance_above(zones: list[dict[str, Any]], price: float, exclude: dict[str, Any]) -> float | None:
    """Cari zone_lower RESISTANCE aktif TERDEKAT di atas `price` (buat TP1),
    tidak termasuk `exclude` (zona yang baru saja ditembus)."""
    candidates = [z["zone_lower"] for z in zones if z is not exclude and z["zone_lower"] > price]
    return min(candidates) if candidates else None


def detect_signals(
    dates: list[str], closes: list[float], highs: list[float], lows: list[float],
    volumes: list[float | None], volume_mas: list[float | None],
    zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deteksi SEMUA event breakout/retest sepanjang histori untuk zona aktif
    yang diberikan. Return list dict siap di-INSERT ke trade_signals (tanpa
    `instrument`/`giel_approved`/`created_at` -- itu urusan orchestrator).

    Deterministik: input sama -> output sama persis, tiap kali dipanggil.
    Dedup terhadap yang sudah ada di DB itu tanggung jawab orchestrator.
    """
    resistance_zones = [z for z in zones if z["zone_type"] == "RESISTANCE" and z["is_active"]]
    if not resistance_zones:
        return []

    signals: list[dict[str, Any]] = []

    for zone in resistance_zones:
        pending_breakout = False
        for i in range(len(dates)):
            ratio = volume_ratio(volumes[i], volume_mas[i])

            if not pending_breakout:
                if closes[i] > zone["zone_upper"] and is_breakout_volume(ratio):
                    signals.append({
                        "date": dates[i], "signal_type": "BREAKOUT",
                        "zone_lower": zone["zone_lower"], "zone_upper": zone["zone_upper"],
                        "entry_price": None, "sl_price": None,
                        "tp1_price": None, "tp2_price": None, "rr_ratio": None,
                        "volume_confirmed": 1, "is_valid": None,
                    })
                    pending_breakout = True
                continue

            # sudah breakout, tunggu RETEST: harga balik masuk zona (bekas
            # resistance, sekarang berperan support) + close > zone_lower
            touching = lows[i] <= zone["zone_upper"] and highs[i] >= zone["zone_lower"]
            if touching and closes[i] > zone["zone_lower"]:
                volume_present = is_volume_present(ratio)
                entry_price = closes[i]
                sl_price = zone["zone_lower"] * (1 - SL_BUFFER)
                tp1_price = _next_resistance_above(resistance_zones, entry_price, zone)

                rr_ratio = None
                if tp1_price is not None and entry_price > sl_price:
                    rr_ratio = (tp1_price - entry_price) / (entry_price - sl_price)
                is_valid = 1 if (rr_ratio is not None and rr_ratio >= MIN_RR) else 0

                signals.append({
                    "date": dates[i], "signal_type": "RETEST",
                    "zone_lower": zone["zone_lower"], "zone_upper": zone["zone_upper"],
                    "entry_price": entry_price, "sl_price": sl_price,
                    "tp1_price": tp1_price, "tp2_price": None, "rr_ratio": rr_ratio,
                    "volume_confirmed": 1 if volume_present else 0, "is_valid": is_valid,
                })
                pending_breakout = False  # boleh breakout lagi nanti di zona yang sama

    signals.sort(key=lambda s: s["date"])
    return signals
