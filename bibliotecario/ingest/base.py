"""Modelos base e interfaz de ingesta (6 tipos de fuente → Document normalizado)."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Document:
    source: str
    source_type: str  # url|youtube|pdf|image|txt|docx
    title: str
    text: str
    language: str = "unknown"
    metadata: dict = field(default_factory=dict)


@dataclass
class IngestResult:
    ok: bool
    doc_id: int | None = None
    title: str = ""
    chunks: int = 0
    quality_score: float = 0.0
    quality_alerts: list = field(default_factory=list)
    validation: dict = field(default_factory=dict)
    error: str = ""
    # Qué hizo el upsert: insertado | actualizado | metadatos actualizados |
    # duplicado | '' (fallo de validación). `quality_alerts` es solo calidad.
    action: str = ""


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Capas semánticas del corpus (diseño de la revisión adoptada, § corpus y
# versionado). Una capa NO es una carpeta: se guarda en documents.corpus_capa
# al ingerir y es la que filtra el retrieval (BIBLIOTECARIO_CAPAS).
# Los cinco papers fundacionales son también el set de evaluación, por eso
# corpus_capa es multivalor: "fundacional,evaluacion".
CAPAS = ("fundacional", "evaluacion", "extendido")
CAPA_DEFAULT = "extendido"


def normalize_capa(capa: str | None) -> str:
    """Valida una capa y la devuelve en orden canónico, coma-separada.

    `None` o vacío → capa por defecto (`extendido`). Un token desconocido es
    error, no un typo silencioso: si la capa mal escrita llegara a la BD, el
    filtrado de retrieval la trataría como una cuarta capa real y excluiría
    documentos sin que nadie lo notara.
    """
    if capa is None or not str(capa).strip():
        return CAPA_DEFAULT
    parts = [p.strip().lower() for p in str(capa).split(",") if p.strip()]
    bad = [p for p in parts if p not in CAPAS]
    if bad:
        raise ValueError(f"capa desconocida: {bad!r} (válidas: {', '.join(CAPAS)})")
    seen = [c for c in CAPAS if c in parts]
    return ",".join(seen)


def chunk_text(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    """Troceado por párrafos con solape; robusto a textos cortos."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    if not paras:
        return []
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 1 <= size:
            buf = f"{buf}\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            if len(p) > size:  # párrafo gigante: corte duro con solape
                for i in range(0, len(p), size - overlap):
                    chunks.append(p[i:i + size])
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    # solape: prefija la cola del chunk anterior
    overlapped = [chunks[0]]
    for ch in chunks[1:]:
        tail = overlapped[-1][-overlap:]
        overlapped.append(f"{tail}\n{ch}" if tail else ch)
    return overlapped
