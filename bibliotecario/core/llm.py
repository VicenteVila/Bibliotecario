"""Cliente LLM mínimo (Gemini cloud) con rotación de keys y backoff ante 429.

- Sin keys → "" (el pipeline sigue sin enriquecimiento).
- Ante 429: espera retryDelay y reintenta en la misma key; si se agotan los
  reintentos, salta a la siguiente key (cuota fresca). 401/403 salta directo.
"""
from __future__ import annotations

import logging
import time

from bibliotecario.config import _LLM_MODEL, gemini_api_keys

logger = logging.getLogger(__name__)


class _KeyInvalid(Exception):
    pass


def _retry_delay(exc: Exception, default: float = 30.0) -> float:
    import re
    m = re.search(r"retry in ([\d.]+)s", str(exc))
    try:
        return min(120.0, float(m.group(1)) + 2.0) if m else default
    except ValueError:
        return default


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


def _classify(exc: Exception) -> str:
    s = str(exc)
    if "401" in s or "403" in s or "API_KEY_INVALID" in s:
        return "invalid"
    if ("429" in s or "500" in s or "503" in s or "UNAVAILABLE" in s
            or "overloaded" in s.lower() or "high demand" in s.lower()):
        return "retryable"
    return "other"


def generate(prompt: str, max_tokens: int = 512, retries: int = 2) -> str:
    keys = gemini_api_keys()
    if not keys:
        return ""
    for ki, key in enumerate(keys):
        try:
            client = _new_client(key)
        except Exception as e:
            logger.warning("LLM key %d inutilizable: %s", ki + 1, str(e)[:120])
            continue
        attempt = 0
        while True:
            try:
                return _call_text(client, prompt, max_tokens)
            except Exception as e:
                kind = _classify(e)
                if kind == "invalid":
                    logger.warning("LLM key %d rechazada, paso a siguiente", ki + 1)
                    break
                if kind == "retryable" and attempt < retries:
                    wait = _retry_delay(e)
                    logger.warning("LLM reintentable key %d: esperando %.0fs (%d)", ki + 1, wait, retries - attempt)
                    time.sleep(wait)
                    attempt += 1
                    continue
                if kind == "retryable":
                    logger.warning("LLM key %d agotada/sobrecargada, paso a siguiente", ki + 1)
                    break
                logger.warning("LLM generate failed: %s", str(e)[:200])
                return ""
    return ""


def generate_vision(prompt: str, png_bytes: bytes, max_tokens: int = 2048) -> str:
    keys = gemini_api_keys()
    if not keys:
        return ""
    for ki, key in enumerate(keys):
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
