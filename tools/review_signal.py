"""Tool CLI untuk approve/reject trade_signals (Phase B).

Mengubah HANYA giel_approved + notes untuk row yang SUDAH ADA — tidak
pernah membuat/menghitung ulang sinyal (itu tugas pipeline/run_analysis.py).
ID wajib eksplisit, TIDAK ADA mode "approve semua" — prinsip "Giel yang
approve, bukan mesin" (Master Plan §3), dikunci di plan_b.txt §6.

Pakai:
    python -m tools.review_signal list
    python -m tools.review_signal list --instrument BTC --valid-only
    python -m tools.review_signal list --all
    python -m tools.review_signal approve --id 42 --notes "setup bagus, volume kuat"
    python -m tools.review_signal reject  --id 42 --notes "DXY breakout barengan, skip"
"""
from __future__ import annotations

import argparse
from typing import Any

from db.connection import get_connection, init_db


def list_signals(
    conn, *, instrument: str | None = None, valid_only: bool = False,
    show_all: bool = False, limit: int = 50,
) -> list[dict[str, Any]]:
    """Default: cuma sinyal PENDING (giel_approved=0 AND notes IS NULL —
    belum pernah direview sama sekali). --all: tampilkan semua status."""
    where: list[str] = []
    params: list[Any] = []
    if not show_all:
        where.append("giel_approved = 0 AND notes IS NULL")
    if instrument:
        where.append("instrument = ?")
        params.append(instrument.upper())
    if valid_only:
        where.append("is_valid = 1")

    sql = "SELECT * FROM trade_signals"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def set_review(conn, signal_id: int, *, approved: bool, notes: str | None) -> bool:
    """Update giel_approved + notes untuk 1 row by id. Return False kalau
    id tidak ditemukan (bukan diam-diam no-op)."""
    exists = conn.execute("SELECT 1 FROM trade_signals WHERE id = ?", (signal_id,)).fetchone()
    if not exists:
        return False
    conn.execute(
        "UPDATE trade_signals SET giel_approved = ?, notes = ? WHERE id = ?",
        (1 if approved else 0, notes, signal_id),
    )
    return True


def _print_signal(s: dict[str, Any]) -> None:
    status = "APPROVED" if s["giel_approved"] else ("REJECTED" if s["notes"] else "pending")
    valid = "valid" if s["is_valid"] == 1 else ("invalid" if s["is_valid"] == 0 else "-")
    print(f"  id={s['id']:<5} {s['date']} {s['instrument']:<8} {s['signal_type']:<9} "
          f"[{valid}] [{status}]")
    if s["entry_price"] is not None:
        print(f"        entry={s['entry_price']:.2f} sl={s['sl_price']:.2f} "
              f"tp1={s['tp1_price']:.2f} rr={s['rr_ratio']:.2f}")
    if s["notes"]:
        print(f"        notes: {s['notes']}")


def cmd_list(args: argparse.Namespace) -> None:
    init_db()
    with get_connection() as conn:
        rows = list_signals(
            conn, instrument=args.instrument, valid_only=args.valid_only,
            show_all=args.all, limit=args.limit,
        )
    if not rows:
        print("[review_signal] Tidak ada sinyal.")
        return
    print(f"[review_signal] {len(rows)} sinyal:")
    for r in rows:
        _print_signal(r)


def cmd_approve(args: argparse.Namespace) -> None:
    init_db()
    with get_connection() as conn:
        ok = set_review(conn, args.id, approved=True, notes=args.notes)
        conn.commit()
    print(f"[review_signal] id={args.id} APPROVED." if ok else f"[review_signal] id={args.id} tidak ditemukan.")


def cmd_reject(args: argparse.Namespace) -> None:
    init_db()
    with get_connection() as conn:
        ok = set_review(conn, args.id, approved=False, notes=args.notes)
        conn.commit()
    print(f"[review_signal] id={args.id} REJECTED." if ok else f"[review_signal] id={args.id} tidak ditemukan.")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Kastara review sinyal trading (Phase B)")
    sub = p.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="Lihat sinyal")
    p_list.add_argument("--instrument")
    p_list.add_argument("--valid-only", action="store_true")
    p_list.add_argument("--all", action="store_true", help="tampilkan semua status, bukan cuma pending")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_list)

    p_approve = sub.add_parser("approve", help="Approve 1 sinyal by id")
    p_approve.add_argument("--id", type=int, required=True)
    p_approve.add_argument("--notes")
    p_approve.set_defaults(func=cmd_approve)

    p_reject = sub.add_parser("reject", help="Reject 1 sinyal by id")
    p_reject.add_argument("--id", type=int, required=True)
    p_reject.add_argument("--notes")
    p_reject.set_defaults(func=cmd_reject)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
