"""Ingesta URL genérica: descarga, limpieza HTML, idioma, resumen/conceptos vía LLM."""
from __future__ import annotations

import logging
import re

from bibliotecario.core.llm import generate
from bibliotecario.ingest.base import Document

logger = logging.getLogger(__name__)
USER_AGENT = "Mozilla/5.0 (compatible; Bibliotecario/0.1)"
MAX_CHARS = 30000
_STRIP_TAGS = ("script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "form", "button")


def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def detect_language(text: str) -> str:
    if not text or len(text) < 100:
        return "unknown"
    sample = f" {text[:1000].lower()} "
    es = ("el", "la", "los", "las", "que", "de", "una", "para", "como", "esta", "este", "pero")
    en = ("the", "is", "are", "of", "and", "for", "with", "this", "that", "have", "will", "from")
    es_n = sum(1 for w in es if f" {w} " in sample)
    en_n = sum(1 for w in en if f" {w} " in sample)
    if es_n >= 2 and es_n >= en_n:
        return "es"
    if en_n >= 2:
        return "en"
    return "unknown"


def summarize(text: str) -> str:
    out = generate(f"Resume en 3-5 líneas concisas los puntos principales:\n\n{text[:5000]}\n\nRESUMEN:")
    return out[:500] if out else ""


def extract_concepts(text: str, n: int = 12) -> list[str]:
    out = generate(
        f"Extrae {n} conceptos clave. Devuelve SOLO los conceptos separados por comas:\n\n{text[:6000]}\n\nCONCEPTOS:"
    )
    if not out:
        return []
    return [c.strip() for c in out.split(",") if c.strip()][:n]


def extract_url(url: str) -> Document:
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    if not resp.ok:
        raise ValueError(f"HTTP {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))[:MAX_CHARS]
    if not text.strip():
        raise ValueError("URL sin texto extraíble")
    return Document(source=url, source_type="url", title=title[:200], text=text,
                    language=detect_language(text))
