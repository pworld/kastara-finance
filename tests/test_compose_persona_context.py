"""Test pipeline/compose_persona_context.py — pure function, tanpa network/LLM.

Arsitektur v4: SHARED CORE (semua persona) + SLICE per lens (field beda-beda).
Test di sini fokus verifikasi isolasi slice -- field GEMA tidak bocor ke
RIVAN dst -- karena itu premis utama pivot dari versi lama (1 konteks sama
ke ke-4 persona).
"""
import pytest

from db.connection import get_connection, init_db
from pipeline.compose_persona_context import compose_persona_context


def _seed_market(conn, date, **overrides):
    defaults = {
        "date": date, "btc_close": 62000.0, "dxy_close": 120.5,
        "us10y_yield": 4.5, "vix_close": 16.0, "net_liquidity": 5_800_000.0,
        "usd_jpy": 160.0, "gold_close": 4000.0, "sp500_close": 7400.0,
        "btc_dominance": 56.0, "usd_idr": 18000.0, "ihsg_close": 5900.0,
        "fear_greed_value": 20, "fear_greed_label": "Extreme Fear",
        "btc_funding_rate": 0.0001, "btc_oi_aggregate": 12_000_000_000.0,
        "btc_liq_long_24h": 500_000.0, "btc_liq_short_24h": 30_000_000.0,
        "btc_long_short_ratio": 1.46, "btc_volume": 40_000_000_000.0,
        "btc_volume_ma20": 29_000_000_000.0,
        "created_at": "",
    }
    defaults.update(overrides)
    cols = ", ".join(defaults)
    placeholders = ", ".join(f":{c}" for c in defaults)
    conn.execute(f"INSERT INTO daily_market ({cols}) VALUES ({placeholders})", defaults)


def _seed_db(tmp_path, date="2026-07-08"):
    db = tmp_path / "t.db"
    init_db(db)
    conn = get_connection(db)
    _seed_market(conn, date)
    conn.commit()
    return conn


def test_shared_core_present_in_all_slices(tmp_path):
    conn = _seed_db(tmp_path)
    for lens in ["GEMA", "LEON", "AKELA", "RIVAN"]:
        text = compose_persona_context(conn, "2026-07-08", lens)
        assert "[TANGGAL ANALISA] 2026-07-08" in text
        assert "[BERITA KEY HARI INI]" in text
        assert "BTC Close: 62,000.00" in text


def test_key_news_shown_and_filtered(tmp_path):
    conn = _seed_db(tmp_path)
    conn.execute(
        "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
        "is_key_trigger, created_at) VALUES ('2026-07-08', 'CNBC', "
        "'Fed signals rate cut', 'https://x.test', 'HIGH', 1, '')"
    )
    conn.execute(
        "INSERT INTO daily_news (date, source, headline, raw_url, impact_level, "
        "is_key_trigger, created_at) VALUES ('2026-07-08', 'CNBC', "
        "'Berita biasa', 'https://x.test', 'LOW', 0, '')"
    )
    conn.commit()
    text = compose_persona_context(conn, "2026-07-08", "GEMA")
    assert "- [HIGH] Fed signals rate cut (CNBC)" in text
    assert "Berita biasa" not in text


def test_gema_slice_has_global_fields_not_rivan_fields(tmp_path):
    conn = _seed_db(tmp_path)
    text = compose_persona_context(conn, "2026-07-08", "GEMA")
    assert "[SLICE GEMA -- Global & Capital Flow]" in text
    assert "DXY: 120.50" in text
    assert "US10Y: 4.50" in text
    assert "USD/IDR" in text
    # field khas RIVAN TIDAK boleh muncul di slice GEMA
    assert "Liquidation Long 24h" not in text
    assert "OI Agregat" not in text


