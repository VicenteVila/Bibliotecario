"""Validadores por tipo de fuente (sustituyen a los schemas YAML del origen con lógica Python tipada)."""
from __future__ import annotations

from bibliotecario.ingest.base import Document


def _base_checks(doc: Document, min_chars: int) -> dict:
    issues = []
    if len(doc.text) < min_chars:
        issues.append(f"texto_corto:{len(doc.text)}")
    if not doc.title.strip():
        issues.append("sin_titulo")
    return {"valid": not issues, "issues": issues}


def validate_url(doc: Document) -> dict:
    return _base_checks(doc, 300) | {"source_type": "url"}


def validate_youtube(doc: Document) -> dict:
    v = _base_checks(doc, 200) | {"source_type": "youtube"}
    if not doc.metadata.get("has_transcript"):
        v["issues"].append("sin_transcripcion_solo_metadatos")
        v["valid"] = len(doc.text) >= 200
    return v


def validate_pdf(doc: Document) -> dict:
    v = _base_checks(doc, 500) | {"source_type": "pdf"}
    if not doc.metadata.get("pages"):
        v["issues"].append("sin_num_paginas")
    return v


def validate_image(doc: Document) -> dict:
    return _base_checks(doc, 20) | {"source_type": "image"}


def validate_txt(doc: Document) -> dict:
    return _base_checks(doc, 50) | {"source_type": "txt"}


def validate_docx(doc: Document) -> dict:
    return _base_checks(doc, 50) | {"source_type": "docx"}


_VALIDATORS = {"url": validate_url, "youtube": validate_youtube, "pdf": validate_pdf,
               "image": validate_image, "txt": validate_txt, "docx": validate_docx}


def validate(doc: Document) -> dict:
    fn = _VALIDATORS.get(doc.source_type)
    if fn is None:
        return {"valid": False, "issues": [f"tipo_desconocido:{doc.source_type}"], "source_type": doc.source_type}
    return fn(doc)
