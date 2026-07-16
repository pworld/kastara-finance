"""Rakit teks Daily Briefing Telegram (Phase E, plan_e.txt) — format PERSIS
Master Plan §8.

Pure function, tidak menyentuh Telegram sama sekali (kirim = `notify.
telegram.send_message`, terpisah supaya testable tanpa network). Mesin
CUMA merakit teks dari data yang SUDAH Giel isi manual (4 lensa, approve
sinyal) — tidak generate/menyimpulkan apa pun sendiri.
"""
from __future__ import annotations

import sqlite3

READING_LENSES = ("GEMA", "LEON", "AKELA", "RIVAN")


def _fmt_num(v: float | int | None, decimals: int = 2) -> str:
    if v is None:
        return "n/a"
    return f"{v:,.{decimals}f}"


def _btc_pct_change(conn: sqlite3.Connection, date: str) -> float | None:
    rows = conn.execute(
        "SELECT close FROM asset_ohlcv WHERE instrument='BTC' AND date <= ? "
        "ORDER BY date DESC LIMIT 2",
        (date,),
    ).fetchall()
    if len(rows) < 2 or not rows[1]["close"]:
        return None
    cur, prev = rows[0]["close"], rows[1]["close"]
    return (cur - prev) / prev * 100


def compose_daily_briefing(conn: sqlite3.Connection, date: str) -> str:
    market = conn.execute(
        "SELECT btc_close, dxy_close, fear_greed_value, fear_greed_label "
        "FROM daily_market WHERE date = ?", (date,),
    ).fetchone()

    btc_close = market["btc_close"] if market else None
    dxy_close = market["dxy_close"] if market else None
    fg_value = market["fear_greed_value"] if market else None
    fg_label = market["fear_greed_label"] if market else None
    pct = _btc_pct_change(conn, date)

    fg_str = f"{fg_value} · {fg_label}" if fg_value is not None else "n/a"
    pct_str = f"({'+' if pct >= 0 else ''}{pct:.1f}%)" if pct is not None else ""
    snapshot = (
        f"BTC: ${_fmt_num(btc_close)} {pct_str} | DXY: {_fmt_num(dxy_close)} | F&G: {fg_str}"
    ).strip()

    key_events = conn.execute(
        "SELECT headline FROM daily_news WHERE date = ? AND for_reading = 1 "
        "ORDER BY id", (date,),
    ).fetchall()

    lens_rows = conn.execute(
        "SELECT lens, notes FROM reading_workspace WHERE date = ? AND lens IN "
        "('GEMA','LEON','AKELA','RIVAN')", (date,),
    ).fetchall()
    lens_notes = {r["lens"]: r["notes"] for r in lens_rows}

    signals = conn.execute(
        "SELECT instrument, signal_type, entry_price, sl_price, tp1_price, rr_ratio "
        "FROM trade_signals WHERE date = ? AND approved = 1 ORDER BY id", (date,),
    ).fetchall()

    lines = [f"🔷 KASTARA FINANCE · {date}", ""]

    lines.append("📊 MARKET SNAPSHOT")
    lines.append(snapshot)
    lines.append("")

    if key_events:
        lines.append("📰 KEY EVENTS")
        for r in key_events:
            lines.append(f"- {r['headline']}")
        lines.append("")

    lines.append("🧠 4 LENSA (ditulis Giel)")
    for lens in READING_LENSES:
        note = lens_notes.get(lens)
        lines.append(f"{lens}: {note if note else '(belum diisi)'}")
    lines.append("")

    lines.append("📈 SIGNAL")
    if signals:
        for s in signals:
            rr = f"{s['rr_ratio']:.2f}" if s["rr_ratio"] is not None else "n/a"
            lines.append(
                f"{s['instrument']} {s['signal_type']} — entry {_fmt_num(s['entry_price'])} / "
                f"SL {_fmt_num(s['sl_price'])} / TP1 {_fmt_num(s['tp1_price'])} / R:R {rr}"
            )
    else:
        lines.append("(belum diisi)")
    lines.append("")

    lines.append("⚠️ Ini bukan rekomendasi finansial.")
    lines.append("Keputusan ada di tangan kamu.")

    return "\n".join(lines)
