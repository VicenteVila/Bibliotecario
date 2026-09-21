"""Extracción de citas: arXiv IDs, DOIs y URLs (port de citation_extractor, simplificado)."""
from __future__ import annotations

import re

_ARXIV = re.compile(r"arXiv:\s?(\d{4}\.\d{4,5})(v\d+)?", re.IGNORECASE)
_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
_URL = re.compile(r"https?://[^\s)>\]]+")


def extract_citations(text: str) -> dict:
    arxiv = sorted({m.group(1) for m in _ARXIV.finditer(text)})
    dois = sorted({m.group(0).rstrip(".,;)") for m in _DOI.finditer(text)})[:50]
    urls = sorted({m.group(0).rstrip(".,;)") for m in _URL.finditer(text)})[:50]
    return {"arxiv": arxiv, "dois": dois, "urls": urls}
