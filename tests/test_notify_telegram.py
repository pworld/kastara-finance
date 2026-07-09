"""Test notify/telegram.py — di-mock, TIDAK hit API Telegram asli (ini SEND,
bukan READ; tidak boleh spam chat asli tiap test run)."""
import notify.telegram as telegram


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_send_message_missing_credentials_returns_false(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert telegram.send_message("hi") is False


def test_send_message_success(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse({"ok": True})

    monkeypatch.setattr(telegram.requests, "post", fake_post)
    ok = telegram.send_message("hello", token="TOK123", chat_id="999")
    assert ok is True
    assert captured["url"] == "https://api.telegram.org/botTOK123/sendMessage"
    assert captured["json"] == {"chat_id": "999", "text": "hello"}


def test_send_message_http_error_returns_false(monkeypatch):
    def fake_post(url, json, timeout):
        return _FakeResponse({}, status_code=401)

    monkeypatch.setattr(telegram.requests, "post", fake_post)
    assert telegram.send_message("hello", token="BAD", chat_id="999") is False


def test_send_message_network_exception_returns_false(monkeypatch):
    def fake_post(url, json, timeout):
        raise ConnectionError("no network")

    monkeypatch.setattr(telegram.requests, "post", fake_post)
    assert telegram.send_message("hello", token="TOK", chat_id="999") is False


def test_get_latest_chat_id_no_updates(monkeypatch):
    def fake_get(url, timeout):
        return _FakeResponse({"result": []})

    monkeypatch.setattr(telegram.requests, "get", fake_get)
    assert telegram.get_latest_chat_id(token="TOK") is None


def test_get_latest_chat_id_returns_last_chat(monkeypatch):
    def fake_get(url, timeout):
        return _FakeResponse({
            "result": [
                {"message": {"chat": {"id": 111}}},
                {"message": {"chat": {"id": 222}}},
            ]
        })

    monkeypatch.setattr(telegram.requests, "get", fake_get)
    assert telegram.get_latest_chat_id(token="TOK") == 222


def test_get_latest_chat_id_missing_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert telegram.get_latest_chat_id() is None
