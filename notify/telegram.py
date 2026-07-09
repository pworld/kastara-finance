"""Telegram push (Phase E, plan_e.txt) — SATU ARAH, push-only.

Bukan bot dua-arah (command /snapshot dll butuh proses long-polling yang
selalu nyala — laptop lokal tidak selalu on, ditunda ke backlog sampai ada
host always-on, lihat plan_e.txt §"DITUNDA"). Modul ini cuma
`send_message()` (kirim teks yang sudah dirakit `pipeline.compose_briefing`)
dan `get_latest_chat_id()` (helper setup sekali pakai, ambil chat_id tanpa
Giel harus decode JSON manual).

Setup (aksi manual, tidak bisa diotomasi):
  1. Chat ke @BotFather di Telegram, /newbot -> dapat TELEGRAM_BOT_TOKEN.
  2. Kirim 1 pesan (mis. "/start") ke bot barumu dari akun Telegram sendiri.
  3. Jalankan `python -m notify.telegram` -> print chat_id dari update
     terakhir.
  4. Simpan TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID di .env.

Tidak pernah raise ke pemanggil -- gagal kirim TIDAK boleh menjatuhkan
proses lain (pola sama dengan scraper: gagal, dicatat, lanjut).
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

# Modul ini dipanggil standalone (`python -m notify.telegram`) maupun via
# db.connection (yang juga load_dotenv() sendiri) -- panggil di sini juga
# supaya jalan sendirian tanpa bergantung urutan import modul lain.
load_dotenv()

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = 15


def send_message(text: str, *, token: str | None = None, chat_id: str | int | None = None) -> bool:
    """Kirim `text` ke chat_id via Bot API sendMessage. Return True/False.

    token/chat_id default dari env TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID kalau
    tidak diberikan eksplisit (dipakai test dengan token/chat_id palsu).
    """
    token = token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("[telegram] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID kosong — pesan tidak dikirim.")
        return False
    try:
        resp = requests.post(
            f"{TELEGRAM_API_BASE}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return bool(resp.json().get("ok"))
    except Exception as exc:  # noqa: BLE001
        print(f"[telegram] gagal kirim: {type(exc).__name__}: {exc}")
        return False


def get_latest_chat_id(token: str | None = None) -> int | None:
    """Helper setup sekali pakai — ambil chat_id dari update TERBARU
    (getUpdates). None kalau belum ada update (Giel belum kirim pesan ke
    bot) atau token kosong/salah."""
    token = token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("[telegram] TELEGRAM_BOT_TOKEN kosong.")
        return None
    try:
        resp = requests.get(
            f"{TELEGRAM_API_BASE}/bot{token}/getUpdates", timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        results = resp.json().get("result", [])
        if not results:
            return None
        last = results[-1]
        msg = last.get("message") or last.get("channel_post") or {}
        chat = msg.get("chat", {})
        return chat.get("id")
    except Exception as exc:  # noqa: BLE001
        print(f"[telegram] gagal ambil update: {type(exc).__name__}: {exc}")
        return None


if __name__ == "__main__":
    chat_id = get_latest_chat_id()
    if chat_id is None:
        print(
            "Tidak ada update. Pastikan sudah kirim 1 pesan (mis. \"/start\") "
            "ke bot dari akun Telegram-mu, lalu jalankan lagi."
        )
    else:
        print(f"chat_id ditemukan: {chat_id}")
        print("Simpan sebagai TELEGRAM_CHAT_ID di .env")
