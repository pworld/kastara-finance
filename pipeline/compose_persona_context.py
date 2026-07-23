"""Rakit teks konteks pasar untuk 4 Analisa AI (Panel 4, llm/persona_analysis.py).

Pure function, tidak menyentuh network/OpenRouter sama sekali (pola sama
dengan pipeline/compose_briefing.py) -- testable tanpa mock HTTP.

**Arsitektur v4 (Giel) -- SHARED CORE + SLICE per persona**, pivot dari versi
awal (1 konteks identik ke ke-4 persona). Alasan: 4 analis yang membaca data
BERBEDA menghasilkan sudut pandang independen yang bisa didebat (konflik
produktif), bukan 4 analis membaca data identik yang cuma beda gaya bicara.
Overlap field TERTENTU sengaja dipertahankan (funding rate AKELA/RIVAN, ETF
flow GEMA/RIVAN, IHSG foreign flow GEMA/LEON) -- itu bahan konflik yang
disengaja, bukan duplikasi yang perlu dihapus.

SHARED CORE (semua persona): tanggal, berita key hari ini, BTC close + delta
Hari/Minggu.

SLICE (beda per lens):
- GEMA (Global & Capital Flow): DXY/US10Y/VIX/NetLiquidity/HY + delta H/M/B/T,
  USD/JPY/Gold/S&P500/BTCDominance (tanpa delta), USD/IDR + delta, IHSG
  foreign flow (F2F/F2D/D2F), COT DXY + ETF flow, Policy Tracker speaker asing.
- LEON (Policy & Sistem Domestik): IHSG/USD-IDR + delta, IHSG foreign flow
  (framing beda dari GEMA -- rapor kepercayaan kebijakan, bukan arah arus),
  econ_calendar country=ID, Policy Tracker speaker domestik.
- AKELA (Dinamika Pasar & Waktu): econ_calendar penuh, Fear&Greed + delta, VIX,
  BTC Vol MA20, funding rate, delta H/M/B/T semua instrumen utama.
- RIVAN (Fundamental & Realist): funding rate, OI agregat + delta, liquidation
  long/short 24h, L/S ratio, ETF flow, BTC Dominance, volume vs Vol MA20,
  fundamental saham individual (revenue/net income/FCF atau rasio bank,
  grade emiten, foreign flow per-saham -- J-9 data plumbing, lihat catatan
  di bawah).

IHSG foreign flow TIDAK diberikan ke AKELA/RIVAN (disiplin slice, lihat
prompts/persona_akela.txt & persona_rivan.txt §BATASAN).

**J-9 (13 Jul 2026) -- data plumbing equity slice, PROMPT BELUM DIUBAH:**
`_equity_fundamentals_lines()` (RIVAN) dan `_earnings_calendar_lines()`
(AKELA) menambah data fundamentals_quarterly/emiten_grade/earnings_calendar/
foreign-flow-per-saham ke slice masing-masing -- infrastruktur murni,
TIDAK butuh judgment (data sudah dibangun J-4/J-6/J-7/J-8/J-11). Prompt
`persona_rivan.txt`/`persona_akela.txt` BELUM diupdate mengklaim field ini
tersedia -- itu draft terpisah yang perlu ditulis ulang dgn suara Giel
sendiri (lihat docs/j9_equity_slice_prompt_draft.md), pola sama Track D:
jangan pasang klaim prompt sebelum datanya beneran ada DAN prompt-nya
sendiri disetujui.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from indicators.calc import compare_from_series

PERIOD_LABELS = {"day": "H", "week": "M", "month": "B", "year": "T"}

# policy_tracker TIDAK punya kolom terstruktur "negara asal speaker" -- ini
# diklasifikasi lewat keyword match nama institusi (case-insensitive
# substring). Institusi yang tidak match masuk default ASING (institusi
# global jauh lebih banyak ragamnya daripada institusi domestik yang cuma
# beberapa -- default asing lebih aman daripada default domestik).
DOMESTIC_INSTITUTION_KEYWORDS = (
    "bi", "bank indonesia", "kemenkeu", "kementerian keuangan", "ojk",
    "pemerintah", "dpr", "menteri",
)


def _is_domestic_institution(institution: str | None) -> bool:
    if not institution:
        return False
    inst_lower = institution.lower()
    return any(kw in inst_lower for kw in DOMESTIC_INSTITUTION_KEYWORDS)


def _fmt_num(v: float | int | None, decimals: int = 2) -> str:
    if v is None:
        return "n/a"
    return f"{v:,.{decimals}f}"


def _market_history(conn: sqlite3.Connection, date: str, limit: int = 400) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM daily_market WHERE date <= ? ORDER BY date DESC LIMIT ?",
        (date, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def _delta_line(
    history: list[dict[str, Any]], date: str, column: str, label: str, decimals: int = 2,
) -> str:
    """1 baris teks: label, nilai sekarang, delta H/M/B/T (kalau ada histori)."""
    cur_val = history[0].get(column) if history else None
    series = [(r["date"], r.get(column)) for r in history]
    compare = compare_from_series(series, date, cur_val)
    parts = [f"{label}: {_fmt_num(cur_val, decimals)}"]
    deltas = []
    for period, plabel in PERIOD_LABELS.items():
        c = compare.get(period)
        if c and c["delta"] is not None:
            sign = "+" if c["delta"] >= 0 else ""
            deltas.append(f"{plabel}{sign}{_fmt_num(c['delta'], decimals)}")
    if deltas:
        parts.append("(" + ", ".join(deltas) + ")")
    return " ".join(parts)


def _value_line(history: list[dict[str, Any]], column: str, label: str, decimals: int = 2) -> str:
    """1 baris teks TANPA delta -- dipakai field yang v4 doc eksplisit tidak minta delta."""
    cur_val = history[0].get(column) if history else None
    return f"{label}: {_fmt_num(cur_val, decimals)}"


def _key_news_lines(conn: sqlite3.Connection, date: str) -> list[str]:
    """Addendum D §22.5: headline asli TETAP jangkar faktual, display_subtitle
    (kalau ada) & rss_summary (D-1, label WAJIB) ikut sebagai baris tambahan
    -- BUKAN pengganti headline, sama guard yang berlaku di 3 jalur konteks
    (slice otomatis di sini, thread digest §20.4, feed manual §21.4)."""
    rows = conn.execute(
        "SELECT headline, source, impact_level, display_subtitle, rss_summary "
        "FROM daily_news WHERE date = ? AND for_reading = 1 ORDER BY id", (date,),
    ).fetchall()
    if not rows:
        return ["(belum ada berita yang ditandai for_reading hari ini)"]
    lines = []
    for r in rows:
        lines.append(f"- [{r['impact_level']}] {r['headline']} ({r['source']})")
        if r["display_subtitle"]:
            lines.append(f"  catatan Giel: {r['display_subtitle']}")
        if r["rss_summary"]:
            lines.append(f"  [ringkasan RSS]: {r['rss_summary']}")
    return lines


def _ihsg_foreign_flow_lines(conn: sqlite3.Connection, date: str, days: int = 10) -> list[str]:
    """N hari terakhir IHSG foreign flow (F2F/F2D/D2F/net), dari `positioning`
    (Track C, scrapers/idx_foreign_flow.py). Baris mentah per-hari + trend
    ringkas -- persona butuh baca F2F/F2D/D2F sendiri-sendiri, bukan cuma net."""
    rows = conn.execute(
        "SELECT date, metric, value FROM positioning "
        "WHERE instrument = 'IHSG' AND date <= ? "
        "ORDER BY date DESC LIMIT ?", (date, days * 4),
    ).fetchall()
    if not rows:
        return ["(belum ada data IHSG foreign flow)"]
    by_date: dict[str, dict[str, float]] = {}
    for r in rows:
        by_date.setdefault(r["date"], {})[r["metric"]] = r["value"]
    lines = []
    net_values = []
    for d in sorted(by_date, reverse=True)[:days]:
        m = by_date[d]
        net = m.get("foreign_net_buy_value")
        if net is not None:
            net_values.append(net)
        lines.append(
            f"- {d}: F2F={_fmt_num(m.get('ihsg_ff_foreign_foreign'), 0)} "
            f"F2D={_fmt_num(m.get('ihsg_ff_foreign_domestic'), 0)} "
            f"D2F={_fmt_num(m.get('ihsg_ff_domestic_foreign'), 0)} "
            f"Net={_fmt_num(net, 0)}"
        )
    if net_values:
        net_sum = sum(net_values)
        arah = "NET BELI" if net_sum > 0 else "NET JUAL" if net_sum < 0 else "NETRAL"
        lines.append(f"Tren {len(net_values)} hari terakhir: {arah} kumulatif {_fmt_num(net_sum, 0)}")
    return lines


def _positioning_value(conn: sqlite3.Connection, date: str, instrument: str, metric: str) -> float | None:
    row = conn.execute(
        "SELECT value FROM positioning WHERE instrument = ? AND metric = ? AND date <= ? "
        "ORDER BY date DESC LIMIT 1", (instrument, metric, date),
    ).fetchone()
    return row["value"] if row else None


def _policy_tracker_lines(conn: sqlite3.Connection, date: str, *, domestic: bool, limit: int = 5) -> list[str]:
    rows = conn.execute(
        "SELECT date, speaker, institution, stance_score, inference, inference_flag "
        "FROM policy_tracker WHERE date <= ? ORDER BY date DESC, id DESC LIMIT 50",
        (date,),
    ).fetchall()
    filtered = [r for r in rows if _is_domestic_institution(r["institution"]) == domestic][:limit]
    if not filtered:
        who = "domestik" if domestic else "asing"
        return [f"(belum ada entri Policy Tracker speaker {who})"]
    lines = []
    for r in filtered:
        stance = f"stance={r['stance_score']}" if r["stance_score"] is not None else "stance=n/a"
        lines.append(
            f"- {r['date']} {r['speaker'] or '?'} ({r['institution'] or '?'}) {stance} "
            f"[{r['inference_flag'] or 'n/a'}]: {(r['inference'] or '').strip()[:150]}"
        )
    return lines


def _econ_calendar_id_lines(conn: sqlite3.Connection, date: str, limit: int = 5) -> list[str]:
    rows = conn.execute(
        "SELECT event_date, event_name, importance, forecast, previous, actual "
        "FROM econ_calendar WHERE country = 'ID' AND event_date >= ? "
        "ORDER BY event_date LIMIT ?", (date, limit),
    ).fetchall()
    if not rows:
        return ["(belum ada event econ_calendar Indonesia -- sumber ForexFactory "
                "saat ini tidak cover kalender ID)"]
    return [
        f"- {r['event_date']} {r['event_name']} [{r['importance']}] "
        f"forecast={r['forecast'] or 'n/a'} previous={r['previous'] or 'n/a'} actual={r['actual'] or 'n/a'}"
        for r in rows
    ]


def _econ_calendar_full_lines(conn: sqlite3.Connection, date: str, limit: int = 8) -> list[str]:
    rows = conn.execute(
        "SELECT event_date, event_name, country, importance, forecast, previous, actual "
        "FROM econ_calendar WHERE event_date >= ? ORDER BY event_date LIMIT ?", (date, limit),
    ).fetchall()
    if not rows:
        return ["(belum ada event econ_calendar mendatang)"]
    return [
        f"- {r['event_date']} {r['event_name']} ({r['country']}) [{r['importance']}] "
        f"forecast={r['forecast'] or 'n/a'} previous={r['previous'] or 'n/a'} actual={r['actual'] or 'n/a'}"
        for r in rows
    ]


def _disonansi_line(conn: sqlite3.Connection) -> str:
    policy_row = conn.execute(
        "SELECT date, speaker, stance_score FROM policy_tracker "
        "WHERE stance_score IS NOT NULL ORDER BY date DESC, id DESC LIMIT 1"
    ).fetchone()
    dxy_rows = conn.execute(
        "SELECT date, value FROM positioning "
        "WHERE instrument='DXY' AND metric='cot_net_long' "
        "AND date >= date((SELECT MAX(date) FROM positioning WHERE instrument='DXY' "
        "AND metric='cot_net_long'), '-14 days') ORDER BY date ASC"
    ).fetchall()
    if not policy_row or policy_row["stance_score"] == 0 or len(dxy_rows) < 2:
        return "Disonansi Flag: (belum cukup data)"
    stance = policy_row["stance_score"]
    dxy_trend = dxy_rows[-1]["value"] - dxy_rows[0]["value"]
    flagged = (stance > 0 and dxy_trend < 0) or (stance < 0 and dxy_trend > 0)
    return (
        f"Disonansi Flag: {'DISONANSI' if flagged else 'SEARAH'} "
        f"({policy_row['speaker'] or 'Speaker'} stance={stance}, DXY COT trend 14 hari={dxy_trend:+.0f})"
    )


def _fear_greed_history_line(history: list[dict[str, Any]], date: str) -> str:
    cur = history[0].get("fear_greed_value") if history else None
    label = history[0].get("fear_greed_label") if history else None
    series = [(r["date"], r.get("fear_greed_value")) for r in history]
    compare = compare_from_series(series, date, cur)
    week = compare.get("week")
    trend = f", M-1={_fmt_num(week['past_value'], 0)}" if week and week["past_value"] is not None else ""
    return f"Fear & Greed: {_fmt_num(cur, 0)} ({label or 'n/a'}){trend}"


def _equity_fundamentals_lines(conn: sqlite3.Connection, date: str) -> list[str]:
    """Ringkasan per-emiten (fundamentals terbaru + grade + foreign flow
    per-saham) utk semua instrumen Phase J+ di instrument_metadata -- SELALU
    disertakan (pola sama BTC di shared core), tidak kondisional per topik
    berita hari itu. J-9 belum menulis kapan/di slice mana ini dipakai --
    fungsi ini murni data plumbing, dipanggil dari _slice_rivan (lihat
    catatan J-9 draft di prompts/README.md)."""
    instruments = conn.execute(
        "SELECT instrument, sector, is_financial FROM instrument_metadata ORDER BY instrument"
    ).fetchall()
    if not instruments:
        return ["(belum ada emiten individual di universe)"]
    lines = []
    for row in instruments:
        inst = row["instrument"]
        fund = conn.execute(
            "SELECT * FROM fundamentals_quarterly WHERE instrument = ? "
            "ORDER BY quarter_end DESC LIMIT 1", (inst,),
        ).fetchone()
        grade = conn.execute(
            "SELECT * FROM emiten_grade WHERE instrument = ? ORDER BY graded_at DESC, id DESC LIMIT 1",
            (inst,),
        ).fetchone()
        ff_net = _positioning_value(conn, date, inst, "stock_ff_foreign_net_vol")

        parts = [f"- {inst} ({row['sector'] or 'sektor n/a'}):"]
        if fund:
            if row["is_financial"]:
                parts.append(
                    f" NII={_fmt_num(fund['net_interest_income'], 0)} CAR={_fmt_num(fund['car'], 1)}% "
                    f"NPL={_fmt_num(fund['npl_gross'], 1)}% NIM={_fmt_num(fund['nim'], 1)}% "
                    f"LDR={_fmt_num(fund['ldr'], 1)}% (Q {fund['quarter_end']})"
                )
            else:
                parts.append(
                    f" Revenue={_fmt_num(fund['revenue'], 0)} NetIncome={_fmt_num(fund['net_income'], 0)} "
                    f"FCF={_fmt_num(fund['free_cash_flow'], 0)} (Q {fund['quarter_end']}, "
                    f"confidence={fund['confidence']})"
                )
        else:
            parts.append(" fundamentals belum tersedia")
        if grade:
            override = ""
            if grade["giel_override"]:
                ov = json.loads(grade["giel_override"])
                override = f" (override Giel: {ov['quadrant']})"
            parts.append(f" | Grade: {grade['quadrant']} score={_fmt_num(grade['fund_score'], 0)}{override}")
        else:
            parts.append(" | belum digrade")
        if ff_net is not None:
            parts.append(f" | Foreign flow saham (net volume lembar): {_fmt_num(ff_net, 0)}")
        lines.append("".join(parts))
    return lines


def _earnings_calendar_lines(conn: sqlite3.Connection, date: str, limit: int = 5) -> list[str]:
    """Earnings/corporate action terjadwal (earnings_calendar, J-7) -- dipakai
    AKELA sbg dimensi timing tambahan (event risk terjadwal, padanan FOMC/
    rilis data ekonomi, BUKAN cuma berita tak terduga). Skema sudah eksplisit
    mencatat peruntukan ini sejak J-7 dibangun (lihat db/schema.sql)."""
    rows = conn.execute(
        "SELECT instrument, earnings_date, eps_forecast, eps_actual, event_type "
        "FROM earnings_calendar WHERE earnings_date >= ? ORDER BY earnings_date LIMIT ?",
        (date, limit),
    ).fetchall()
    if not rows:
        return ["(belum ada earnings/corporate action terjadwal)"]
    return [
        f"- {r['instrument']} {r['earnings_date']} [{r['event_type'] or 'EARNINGS'}] "
        f"forecast_eps={r['eps_forecast'] if r['eps_forecast'] is not None else 'n/a'} "
        f"actual_eps={r['eps_actual'] if r['eps_actual'] is not None else 'n/a'}"
        for r in rows
    ]


# ---------- SHARED CORE ----------

def _shared_core(conn: sqlite3.Connection, date: str, history: list[dict[str, Any]]) -> str:
    lines = [f"[TANGGAL ANALISA] {date}", ""]
    lines.append("[BERITA KEY HARI INI]")
    lines.extend(_key_news_lines(conn, date))
    lines.append("")
    lines.append("[BTC]")
    lines.append(_delta_line(history, date, "btc_close", "BTC Close", 2))
    return "\n".join(lines)


# ---------- SLICES ----------

def _slice_gema(conn: sqlite3.Connection, date: str, history: list[dict[str, Any]]) -> str:
    lines = ["[SLICE GEMA -- Global & Capital Flow]", ""]
    lines.append("Likuiditas & risk appetite global:")
    for col, label in [
        ("dxy_close", "DXY"), ("us10y_yield", "US10Y"), ("vix_close", "VIX"),
        ("net_liquidity", "Net Liquidity"), ("walcl", "WALCL"), ("rrp", "RRP"),
        ("tga", "TGA"), ("hy_credit_spread", "HY Spread"),
    ]:
        lines.append("  " + _delta_line(history, date, col, label))
    lines.append("")
    lines.append("Rotasi antar-aset & antar-region (tanpa delta):")
    for col, label in [
        ("usd_jpy", "USD/JPY"), ("gold_close", "Gold"),
        ("sp500_close", "S&P 500"), ("btc_dominance", "BTC Dominance"),
    ]:
        lines.append("  " + _value_line(history, col, label))
    lines.append("")
    lines.append("Proxy tekanan kurs EM:")
    lines.append("  " + _delta_line(history, date, "usd_idr", "USD/IDR"))
    lines.append("")
    lines.append("IHSG Foreign Flow (jejak arus modal asing ke ekuitas Indonesia):")
    lines.extend("  " + ln for ln in _ihsg_foreign_flow_lines(conn, date))
    lines.append("")
    lines.append("Jejak posisi modal aktual:")
    cot_dxy = _positioning_value(conn, date, "DXY", "cot_net_long")
    etf_flow = _positioning_value(conn, date, "BTC", "etf_net_flow")
    lines.append(f"  COT net-long DXY: {_fmt_num(cot_dxy, 0)}")
    lines.append(f"  BTC ETF net flow: {_fmt_num(etf_flow, 1)} (USD juta)")
    lines.append("")
    lines.append("Policy Tracker (speaker ASING):")
    lines.extend("  " + ln for ln in _policy_tracker_lines(conn, date, domestic=False))
    return "\n".join(lines)


def _slice_leon(conn: sqlite3.Connection, date: str, history: list[dict[str, Any]]) -> str:
    lines = ["[SLICE LEON -- Policy & Sistem Domestik]", ""]
    lines.append("Barometer domestik:")
    lines.append("  " + _delta_line(history, date, "ihsg_close", "IHSG"))
    lines.append("  " + _delta_line(history, date, "usd_idr", "USD/IDR"))
    lines.append("")
    lines.append("IHSG Foreign Flow (barometer kepercayaan asing thd kebijakan domestik):")
    lines.extend("  " + ln for ln in _ihsg_foreign_flow_lines(conn, date))
    lines.append("")
    lines.append("Agenda kebijakan domestik (econ_calendar country=ID):")
    lines.extend("  " + ln for ln in _econ_calendar_id_lines(conn, date))
    lines.append("")
    lines.append("Policy Tracker (speaker DOMESTIK):")
    lines.extend("  " + ln for ln in _policy_tracker_lines(conn, date, domestic=True))
    return "\n".join(lines)


def _slice_akela(conn: sqlite3.Connection, date: str, history: list[dict[str, Any]]) -> str:
    lines = ["[SLICE AKELA -- Dinamika Pasar & Waktu]", ""]
    lines.append("Kalender ekonomi (forecast/previous/actual):")
    lines.extend("  " + ln for ln in _econ_calendar_full_lines(conn, date))
    lines.append("")
    lines.append("  " + _disonansi_line(conn))
    lines.append("")
    lines.append("Exhaustion & volatilitas:")
    lines.append("  " + _fear_greed_history_line(history, date))
    lines.append("  " + _delta_line(history, date, "vix_close", "VIX"))
    lines.append("  " + _delta_line(history, date, "btc_volume_ma20", "BTC Vol MA20", 0))
    lines.append("  " + _delta_line(history, date, "btc_funding_rate", "Funding Rate", 5))
    lines.append("")
    lines.append("Jadwal earnings/corporate action terjadwal (event risk saham individual, J-7):")
    lines.extend("  " + ln for ln in _earnings_calendar_lines(conn, date))
    lines.append("")
    lines.append("Delta harga instrumen utama (H/M/B/T):")
    for col, label in [
        ("btc_close", "BTC"), ("dxy_close", "DXY"), ("sp500_close", "S&P 500"),
        ("us10y_yield", "US10Y"), ("ihsg_close", "IHSG"), ("gold_close", "Gold"),
    ]:
        lines.append("  " + _delta_line(history, date, col, label))
    return "\n".join(lines)


def _slice_rivan(conn: sqlite3.Connection, date: str, history: list[dict[str, Any]]) -> str:
    lines = ["[SLICE RIVAN -- Fundamental & Realist]", ""]
    lines.append("Struktur leverage & komposisi pergerakan:")
    lines.append("  " + _delta_line(history, date, "btc_funding_rate", "Funding Rate", 5))
    lines.append("  " + _delta_line(history, date, "btc_oi_aggregate", "OI Agregat (3 exchange)", 0))
    lines.append("  " + _value_line(history, "btc_liq_long_24h", "Liquidation Long 24h", 0))
    lines.append("  " + _value_line(history, "btc_liq_short_24h", "Liquidation Short 24h", 0))
    lines.append("  " + _value_line(history, "btc_long_short_ratio", "Long/Short Ratio", 3))
    lines.append("")
    lines.append("Demand struktural & partisipasi:")
    etf_flow = _positioning_value(conn, date, "BTC", "etf_net_flow")
    lines.append(f"  BTC ETF net flow: {_fmt_num(etf_flow, 1)} (USD juta)")
    lines.append("  " + _value_line(history, "btc_dominance", "BTC Dominance"))
    lines.append("  " + _delta_line(history, date, "btc_volume", "BTC Volume", 0))
    lines.append("  " + _delta_line(history, date, "btc_volume_ma20", "BTC Vol MA20", 0))
    lines.append("")
    lines.append("Fundamental saham individual (universe Phase J+, J-4/J-6/J-8/J-11):")
    lines.extend("  " + ln for ln in _equity_fundamentals_lines(conn, date))
    return "\n".join(lines)


_SLICE_BUILDERS = {
    "GEMA": _slice_gema, "LEON": _slice_leon,
    "AKELA": _slice_akela, "RIVAN": _slice_rivan,
}


# ---------- Feed manual berita -> persona (Addendum C §21.4, GELOMBANG C-2)
# ----------

def _manual_selection_block(conn: sqlite3.Connection, news_ids: list[int]) -> str:
    """Blok TAMBAHAN (bukan pengganti slice, guard non-negotiable §21.4) utk
    berita yang Giel pilih manual lewat filter tag di NewsView. Judul yang
    dikirim = headline + display_subtitle (kalau ada) -- indikator subtitle
    SELALU ikut supaya bias editorial Giel kelihatan & auditable, tidak
    tersembunyi (keputusan #3 §21.2). + rss_summary (Addendum D §22.5) --
    format sama §22.5, berlaku di ketiga jalur konteks."""
    if not news_ids:
        return ""
    placeholders = ",".join("?" for _ in news_ids)
    rows = conn.execute(
        f"SELECT headline, source, display_subtitle, rss_summary FROM daily_news WHERE id IN ({placeholders})",
        news_ids,
    ).fetchall()
    if not rows:
        return ""
    lines = ["[BERITA PILIHAN GIEL -- tambahan, BUKAN pengganti slice di atas]", ""]
    for r in rows:
        line = f"- {r['headline']} ({r['source']})"
        if r["display_subtitle"]:
            line += f" [catatan Giel: {r['display_subtitle']}]"
        lines.append(line)
        if r["rss_summary"]:
            lines.append(f"  [ringkasan RSS]: {r['rss_summary']}")
    return "\n".join(lines)


def compose_persona_context(
    conn: sqlite3.Connection, date: str, lens: str, extra_news_ids: list[int] | None = None,
) -> str:
    """SHARED CORE + slice `lens` (GEMA/LEON/AKELA/RIVAN) + opsional blok
    berita pilihan manual Giel (`extra_news_ids`, §21.4). Raise ValueError
    kalau lens tidak dikenal -- caller (web/app.py) yang validasi lens
    sebelum sampai sini, sama seperti pola llm/persona_analysis.py. Guard
    struktural non-negotiable: slice SELALU dipanggil terlepas dari
    `extra_news_ids` -- seleksi manual tidak pernah menggantikan slice
    (§21.4), cuma menambah blok di akhir."""
    lens = lens.upper()
    if lens not in _SLICE_BUILDERS:
        raise ValueError(f"lens tidak dikenal: {lens}")
    history = _market_history(conn, date)
    shared = _shared_core(conn, date, history)
    slice_text = _SLICE_BUILDERS[lens](conn, date, history)
    context = f"{shared}\n\n{slice_text}"
    manual_block = _manual_selection_block(conn, extra_news_ids or [])
    if manual_block:
        context = f"{context}\n\n{manual_block}"
    return context
