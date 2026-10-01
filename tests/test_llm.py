"""Failover de keys: 429 agota reintentos y salta; 401 salta directo sin esperar."""
import pytest

import bibliotecario.core.llm as LLM


@pytest.fixture(autouse=True)
def _deterministic(monkeypatch):
    monkeypatch.setattr(LLM, "_RR_INDEX", 0)
    monkeypatch.setattr(LLM, "_LAST_CALL", {})
    monkeypatch.setattr(LLM, "_DEAD_UNTIL", {})
    monkeypatch.setattr(LLM, "_STREAK", {})
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
    # fuerza solo Gemini para que los tests existentes sigan válidos
    monkeypatch.setattr(LLM, "groq_api_key", lambda: None)
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: None)
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
    monkeypatch.setattr(LLM, "groq_api_key", lambda: None)
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: None)
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


def test_proveedor_agotado_se_aparca(tmp_path, monkeypatch):
    calls = {"K1": 0, "K2": 0}

    def factory(key):
        def fn():
            calls[key] += 1
            if key == "K1":
                raise RuntimeError("429 quota")
            return _Resp("ok-K2")
        return _FakeClient(fn)

    monkeypatch.setattr(LLM, "groq_api_key", lambda: None)
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: None)
    monkeypatch.setattr(LLM, "gemini_api_keys", lambda: ["K1", "K2"])
    monkeypatch.setattr(LLM, "_new_client", factory)
    for _ in range(4):
        assert LLM.generate("x", retries=0) == "ok-K2"
    # K1 aparcada: solo se sondea en la 1ª llamada
    assert calls["K1"] == 1


def test_cooldown_escalona_hasta_1h(monkeypatch):
    LLM._mark_dead("nvidia")
    b1 = LLM._DEAD_UNTIL["nvidia#b"]
    LLM._mark_dead("nvidia")
    b2 = LLM._DEAD_UNTIL["nvidia#b"]
    assert b2 == min(3600.0, b1 * 2) and b1 == 900.0
    LLM._mark_alive("nvidia")
    assert "nvidia" not in LLM._DEAD_UNTIL


def test_sin_keys_devuelve_vacio(monkeypatch):
    monkeypatch.setattr(LLM, "groq_api_key", lambda: None)
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: None)
    monkeypatch.setattr(LLM, "gemini_api_keys", list)
    assert LLM.generate("hola") == ""


def test_nvidia_prueba_modelo_respaldo(monkeypatch):
    used = []
    monkeypatch.setattr(LLM, "groq_api_key", lambda: None)
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: "N")
    monkeypatch.setattr(LLM, "_models", lambda n: ["m1", "m2"])

    def fake(base, key, model, p, mt, **kw):
        used.append(model)
        if model == "m1":
            raise RuntimeError("HTTP 503: Service temporarily overloaded")
        return "ok-fallback"
    monkeypatch.setattr(LLM, "_openai_compat", fake)
    assert LLM.generate("x", retries=1) == "ok-fallback"
    assert used == ["m1", "m2"]


def test_cadena_orden_y_rotacion(monkeypatch):
    import inspect
    real = LLM._openai_compat
    assert inspect.signature(real).parameters["no_think"].default is True
    monkeypatch.setattr(LLM, "groq_api_key", lambda: "G")
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: "N")
    monkeypatch.setattr(LLM, "gemini_api_keys", lambda: ["K1"])
    seen = []
    monkeypatch.setattr(LLM, "_openai_compat",
                        lambda base, key, model, p, mt, **kw: (seen.append((key, model)), "ok")[1])
    assert LLM.generate("x") == "ok"
    assert LLM.generate("x") == "ok"
    # round-robin reparte G→N; ambos por delante de Gemini
    assert [k for k, _ in seen] == ["G", "N"]
    assert LLM._providers()[0] == ("groq", "openai")


