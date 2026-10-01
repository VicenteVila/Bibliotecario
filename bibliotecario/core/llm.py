"""Cliente LLM multi-proveedor: Groq → NVIDIA → Gemini, con failover.

- Cada proveedor configurado por env var se añade a la cadena en este orden:
  GROQ_API_KEY, NVIDIA_API_KEY, GEMINI_API_KEY[_N] (round-robin entre las Gemini).
- Toda llamada va a /chat/completions estilo OpenAI (Groq y NVIDIA) excepto las
  Gemini (SDK nativo). 401/403 salta de proveedor; 429/503/500 con backoff.
- Sin proveedor configurado → "" (el pipeline sigue sin LLM).
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

from bibliotecario.config import (
    _GROQ_MODEL,
    _LLM_MODEL,
    _NVIDIA_FALLBACK,
    _NVIDIA_MODEL,
    gemini_api_keys,
    groq_api_key,
    nvidia_api_key,
)

logger = logging.getLogger(__name__)


class _KeyInvalid(Exception):
    pass


# Pacing por proveedor: respeta rate limits de cada endpoint.
_RR_INDEX = 0
_LAST_CALL: dict[str, float] = {}
_MIN_INTERVAL = 10.0

# Cooldown adaptativo: un proveedor agotado se aparca (evita sondearlo cada llamada).
_DEAD_UNTIL: dict[str, float] = {}
_DEAD_BACKOFF = 900.0  # 15 min, se duplica hasta 1h por fallos consecutivos
_MAX_BACKOFF = 3600.0


def _is_dead(name: str) -> bool:
    return _DEAD_UNTIL.get(name, 0.0) > time.monotonic()


def _mark_dead(name: str) -> None:
    prev = _DEAD_UNTIL.get(name + "#b")
    back = _DEAD_BACKOFF if prev is None else min(_MAX_BACKOFF, prev * 2)
    _DEAD_UNTIL[name] = time.monotonic() + back
    _DEAD_UNTIL[name + "#b"] = back
    logger.warning("LLM %s aparcado %.0f min", name, back / 60)


def _mark_alive(name: str) -> None:
    _DEAD_UNTIL.pop(name, None)
    _DEAD_UNTIL.pop(name + "#b", None)


def _pace(name: str) -> None:
    wait = _MIN_INTERVAL - (time.monotonic() - _LAST_CALL.get(name, 0.0))
    if wait > 0:
        time.sleep(wait)
    _LAST_CALL[name] = time.monotonic()


def _retry_delay(exc: Exception, default: float = 30.0) -> float:
    import re
    m = re.search(r"retry in ([\d.]+)s", str(exc))
    try:
        return min(120.0, float(m.group(1)) + 2.0) if m else default
    except ValueError:
        return default


def _classify(exc: Exception) -> str:
    s = str(exc)
    code = getattr(exc, "code", None)
    if code == 401 or code == 403 or "401" in s or "403" in s or "API_KEY_INVALID" in s:
        return "invalid"
    if (code in (429, 500, 503) or "429" in s or "500" in s or "503" in s
            or "UNAVAILABLE" in s or "overloaded" in s.lower() or "high demand" in s.lower()):
        return "retryable"
    return "other"


def _openai_compat(base_url: str, api_key: str, model: str, prompt: str,
                   max_tokens: int, temperature: float = 0.2, no_think: bool = True) -> str:
    return _openai_compat_usage(base_url, api_key, model, prompt, max_tokens,
                                temperature, no_think)[0]


def _openai_compat_usage(base_url: str, api_key: str, model: str, prompt: str,
                         max_tokens: int, temperature: float = 0.2,
                         no_think: bool = True) -> tuple[str, dict]:
    """Como _openai_compat, pero devuelve también el `usage` de la respuesta.

    El conteo de tokens es lo único que permite saber si el barrido profundo
    (que mete decenas de miles de caracteres en el cierre) sale rentable: sin
    medirlo, cualquier decisión sobre el prompt es a ciegas.
    """
    payload = {"model": model,
               "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens, "temperature": temperature}
    if no_think:  # Nemotron/GLM: sin esto el razonamiento se filtra en content
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                 "User-Agent": "bibliotecario/1.0 (+https://github.com/VicenteVila/Bibliotecario)"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}") from e
    msg = d["choices"][0]["message"]
    usage = d.get("usage") or {}
    return (msg.get("content") or msg.get("reasoning_content") or "").strip(), usage


def _new_client(key: str):
    from google import genai
    return genai.Client(api_key=key)


def _call_text(client, prompt: str, max_tokens: int) -> str:
    resp = client.models.generate_content(
        model=_LLM_MODEL,
        contents=prompt,
        config={"max_output_tokens": max_tokens, "temperature": 0.2},
    )
    return (resp.text or "").strip()


def _endpoint(name: str) -> tuple[str, str | None]:
    return {"groq": ("https://api.groq.com/openai/v1", groq_api_key()),
            "nvidia": ("https://integrate.api.nvidia.com/v1", nvidia_api_key())}[name]


def _models(name: str) -> list[str]:
    """Modelos por proveedor, en orden de preferencia (el último es el respaldo)."""
    if name == "groq":
        return [_GROQ_MODEL]
    return [_NVIDIA_MODEL] + ([_NVIDIA_FALLBACK] if _NVIDIA_FALLBACK != _NVIDIA_MODEL else [])


def _providers() -> list[tuple[str, str]]:
    """[(nombre, rol)] en orden de prioridad; rol: openai|gemini."""
    prov: list[tuple[str, str]] = []
    if groq_api_key():
        prov.append(("groq", "openai"))
    if nvidia_api_key():
        prov.append(("nvidia", "openai"))
    for i, _k in enumerate(gemini_api_keys(), start=1):
        prov.append((f"gemini{i}", "gemini"))
    return prov


def generate(prompt: str, max_tokens: int = 512, retries: int = 2) -> str:
    global _RR_INDEX
    provs = _providers()
    if not provs:
        return ""
    live = [p for p in provs if not _is_dead(p[0])] or provs
    start = _RR_INDEX % len(live)
    _RR_INDEX += 1
    for off in range(len(live)):
        name, role = live[(start + off) % len(live)]
        _pace(name)
        attempt = 0
        mi = 0  # índice de modelo: el reintento cae al modelo de respaldo
        while True:
            try:
                if role == "gemini":
                    idx = int(name[len("gemini"):]) - 1
                    client = _new_client(gemini_api_keys()[idx])
                    out = _call_text(client, prompt, max_tokens)
                else:
                    base, key = _endpoint(name)
                    models = _models(name)
                    out = _openai_compat(base, key or "", models[min(mi, len(models) - 1)],
                                        prompt, max_tokens)
                _mark_alive(name)
                return out
            except Exception as e:
                kind = _classify(e)
                if kind == "invalid":
                    logger.warning("LLM %s rechazada, paso a siguiente", name)
                    _mark_dead(name)
                    break
                if kind == "retryable" and attempt < retries:
                    wait = _retry_delay(e)
                    logger.warning("LLM reintentable %s: esperando %.0fs (%d)", name, wait, retries - attempt)
                    mi += 1  # prueba el modelo de respaldo en el siguiente intento
                    time.sleep(wait)
                    attempt += 1
                    continue
                if kind == "retryable":
                    logger.warning("LLM %s agotada/sobrecargada, paso a siguiente", name)
                    _mark_dead(name)
                    break
                logger.warning("LLM %s failed: %s", name, str(e)[:200])
                return ""
    return ""


def generate_vision(prompt: str, png_bytes: bytes, max_tokens: int = 2048) -> str:
    global _RR_INDEX
    keys = gemini_api_keys()
    if not keys:
        return ""
    n = len(keys)
    start = _RR_INDEX % n
    _RR_INDEX += 1
    for off in range(n):
        ki = (start + off) % n
        key = keys[ki]
        _pace(f"ocr{ki}")
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=key)
            resp = client.models.generate_content(
                model=_LLM_MODEL,
                contents=[prompt, types.Part.from_bytes(data=png_bytes, mime_type="image/png")],
                config={"max_output_tokens": max_tokens, "temperature": 0.0},
            )
            return (resp.text or "").strip()
        except Exception as e:
            if _classify(e) == "other":
                logger.warning("OCR visión falló: %s", str(e)[:200])
                return ""
            logger.warning("OCR visión key %d falló, paso a siguiente", ki + 1)
            continue
    return ""
