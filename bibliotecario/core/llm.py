"""Cliente LLM multi-proveedor: Groq → NVIDIA → Gemini, con failover.

- Cada proveedor configurado por env var se añade a la cadena en este orden:
  GROQ_API_KEY, NVIDIA_API_KEY, GEMINI_API_KEY (siempre la principal; ver
  política de claves en config.gemini_api_keys, dueño 2026-10-23).
- Toda llamada va a /chat/completions estilo OpenAI (Groq y NVIDIA) excepto las
  Gemini (SDK nativo). 401/403 salta de proveedor; 429/503/500 con backoff.
- Sin proveedor configurado → "" (el pipeline sigue sin LLM).
"""
from __future__ import annotations

import json
import logging
import os
import threading
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
# Fallos consecutivos antes de aparcar un proveedor. Con un solo proveedor
# configurado no se aparca nunca antes de esto: en la eval cieda una rafaga de
# 504 tumbaba el endpoint entero y las 35 preguntas salian con answer vacia.
_DEAD_AFTER = int(os.environ.get("LLM_DEAD_AFTER", "3"))
_STREAK: dict[str, int] = {}


def _is_dead(name: str) -> bool:
    return _DEAD_UNTIL.get(name, 0.0) > time.monotonic()


def _mark_dead(name: str) -> None:
    """Aparta un proveedor, pero no a la primera.

    Con varios proveedores tiene sentido apartar al que falla: los demas siguen
    contestando. Con uno solo (evaluacion pineada a un endpoint) apartarlo deja la
    run entera sin modelo, y una rafaga de 504 tumba las 35 preguntas. Por eso se
    cuentan fallos consecutivos y hace falta `_DEAD_AFTER` antes de aparcar.
    """
    n = _STREAK.get(name, 0) + 1
    _STREAK[name] = n
    if n < _DEAD_AFTER and len(_providers()) < 2:
        logger.warning("LLM %s fallo %d/%d, se reintenta (no se aparca: es el unico "
                       "proveedor)", name, n, _DEAD_AFTER)
        return
    prev = _DEAD_UNTIL.get(name + "#b")
    back = _DEAD_BACKOFF if prev is None else min(_MAX_BACKOFF, prev * 2)
    _DEAD_UNTIL[name] = time.monotonic() + back
    _DEAD_UNTIL[name + "#b"] = back
    logger.warning("LLM %s aparcado %.0f min tras %d fallos", name, back / 60, n)


def _mark_alive(name: str) -> None:
    _DEAD_UNTIL.pop(name, None)
    _DEAD_UNTIL.pop(name + "#b", None)
    _STREAK[name] = 0


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


class TransientResponse(RuntimeError):
    """HTTP 200 con un cuerpo que no es una completacion valida.

    NVIDIA a veces devuelve 200 OK con un payload de error en lugar de
    `choices`. Clasificado como "other" caia en la rama de `strict_fallback` y
    reventaba la RUN ENTERA: murio `abst_candC` a las 22/64 y se perdio la mitad
    del coste de la run. Un 200 malformado es transitorio por definicion: se
    reintenta como cualquier 5xx.
    """


def _classify(exc: Exception) -> str:
    if isinstance(exc, TransientResponse):
        return "retryable"
    s = str(exc)
    code = getattr(exc, "code", None)
    if code == 401 or code == 403 or "401" in s or "403" in s or "API_KEY_INVALID" in s:
        return "invalid"
    # Fallos de red locales/transitorios (§0.3 HITO20, C1): el DNS caído del
    # diagnóstico murió sin reintento porque "name resolution" no matcheaba
    # ningún patrón y clasificaba "other". URLError y errno de red son
    # transitorios por definición.
    s_low = s.lower()
    if (isinstance(exc, urllib.error.URLError)
            or "name resolution" in s_low or "temporary failure" in s_low
            or "connection refused" in s_low or "connection reset" in s_low
            or "network is unreachable" in s_low
            or "errno -3" in s_low or "errno -101" in s_low
            or "errno -110" in s_low or "errno -111" in s_low
            or "errno -104" in s_low):
        return "retryable"
    # 504 y timeout son transitorios por definición en este endpoint: se vio a
    # NVIDIA devolver 504 en una rafaga durante la eval ciega. Sin esto no
    # entraban en "retryable", no reintentaban y tumba(ban) el proveedor entero.
    if (code in (408, 429, 500, 502, 503, 504) or "408" in s or "429" in s
            or "500" in s or "502" in s or "503" in s or "504" in s
            or "UNAVAILABLE" in s or "overloaded" in s.lower() or "high demand" in s.lower()
            or "timeout" in s.lower() or "timed out" in s.lower()
            or "gateway time-out" in s.lower() or "bad gateway" in s.lower()):
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
    # `chat_template_kwargs` es un parámetro de la plantilla vLLM (Nemotron/GLM):
    # sin él el razonamiento se filtra en `content`. Groq NO lo admite y devuelve
    # HTTP 400 `property 'chat_template_kwargs' is unsupported`, lo que tumbo
    # el fallback entero del round-robin. Se envía salvo a Groq.
    if no_think and "groq.com" not in base_url:
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
    choices = d.get("choices") if isinstance(d, dict) else None
    msg = choices[0].get("message") if choices and isinstance(choices[0], dict) else None
    if not msg:
        raise TransientResponse(
            f"HTTP 200 sin choices: {json.dumps(d, ensure_ascii=False)[:300]}")
    usage = d.get("usage") or {}
    _usage_sink().append({**usage, "model": model})
    return (msg.get("content") or msg.get("reasoning_content") or "").strip(), usage


_TLS = threading.local()


