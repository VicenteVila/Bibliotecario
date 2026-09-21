"""Failover de keys: 429 agota reintentos y salta; 401 salta directo sin esperar."""
import pytest

import bibliotecario.core.llm as LLM


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch):
    monkeypatch.setattr(LLM, "_RR_INDEX", 0)
    monkeypatch.setattr(LLM, "_LAST_CALL", {})
    monkeypatch.setattr("time.sleep", lambda s: None)


class _Resp:
    def __init__(self, text):
        self.text = text


class _FakeClient:
    def __init__(self, fn):
        self.models = self
        self._fn = fn

    def generate_content(self, **kw):
        return self._fn()


def _patch(monkeypatch, behaviors):
    monkeypatch.setattr(LLM, "gemini_api_keys", lambda: ["K1", "K2"])
    iters = {k: iter(v) for k, v in behaviors.items()}

    def factory(key):
        def fn():
            effect = next(iters[key])
            if isinstance(effect, Exception):
                raise effect
            return _Resp(effect)
        return _FakeClient(fn)

    monkeypatch.setattr(LLM, "_new_client", factory)


def test_rotacion_alterna_keys(monkeypatch):
    seen = []
    monkeypatch.setattr(LLM, "gemini_api_keys", lambda: ["K1", "K2"])

    def factory(key):
        seen.append(key)
        return _FakeClient(lambda: _Resp("ok"))

    monkeypatch.setattr(LLM, "_new_client", factory)
    assert LLM.generate("a") == "ok"
    assert LLM.generate("b") == "ok"
    assert seen == ["K1", "K2"]


def test_429_salta_a_segunda_key(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    _patch(monkeypatch, {"K1": [Exception("429 RESOURCE_EXHAUSTED retry in 0s")] * 3, "K2": ["OK2"]})
    assert LLM.generate("hola", retries=1) == "OK2"
    assert len(sleeps) == 1  # retries=1 → una espera en K1, luego salto a K2


def test_503_reintenta_y_salta(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    _patch(monkeypatch, {"K1": [Exception("503 UNAVAILABLE overloaded")] * 3, "K2": ["OK2"]})
    assert LLM.generate("hola", retries=1) == "OK2"
    assert len(sleeps) == 1


def test_401_salta_sin_esperar(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    _patch(monkeypatch, {"K1": [Exception("401 API_KEY_INVALID")], "K2": ["OK2"]})
    assert LLM.generate("hola") == "OK2"
    assert sleeps == []


def test_sin_keys_devuelve_vacio(monkeypatch):
    monkeypatch.setattr(LLM, "gemini_api_keys", list)
    assert LLM.generate("hola") == ""
