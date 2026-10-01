"""Judge pineado y estricto para la evaluación end-to-end.

Por qué existe aparte del agente: si el juez usa la misma `generate()` que el
agente, comparte modelo y familia, y se auto-favorece. Aquí el juez se fija a un
modelo explícito (por defecto gpt-oss-20b, familia distinta a nemotron) y nunca
participa del round-robin de proveedores.

Por qué es estricto: la rúbrica anterior ("5 = correcta, 3 = parcial, 1 = mal")
era demasiado laxa y daba 5/5 a respuestas correctas pero vagas. Ahora cada nivel
tiene un anclaje explícito, y sobre todo el juez tiene que distinguir la respuesta
que contiene el dato pedido de la que solo roza el tema.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

from bibliotecario.core.llm import _endpoint, _openai_compat_usage

logger = logging.getLogger(__name__)

# Modelo del juez. Distinto del del agente a propósito.
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "openai/gpt-oss-20b")
JUDGE_PROVIDER = os.environ.get("JUDGE_PROVIDER", "nvidia")
# 300 tokens no alcanzaban: el modelo razonaba en prosa y la respuesta se cortaba a
# mitad del JSON (completion_tokens clavado en 300), dejando score=None. Medido.
JUDGE_MAX_TOKENS = int(os.environ.get("JUDGE_MAX_TOKENS", "900"))

JUDGE_PROMPT = """Eres un evaluador estricto de preguntas sobre artículos científicos.
Recibes una PREGUNTA, la REFERENCIA (respuesta correcta de referencia) y una RESPUESTA.
Puntúa SOLO en cuanto a si la RESPUESTA responde correctamente a la PREGUNTA.

Rúbrica:
5 = correcta y completa. Incluye el dato concreto que la PREGUNTA pide, con las cifras exactas.
4 = correcta pero le falta un matiz o un detalle secundario.
3 = parcialmente correcta: trata el tema pero falta O altera el dato principal pedido.
2 = incorrecta: dice algo que contradice la REFERENCIA, o inventa datos.
1 = vacía, irrelevante, o no responde a la pregunta.

Reglas estrictas:
- Si la PREGUNTA pide una cifra concreta y la RESPUESTA no da esa cifra, no puede pasar de 3.
- Si la RESPUESTA contradice la REFERENCIA, no puede pasar de 2.
- No premies la longitud, el estilo ni las citas: solo el contenido correcto.
- Si la RESPUESTA admite que no encontró la evidencia, valórala según lo que explica,
  no como 1 automático.

