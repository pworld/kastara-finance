"""CLI: rakit + kirim Daily Briefing ke Telegram (Phase E, plan_e.txt).

Pakai:
    python -m pipeline.send_briefing                  # hari ini, kirim
    python -m pipeline.send_briefing --date 2026-07-08 # tanggal tertentu
    python -m pipeline.send_briefing --dry-run         # print, TIDAK kirim

Dipicu MANUAL oleh Giel setelah selesai rutinitas pagi (Panel 4-6 terisi)
— BUKAN bagian dari `run_daily` (lihat plan_e.txt: isi briefing baru
lengkap setelah Panel 6, bukan pas data pull jam 07:00).
"""
from __future__ import annotations

import argparse

from db.connection import get_connection
from notify.telegram import send_message
from pipeline.compose_briefing import compose_daily_briefing
from scrapers.base import today_wib


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Kirim Daily Briefing ke Telegram (Phase E)")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default: hari ini WIB)")
    p.add_argument("--dry-run", action="store_true", help="print teks, tidak kirim")
    args = p.parse_args(argv)

    date = args.date or today_wib()
    with get_connection() as conn:
        text = compose_daily_briefing(conn, date)

    print(text)
    if args.dry_run:
        print("\n[send_briefing] --dry-run: TIDAK dikirim.")
        return

    ok = send_message(text)
    print(f"\n[send_briefing] {'terkirim' if ok else 'GAGAL kirim'} ke Telegram.")


if __name__ == "__main__":
    main()
