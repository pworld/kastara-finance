"""Test calculated fields: net_liquidity + volume_ma20."""
from db.connection import get_connection, init_db
from indicators.calc import (
    net_liquidity,
    volume_ma20_from_values,
    volume_ma20_for_instrument,
)


def test_net_liquidity_formula():
    # net_liquidity = walcl - rrp - tga
    assert net_liquidity(7_000_000, 500_000, 800_000) == 5_700_000


def test_net_liquidity_none_when_missing():
    assert net_liquidity(None, 1, 1) is None
    assert net_liquidity(1, None, 1) is None
    assert net_liquidity(1, 1, None) is None


def test_volume_ma20_from_values():
    assert volume_ma20_from_values([10, 20, 30]) == 20
    assert volume_ma20_from_values([]) is None
    # > 20 nilai -> hanya 20 terakhir
    vals = list(range(1, 26))  # 1..25
    assert volume_ma20_from_values(vals) == sum(range(6, 26)) / 20


def test_volume_ma20_for_instrument(tmp_path):
    db = tmp_path / "calc.db"
    init_db(db)
    with get_connection(db) as conn:
        for i, d in enumerate(["2025-01-01", "2025-01-02", "2025-01-03"]):
            conn.execute(
                "INSERT INTO asset_ohlcv (date, instrument, close, volume, created_at) "
                "VALUES (?, 'BTC', 100, ?, '')",
                (d, (i + 1) * 100),  # 100, 200, 300
            )
        conn.commit()
    # rata-rata 100,200,300 = 200
    assert volume_ma20_for_instrument("BTC", "2025-01-03", db) == 200
    # batas tanggal: hanya s/d 2025-01-02 -> (100+200)/2 = 150
    assert volume_ma20_for_instrument("BTC", "2025-01-02", db) == 150
    # instrument tidak ada -> None
    assert volume_ma20_for_instrument("ETH", "2025-01-03", db) is None