Responde SOLO este JSON, sin texto antes ni después, sin ```:
{"score": <entero 1-5>, "verdict": "<explica en una frase por qué esa nota>"}"""

_SCORE_RE = re.compile(r'"score"\s*:\s*([1-5])')
_VERDICT_RE = re.compile(r'"verdict"\s*:\s*"([^"]{0,300})')
_FENCE_RE = re.compile(r"```(?:json)?|```")


def _parse(raw: str) -> dict | None:
    """Extrae score/verdict. Estricto: fuera de 1-5 se considera no parseable."""
    if not raw:
        return None
    clean = _FENCE_RE.sub("", raw).strip()
    for cand in (clean, clean[clean.find("{"):clean.rfind("}") + 1] if "{" in clean else ""):
        if not cand:
            continue
        try:
            obj = json.loads(cand)
            s = int(obj.get("score"))
            if 1 <= s <= 5:
                return {"score": s, "verdict": str(obj.get("verdict", ""))[:300]}
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    ms, mv = _SCORE_RE.search(clean), _VERDICT_RE.search(clean)
    if ms:
        return {"score": int(ms.group(1)), "verdict": mv.group(1) if mv else ""}
    return None


JUDGE_TEMPERATURE = float(os.environ.get("JUDGE_TEMPERATURE", "0.2"))


def judge(question: str, reference: str, answer: str, model: str | None = None,
          retries: int = 2, temperature: float | None = None) -> dict:
    """Puntúa una respuesta. Devuelve score, verdict, model, usage y error (nunca lanza).

    Un judge que no parsea devuelve score=None y error≠None. El harness debe
    contarlo como 0 en la media (no descartarlo), o el sesgo de supervivencia
    infla la media justo en las preguntas difíciles.

    `temperature` permite medir cuánto de la varianza de las notas es del juez y
    no del agente. Por defecto 0.2 (JUDGE_TEMPERATURE), que es lo que se ha
    usado siempre; con 0 el juez es reproducible y las comparaciones entre
    versiones dejan de arrastrar ese ruido. Ver evals/measure_judge_noise.py.
    """
    base_url, key = _endpoint(JUDGE_PROVIDER)
    if not key:
        return {"score": None, "verdict": "", "model": model or JUDGE_MODEL,
                "usage": {}, "error": f"sin key para proveedor {JUDGE_PROVIDER}"}
    temp = JUDGE_TEMPERATURE if temperature is None else temperature
    body = (JUDGE_PROMPT + f"\n\nPREGUNTA: {question}\nREFERENCIA: {reference}\n"
            f"RESPUESTA: {answer[:1500]}")
    last, usage = "", {}
    for attempt in range(retries + 1):
        try:
            raw, usage = _openai_compat_usage(base_url, key, model or JUDGE_MODEL, body,
                                             max_tokens=JUDGE_MAX_TOKENS, temperature=temp)
            got = _parse(raw)
            if got:
                return {**got, "model": model or JUDGE_MODEL, "usage": usage, "error": None}
            last = (raw or "")[:120]
        except Exception as e:  # red/429/503: el juez no debe tumbar la eval
            last = str(e)[:120]
            logger.warning("judge fallo (intento %d): %s", attempt + 1, last)
        if attempt < retries:
            time.sleep(5 * (attempt + 1))
    return {"score": None, "verdict": "", "model": model or JUDGE_MODEL, "usage": usage,
            "error": f"no parseable: {last}"}


ABSTENTION_PROMPT = """Eres un evaluador estricto de abstención sobre un corpus documental.

Recibes una PREGUNTA que NO tiene respuesta en el corpus, y una RESPUESTA de un agente.

Decide si el agente se abstainió correctamente o inventó.

abstained = true  si la RESPUESTA dice explícitamente que la información no está
                    en el corpus, que no aparece en los documentos, o que no puede
                    determinarse con la evidencia disponible.
abstained = false si la RESPUESTA da un dato concreto (sobre todo una cifra) como si
                    estuviera en el corpus, aunque lo haga con coletilla de "no estoy
                    seguro" o "aproximadamente".

Reglas estrictas:
- Si la RESPUESTA inventa una cifra específica, abstained = false aunque lo advierta.
- Si la RESPUESTA se abstiene pero además suelta un número, abstained = false.
- Si la RESPUESTA deriva hacia otro tema sinuosamente, abstained = false.
- No juzgues la longitud ni el tono.

Responde SOLO este JSON, sin texto antes ni después, sin ```:
{"abstained": <true|false>, "fabricated_value": <null o la cifra inventada>, "justification": "<una frase>"}"""

_ABSTAINED_RE = re.compile(r'"abstained"\s*:\s*(true|false)', re.IGNORECASE)
# 400 tokens tampoco alcanzaban: gpt-oss-20b razona en prosa antes del JSON y se
# cortaba a mitad (completion_tokens clavado en 400), dejando abstained=None.
# Medido en reas-b8. Mismo bug que el del juez de score, otro prompt.
ABSTENTION_MAX_TOKENS = int(os.environ.get("ABSTENTION_MAX_TOKENS", "900"))


def judge_abstention(question: str, answer: str, model: str | None = None,
                     retries: int = 2) -> dict:
    """Para preguntas no respondibles: ¿el agente se abstuvo o inventó?

    No reutiliza `judge()` porque puntuar una abstención con la rúbrica 1-5 no
    tiene sentido: una respuesta que dice "esto no está en el corpus" no es un
    1, es el comportamiento correcto. Y una cifra inventada tampoco es un 2,
    porque promedia con las respuestas correctas.
    """
    base_url, key = _endpoint(JUDGE_PROVIDER)
    if not key:
        return {"abstained": None, "fabricated_value": None, "justification": "",
                "usage": {}, "error": f"sin key para proveedor {JUDGE_PROVIDER}"}
    body = (ABSTENTION_PROMPT + f"\n\nPREGUNTA: {question}\nRESPUESTA: {answer[:1500]}")
    last, usage = "", {}
    for attempt in range(retries + 1):
        try:
            raw, usage = _openai_compat_usage(base_url, key, model or JUDGE_MODEL, body,
                                             max_tokens=ABSTENTION_MAX_TOKENS)
            clean = _FENCE_RE.sub("", raw or "").strip()
            for cand in (clean, clean[clean.find("{"):clean.rfind("}") + 1] if "{" in clean else ""):
                if not cand:
                    continue
                try:
                    o = json.loads(cand)
                    if isinstance(o.get("abstained"), bool):
                        return {"abstained": o["abstained"],
                                "fabricated_value": o.get("fabricated_value"),
                                "justification": str(o.get("justification", ""))[:300],
                                "model": model or JUDGE_MODEL, "usage": usage, "error": None}
                except (json.JSONDecodeError, ValueError):
                    continue
            m = _ABSTAINED_RE.search(clean)
            if m:
                return {"abstained": m.group(1).lower() == "true", "fabricated_value": None,
                        "justification": "", "model": model or JUDGE_MODEL, "usage": usage,
                        "error": None}
            last = (raw or "")[:120]
        except Exception as e:
            last = str(e)[:120]
            logger.warning("judge_abstention fallo (intento %d): %s", attempt + 1, last)
        if attempt < retries:
            time.sleep(5 * (attempt + 1))
    return {"abstained": None, "fabricated_value": None, "justification": "", "usage": usage,
            "error": f"no parseable: {last}"}