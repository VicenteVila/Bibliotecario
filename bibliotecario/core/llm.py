"""Cliente LLM mínimo (Gemini cloud). Devuelve "" si no hay clave: el pipeline sigue sin enriquecimiento."""
from __future__ import annotations

import logging

from bibliotecario.config import _LLM_MODEL, gemini_api_key

logger = logging.getLogger(__name__)


def _retry_delay(exc: Exception, default: float = 30.0) -> float:
    import re
    m = re.search(r"retry in ([\d.]+)s", str(exc))
    try:
        return min(120.0, float(m.group(1)) + 2.0) if m else default
    except ValueError:
        return default


def generate(prompt: str, max_tokens: int = 512, retries: int = 2) -> str:
    import time

    key = gemini_api_key()
    if not key:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=key)
        try:
            resp = client.models.generate_content(
                model=_LLM_MODEL,
                contents=prompt,
                config={"max_output_tokens": max_tokens, "temperature": 0.2},
            )
            return (resp.text or "").strip()
        except Exception as e:
            if "429" in str(e) and retries > 0:
                wait = _retry_delay(e)
                logger.warning("LLM 429: esperando %.0fs y reintentando (%d)", wait, retries)
                time.sleep(wait)
                return generate(prompt, max_tokens=max_tokens, retries=retries - 1)
            raise
    except Exception as e:
        logger.warning("LLM generate failed: %s", str(e)[:200])
        return ""
