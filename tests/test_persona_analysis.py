"""Test llm/persona_analysis.py — di-mock, TIDAK hit OpenRouter asli."""
import llm.persona_analysis as persona_analysis


class _FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_get_persona_prompt_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    assert persona_analysis.get_persona_prompt("GEMA") is None


def test_get_persona_prompt_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    (tmp_path / "persona_gema.txt").write_text("   \n  ", encoding="utf-8")
    assert persona_analysis.get_persona_prompt("GEMA") is None


def test_get_persona_prompt_filled(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    (tmp_path / "persona_gema.txt").write_text("Kamu analis makro global.", encoding="utf-8")
    assert persona_analysis.get_persona_prompt("GEMA") == "Kamu analis makro global."


def test_persona_status(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    (tmp_path / "persona_gema.txt").write_text("isi", encoding="utf-8")
    status = persona_analysis.persona_status()
    assert status == {"GEMA": True, "LEON": False, "AKELA": False, "RIVAN": False}


def test_run_persona_analysis_missing_prompt_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    try:
        persona_analysis.run_persona_analysis("GEMA", "konteks")
        assert False, "harus raise PersonaPromptMissing"
    except persona_analysis.PersonaPromptMissing as exc:
        assert "GEMA" in str(exc)


def test_run_persona_analysis_missing_api_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    (tmp_path / "persona_gema.txt").write_text("prompt gema", encoding="utf-8")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    try:
        persona_analysis.run_persona_analysis("GEMA", "konteks")
        assert False, "harus raise RuntimeError"
    except RuntimeError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)


def test_run_persona_analysis_success(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    (tmp_path / "persona_gema.txt").write_text("prompt gema", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-123")

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse({"choices": [{"message": {"content": "  hasil analisa  "}}]})

    monkeypatch.setattr(persona_analysis.requests, "post", fake_post)
    text = persona_analysis.run_persona_analysis("GEMA", "konteks pasar")

    assert text == "hasil analisa"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"] == {"Authorization": "Bearer sk-test-123"}
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "prompt gema"},
        {"role": "user", "content": "konteks pasar"},
    ]


def test_run_persona_analysis_uses_model_override(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    (tmp_path / "persona_gema.txt").write_text("prompt gema", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-123")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _FakeResponse({"choices": [{"message": {"content": "x"}}]})

    monkeypatch.setattr(persona_analysis.requests, "post", fake_post)
    persona_analysis.run_persona_analysis("GEMA", "konteks", model="custom/model-x")
    assert captured["json"]["model"] == "custom/model-x"


def test_run_persona_analysis_http_error_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_analysis, "PROMPTS_DIR", tmp_path)
    (tmp_path / "persona_gema.txt").write_text("prompt gema", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-bad")

    def fake_post(url, headers, json, timeout):
        return _FakeResponse({}, status_code=401)

    monkeypatch.setattr(persona_analysis.requests, "post", fake_post)
    try:
        persona_analysis.run_persona_analysis("GEMA", "konteks")
        assert False, "harus raise error dari raise_for_status"
    except RuntimeError as exc:
        assert "401" in str(exc)
