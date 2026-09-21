"""Quality gate de ingesta: puntuación 0-100 + alertas (sustituye track_ingest_quality)."""
from __future__ import annotations


def score(source_type: str, text: str, metadata: dict | None = None) -> tuple[float, list[str]]:
    meta = metadata or {}
    alerts: list[str] = []
    pts = 100.0
    n = len(text)
    if n < 500:
        pts -= 40
        alerts.append("contenido_muy_corto")
    elif n < 2000:
        pts -= 15
        alerts.append("contenido_corto")
    if source_type == "youtube" and not meta.get("has_transcript"):
        pts -= 20
        alerts.append("sin_transcripcion")
    if source_type == "pdf" and meta.get("pages", 0) and meta.get("digital_pages", 0) == 0:
        pts -= 10
        alerts.append("pdf_sin_paginas_digitales")
    if source_type == "image":
        pts -= 5
        alerts.append("ocr_sin_verificacion_manual")
    return max(0.0, pts), alerts