def _usage_sink() -> list:
    """Contador de tokens del agente, por hilo.

    El harness de evaluación necesita el gasto real del agente para decidir si
    el barrido profundo se paga. Es thread-local porque la eval puede correr en
    paralelo y un sink compartido mezclaría el gasto de preguntas distintas.
    """
    sink = getattr(_TLS, "sink", None)
    if sink is None:
        sink = _TLS.sink = []
    return sink


def reset_usage() -> None:
    _usage_sink().clear()


def usage_totals() -> dict:
    """Tokens y llamadas acumuladas desde el último reset_usage()."""
    sink = _usage_sink()
    tot = {"calls": len(sink),
           "prompt_tokens": sum(int(u.get("prompt_tokens") or 0) for u in sink),
           "completion_tokens": sum(int(u.get("completion_tokens") or 0) for u in sink),
           "models": sorted({u.get("model", "?") for u in sink})}
    tot["total_tokens"] = tot["prompt_tokens"] + tot["completion_tokens"]
    tot["calls_tokens_unknown"] = sum(1 for u in sink if u.get("tokens_unknown"))
    return tot


def _new_client(key: str):
    from google import genai
    return genai.Client(api_key=key)


def _call_text(client, prompt: str, max_tokens: int, temperature: float = 0.2) -> str:
    resp = client.models.generate_content(
        model=_LLM_MODEL,
        contents=prompt,
        config={"max_output_tokens": max_tokens, "temperature": temperature},
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
    """[(nombre, rol)] en orden de prioridad; rol: openai|gemini.

    `LLM_PROVIDERS` fija la lista (ej. "nvidia"). La evaluación lo necesita: el
    round-robin normal reparte las llamadas entre proveedores, así que una run
    de 120 preguntas acaba midiendo un Agentson: una parte Nemotron y otra
    Gemini. La media seguía pareciendo válida, pero mezcla dos sistemas y las
    llamadas a Gemini además no reportan tokens, así que el coste salía
    infravalado. Con la lista fijada, una caída se registra como fallo.
    """
    prov: list[tuple[str, str]] = []
    if groq_api_key():
        prov.append(("groq", "openai"))
    if nvidia_api_key():
        prov.append(("nvidia", "openai"))
    for i, _k in enumerate(gemini_api_keys(), start=1):
        prov.append((f"gemini{i}", "gemini"))
    pinned = [p.strip() for p in (os.environ.get("LLM_PROVIDERS") or "").split(",") if p.strip()]
    if pinned:
        prov = [p for p in prov if p[0] in pinned]
    return prov


def generate(prompt: str, max_tokens: int = 512, retries: int = 2,
             strict_fallback: bool = False, temperature: float | None = None) -> str:
    """strict_fallback=True: si TODOS los proveedores fallan, lanza en vez de
    devolver "".

    `temperature=None` deja el valor por defecto de cada backend (0.2). Se expone
    solo para poder medir si un fallo del cierre es un modo estable del modelo o
    una muestra desafortunada: si a 0.8 el modelo sigue omitiendo lo mismo, el
    fallo no es de muestreo. Ver evals/probe_close_diversity.py.

    Importante para la evaluación. Con el comportamiento normal, un 504
    transitorio marca un proveedor como muerto y el resto de la run contesta
    con otro modelo sin que nadie se entere: la media resultante mezcla dos
    sistemas y sigue pareciendo válida. Con strict_fallback la pregunta se
    registra como fallida, que es lo honesto.
    """
    global _RR_INDEX
    provs = _providers()
    if not provs:
        if strict_fallback:
            raise RuntimeError("sin proveedores LLM configurados")
        return ""
    temp = 0.2 if temperature is None else temperature
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
                    out = _call_text(client, prompt, max_tokens, temperature=temp)
                    # Gemini no devuelve usage aquí: se registra la llamada con
                    # tokens_desconocidos para que el coste nunca se infravalore
                    # en silencio por cambiar de proveedor.
                    _usage_sink().append({"model": _LLM_MODEL, "provider": "gemini",
                                          "tokens_unknown": True})
                else:
                    base, key = _endpoint(name)
                    models = _models(name)
                    out = _openai_compat(base, key or "", models[min(mi, len(models) - 1)],
                                        prompt, max_tokens, temperature=temp)
                _mark_alive(name)
                # Vacio != respuesta. Los proveedores devuelven "" cuando la
                # llamada cae por rate limit o 504 silencioso, y aqui se
                # trataba como exito: el "" se devolvia y el llamante lo leia
                # como veredicto. Medido 2026-10-12: 2 de 3 llamadas seguidas
                # al juez de ruta 5 salieron vacias y se contaron como
                # violaciones del modelo. Se reintenta como si fuera
                # retryable, con el mismo tope.
                if not out.strip() and attempt < retries:
                    wait = 5 * (attempt + 1)
                    logger.warning("LLM %s devolvio vacio, reintento (%d)", name, attempt + 1)
                    time.sleep(wait)
                    attempt += 1
                    mi += 1
                    continue
                if not out.strip():
                    # Vacio tras agotar reintentos: como en el camino de
                    # excepción, se rueda al siguiente proveedor en vez de
                    # devolver "" y dejar al llamante sin fallback. Medido en
                    # H4 (Fase 4 Hito 3): el cierre quedaba en "  [doc:?]"
                    # porque un único proveedor agotado bastaba para vaciar
                    # la respuesta final.
                    logger.warning("LLM %s siguio devolviendo vacio, paso a siguiente", name)
                    break
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
                if strict_fallback:
                    raise
                return ""
    if strict_fallback:
        raise RuntimeError("todos los proveedores LLM fallaron: "
                           + ", ".join(f"{n}({'muerto' if _is_dead(n) else 'ok'})"
                                       for n, _ in provs))
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