# --- 504 / timeouts y el Aparcado de un proveedor unico -----------------------
#
# Durante la eval ciega NVIDIA devolvio 504 y timeout. _classify no los reconociа
# como transitorios, no reintentaba y _mark_dead aparcaba el endpoint entero: con
# un solo proveedor eso deja la run sin modelo y cada pregunta se guardaba con
# answer vacia y judge=0 (ver tests/test_eval_agg.py).


@pytest.mark.parametrize("mensaje", [
    "HTTP 504: Gateway Time-out",
    "Request timed out after 600s",
    "HTTP 502: Bad Gateway",
    "HTTP 408: Request Timeout",
    "HTTP 429: rate limited",
    "HTTP 500: internal error",
])
def test_transitorios_que_antes_no_reintentaban(mensaje):
    """504/502/408/timeout ahora son retryable, no "other"."""
    assert LLM._classify(RuntimeError(mensaje)) == "retryable"


def test_timeout_de_read_sigue_siendo_transitorio():
    assert LLM._classify(TimeoutError("timed out")) == "retryable"


def test_unico_proveedor_no_se_aparca_a_la_primera(monkeypatch):
    """Con un solo proveedor, un 504 aislado no puede tumbar la run entera.

    Se mide la racha (una vez por llamada a generate que agota sus reintentos),
    no el numero de intentos HTTP: con retries=1 cada generate() intenta 2 veces.
    """
    monkeypatch.setattr(LLM, "groq_api_key", lambda: None)
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: "N")
    monkeypatch.setattr(LLM, "gemini_api_keys", list)   # un solo proveedor, de verdad
    monkeypatch.setattr(LLM, "_models", lambda n: ["m1"])
    monkeypatch.setattr(LLM, "_retry_delay", lambda exc, default=30.0: 0.0)
    assert [n for n, _ in LLM._providers()] == ["nvidia"]

    def fake(base, key, model, p, mt, **kw):
        raise RuntimeError("HTTP 504: Gateway Time-out")

    monkeypatch.setattr(LLM, "_openai_compat", fake)

    for esperado in range(1, LLM._DEAD_AFTER):
        with pytest.raises(RuntimeError):
            LLM.generate("x", retries=1, strict_fallback=True)
        assert LLM._STREAK.get("nvidia") == esperado
        assert not LLM._is_dead("nvidia"), f"aparcado demasiado pronto en el fallo {esperado}"


def test_proveedor_unico_se_aparca_al_ersistir(monkeypatch):
    """Pero si insiste mas de _DEAD_AFTER veces, aparca: no es un no-op."""
    monkeypatch.setattr(LLM, "groq_api_key", lambda: None)
    monkeypatch.setattr(LLM, "nvidia_api_key", lambda: "N")
    monkeypatch.setattr(LLM, "gemini_api_keys", list)
    monkeypatch.setattr(LLM, "_models", lambda n: ["m1"])
    monkeypatch.setattr(LLM, "_retry_delay", lambda exc, default=30.0: 0.0)

    def fake(base, key, model, p, mt, **kw):
        raise RuntimeError("HTTP 504: Gateway Time-out")

    monkeypatch.setattr(LLM, "_openai_compat", fake)
    for _ in range(LLM._DEAD_AFTER):
        with pytest.raises(RuntimeError):
            LLM.generate("x", retries=1, strict_fallback=True)
    assert LLM._is_dead("nvidia")


def test_mark_alive_limpia_la_racha(monkeypatch):
    """Un acierto resetea la racha: no se acumulan fallos aislados en el tiempo."""
    monkeypatch.setattr(LLM, "_providers", lambda: [("nvidia", "openai")])
    LLM._STREAK["nvidia"] = 2
    LLM._mark_alive("nvidia")
    assert LLM._STREAK.get("nvidia") == 0


def test_con_varios_proveedores_aparca_seguido(monkeypatch):
    """El comportamiento de failover se conserva: con alternativas, aparca al 1o."""
    monkeypatch.setattr(LLM, "_providers", lambda: [("nvidia", "openai"), ("gemini1", "gemini")])
    LLM._mark_dead("nvidia")
    assert LLM._is_dead("nvidia")
