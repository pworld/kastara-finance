"""OpenRouter-based LLM persona analysis (Panel 4).

Pivot dari plan_c.txt §0 / Master Plan ("4 lensa diisi manual, bukan AI
agent") -- disetujui eksplisit oleh Giel: 4 analisa (GEMA/LEON/AKELA/RIVAN)
sekarang di-generate lewat OpenRouter, bukan diketik manual. Sisa dashboard
(Synthesis, Outlook, Trading Journal, Prediction Log, External AI Check,
Conflict Notes) TETAP 100% manual -- deviasi ini scoped ke 4 analisa saja.

System prompt tiap persona ditulis manual oleh Giel di
`prompts/persona_<lens>.txt` (TIDAK dibuat otomatis, TIDAK di-commit --
lihat prompts/README.md). Kalau file belum ada/kosong, `run_persona_analysis`
raise `PersonaPromptMissing` -- caller (web/app.py) WAJIB kasih tahu Giel,
bukan diam-diam skip atau jalan dengan prompt kosong.

Beda dari notify/telegram.py: modul itu SENGAJA menelan semua error (fire-
and-forget, gagal kirim tidak boleh menjatuhkan pipeline lain). Modul ini
SENGAJA raise -- dipanggil dari 1 request/response interaktif yang perlu
membedakan penyebab gagal (prompt belum diisi vs API key kosong vs network)
supaya pesan ke Giel akurat.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 10 Agustus 2026: `prompts/` sengaja gitignored (lihat prompts/README.md)
# -- di Railway, filesystem app di luar Volume dibangun ULANG dari image
# tiap deploy, jadi file yang di-upload manual ke situ hilang lagi begitu
# deploy berikutnya. `KASTARA_PROMPTS_DIR` (opsional) arahkan ke folder di
# Volume yang sama dgn DB (mis. /data/prompts) supaya prompt persona
# bertahan lintas deploy -- kosong = pakai default lama (prompts/ di
# source tree, cocok utk dev lokal, TIDAK berubah drpd sebelumnya).
_PROMPTS_DIR_OVERRIDE = os.getenv("KASTARA_PROMPTS_DIR", "").strip()
PROMPTS_DIR = Path(_PROMPTS_DIR_OVERRIDE) if _PROMPTS_DIR_OVERRIDE else PROJECT_ROOT / "prompts"

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-sonnet-5"
DEFAULT_TIMEOUT = 60

# Label anonim (tanpa codename) -- ditampilkan di UI. Codename tetap dipakai
# sebagai `reading_workspace.lens` value (schema/histori tidak berubah).
PERSONA_LABELS = {
    "GEMA": "Global & Capital Flow",
    "LEON": "Policy & Sistem Domestik",
    "AKELA": "Dinamika Pasar & Waktu",
    "RIVAN": "Fundamental & Realist",
}


class PersonaPromptMissing(Exception):
    """Prompt persona belum diisi -- caller harus kasih tahu Giel, bukan skip diam-diam."""


def prompt_path(lens: str) -> Path:
    return PROMPTS_DIR / f"persona_{lens.lower()}.txt"


def get_persona_prompt(lens: str) -> str | None:
    """System prompt utk 1 persona. None kalau file belum ada atau isinya kosong."""
    p = prompt_path(lens)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8").strip()
    return text or None


def persona_status() -> dict[str, bool]:
    """{lens: True/False} -- True kalau prompt sudah diisi, dipakai UI Panel 4
    buat nunjukin kartu mana yang belum siap dijalankan."""
    return {lens: get_persona_prompt(lens) is not None for lens in PERSONA_LABELS}


def run_persona_analysis(lens: str, context_text: str, *, model: str | None = None) -> str:
    """Panggil OpenRouter chat completion utk 1 persona (system prompt persona
    + context_text sebagai user message). Raise PersonaPromptMissing kalau
    prompt kosong, RuntimeError kalau OPENROUTER_API_KEY kosong, atau
    requests.HTTPError/RequestException kalau panggilan API gagal."""
    system_prompt = get_persona_prompt(lens)
    if system_prompt is None:
        raise PersonaPromptMissing(
            f"Prompt persona {lens} belum diisi. Tulis system prompt-nya di "
            f"prompts/{prompt_path(lens).name}"
        )
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY kosong di .env")
    model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)

    resp = requests.post(
        f"{OPENROUTER_API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_text},
            ],
        },
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
