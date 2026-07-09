"""Rakit teks konteks pasar untuk 4 Analisa AI (Panel 4, llm/persona_analysis.py).

Pure function, tidak menyentuh network/OpenRouter sama sekali (pola sama
dengan pipeline/compose_briefing.py) -- testable tanpa mock HTTP. SATU blob
konteks yang sama dikirim ke ke-4 persona; system prompt masing-masing
(ditulis manual oleh Giel) yang menentukan sudut pandang analisanya.
"""
from __future__ import annotations

import sqlite3


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


def compose_persona_context(conn: sqlite3.Connection, date: str) -> str:
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
        "SELECT headline, source, impact_level FROM daily_news "
        "WHERE date = ? AND is_key_trigger = 1 ORDER BY id", (date,),
    ).fetchall()

    lines = [f"[SNAPSHOT PASAR - {date}]", snapshot, ""]
    lines.append("[BERITA KEY HARI INI]")
    if key_events:
        for r in key_events:
            lines.append(f"- [{r['impact_level']}] {r['headline']} ({r['source']})")
    else:
        lines.append("(belum ada berita yang di-flag key hari ini)")

    return "\n".join(lines)