def test_rivan_slice_has_derivatives_fields_not_gema_fields(tmp_path):
    conn = _seed_db(tmp_path)
    text = compose_persona_context(conn, "2026-07-08", "RIVAN")
    assert "[SLICE RIVAN -- Fundamental & Realist]" in text
    assert "Funding Rate" in text
    assert "OI Agregat (3 exchange): 12,000,000,000" in text
    assert "Liquidation Long 24h: 500,000" in text
    assert "Liquidation Short 24h: 30,000,000" in text
    # field khas GEMA (DXY dll) TIDAK boleh muncul di slice RIVAN
    assert "DXY:" not in text
    assert "US10Y:" not in text


def test_ihsg_foreign_flow_in_gema_and_leon_not_akela_rivan(tmp_path):
    conn = _seed_db(tmp_path)
    conn.execute(
        "INSERT INTO positioning (date, instrument, metric, value, source, created_at) "
        "VALUES ('2026-07-08', 'IHSG', 'ihsg_ff_foreign_foreign', 5_000_000_000, 'test', '')"
    )
    conn.execute(
        "INSERT INTO positioning (date, instrument, metric, value, source, created_at) "
        "VALUES ('2026-07-08', 'IHSG', 'foreign_net_buy_value', -1_000_000_000, 'test', '')"
    )
    conn.commit()

    gema_text = compose_persona_context(conn, "2026-07-08", "GEMA")
    leon_text = compose_persona_context(conn, "2026-07-08", "LEON")
    akela_text = compose_persona_context(conn, "2026-07-08", "AKELA")
    rivan_text = compose_persona_context(conn, "2026-07-08", "RIVAN")

    assert "IHSG Foreign Flow" in gema_text
    assert "IHSG Foreign Flow" in leon_text
    assert "IHSG Foreign Flow" not in akela_text
    assert "IHSG Foreign Flow" not in rivan_text
    # framing beda -- GEMA arah arus modal, LEON rapor kepercayaan kebijakan
    assert "arus modal asing" in gema_text
    assert "kepercayaan asing" in leon_text


def test_leon_slice_has_domestic_fields(tmp_path):
    conn = _seed_db(tmp_path)
    text = compose_persona_context(conn, "2026-07-08", "LEON")
    assert "[SLICE LEON -- Policy & Sistem Domestik]" in text
    assert "IHSG: 5,900.00" in text
    assert "econ_calendar country=ID" in text


def test_akela_slice_has_timing_fields(tmp_path):
    conn = _seed_db(tmp_path)
    text = compose_persona_context(conn, "2026-07-08", "AKELA")
    assert "[SLICE AKELA -- Dinamika Pasar & Waktu]" in text
    assert "Fear & Greed: 20 (Extreme Fear)" in text
    assert "Disonansi Flag" in text


def test_policy_tracker_split_domestic_vs_foreign(tmp_path):
    conn = _seed_db(tmp_path)
    conn.execute(
        "INSERT INTO policy_tracker (date, speaker, institution, literal_statement, "
        "stance_score, inference, inference_flag, created_at) VALUES "
        "('2026-07-08', 'Powell', 'Fed', 'stmt', 1, 'hawkish lean', 'TESTABLE', '')"
    )
    conn.execute(
        "INSERT INTO policy_tracker (date, speaker, institution, literal_statement, "
        "stance_score, inference, inference_flag, created_at) VALUES "
        "('2026-07-08', 'Perry Warjiyo', 'BI', 'stmt', -1, 'dovish lean', 'TESTABLE', '')"
    )
    conn.commit()

    gema_text = compose_persona_context(conn, "2026-07-08", "GEMA")
    leon_text = compose_persona_context(conn, "2026-07-08", "LEON")

    assert "Powell" in gema_text
    assert "Perry Warjiyo" not in gema_text
    assert "Perry Warjiyo" in leon_text
    assert "Powell" not in leon_text


def test_unknown_lens_raises(tmp_path):
    conn = _seed_db(tmp_path)
    with pytest.raises(ValueError):
        compose_persona_context(conn, "2026-07-08", "UNKNOWN")
