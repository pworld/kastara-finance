"""Shared helpers untuk semua scraper.

Prinsip:
- Semua waktu WIB (UTC+7). Date disimpan sebagai 'YYYY-MM-DD'.
- Scraper TIDAK boleh melempar exception yang menghentikan pipeline.
  Pakai `safe_call` / SourceFlags untuk tangkap error, tandai 'fail', lanjut.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests

# Zona waktu WIB (UTC+7) — tidak pakai DST.
WIB = timezone(timedelta(hours=7))

DEFAULT_TIMEOUT = 20
DEFAULT_HEADERS = {
    "User-Agent": "kastara-finance/0.1 (Phase A data layer; contact: local)",
    "Accept": "application/json",
}


def get_proxies() -> dict[str, str] | None:
    """Proxy dict untuk requests, dari env KASTARA_PROXY (mis. VPN/SOCKS).

    Contoh .env: KASTARA_PROXY=socks5://127.0.0.1:1080
    Kalau kosong -> None (requests tetap hormati HTTP_PROXY/HTTPS_PROXY bawaan).
    """
    proxy = os.getenv("KASTARA_PROXY", "").strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def now_wib() -> datetime:
    """Waktu sekarang dalam WIB."""
    return datetime.now(WIB)


def today_wib() -> str:
    """Tanggal hari ini WIB sebagai 'YYYY-MM-DD'."""
    return now_wib().strftime("%Y-%m-%d")


def created_at() -> str:
    """Timestamp ISO untuk kolom created_at (WIB)."""
    return now_wib().strftime("%Y-%m-%d %H:%M:%S%z")


def http_get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = 3,
    backoff: float = 1.5,
) -> requests.Response:
    """GET dengan retry sederhana + backoff. Raise kalau gagal total."""
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    proxies = get_proxies()
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                url, params=params, headers=merged_headers,
                timeout=timeout, proxies=proxies,
            )
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001 — sengaja luas, di-retry
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"http_get gagal untuk {url}: {last_exc}") from last_exc


def http_get_json(url: str, **kwargs) -> Any:
    """GET lalu parse JSON."""
    return http_get(url, **kwargs).json()


class SourceFlags:
    """Akumulator status per source/series. Nilai: 'ok' | 'fail' | 'skip'.

    Dipakai supaya pipeline tahu API mana yang sukses/gagal tiap run,
    tanpa silent fail.
    """

    def __init__(self) -> None:
        self._flags: dict[str, str] = {}

    def ok(self, name: str) -> None:
        self._flags[name] = "ok"

    def fail(self, name: str) -> None:
        self._flags[name] = "fail"

    def skip(self, name: str) -> None:
        self._flags[name] = "skip"

    def set(self, name: str, status: str) -> None:
        self._flags[name] = status

    def merge(self, other: "SourceFlags | dict") -> None:
        data = other.as_dict() if isinstance(other, SourceFlags) else dict(other)
        self._flags.update(data)

    def as_dict(self) -> dict[str, str]:
        return dict(self._flags)

    def count(self, status: str) -> int:
        return sum(1 for v in self._flags.values() if v == status)

    def __repr__(self) -> str:  # pragma: no cover
        return f"SourceFlags({self._flags!r})"


def safe_call(
    name: str,
    fn: Callable[[], Any],
    flags: SourceFlags,
    default: Any = None,
) -> Any:
    """Jalankan fn(); kalau error -> flags.fail(name), return default.

    Kalau sukses -> flags.ok(name), return hasil.
    Tidak pernah melempar exception ke pemanggil.
    """
    try:
        result = fn()
        flags.ok(name)
        return result
    except Exception as exc:  # noqa: BLE001
        flags.fail(name)
        print(f"[scraper:fail] {name}: {type(exc).__name__}: {exc}")
        return default
