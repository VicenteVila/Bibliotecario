"""Extracción PDF con PyMuPDF + análisis de páginas que necesitarían OCR."""
from __future__ import annotations

import logging
from pathlib import Path

from bibliotecario.ingest.base import Document

logger = logging.getLogger(__name__)
OCR_THRESHOLD_CHARS = 200


def extract_pdf(path: str | Path, ocr: bool = False) -> Document:
    import pymupdf

    p = Path(path)
    doc = pymupdf.open(str(p))
    try:
        n_pages = doc.page_count
        title = (doc.metadata.get("title") or "").strip() or p.stem
        page_texts: dict[int, str] = {}
        needs_ocr: list[int] = []
        for i, page in enumerate(doc):
            t = (page.get_text() or "").strip()
            if len(t) < OCR_THRESHOLD_CHARS:
                needs_ocr.append(i)
            else:
                page_texts[i] = t
        if ocr and needs_ocr:
            from bibliotecario.ingest.image import ocr_image_bytes
            for i in needs_ocr:
                try:
                    pix = doc.load_page(i).get_pixmap(matrix=pymupdf.Matrix(200 / 72, 200 / 72))
                    text = ocr_image_bytes(pix.tobytes("png"))
                    if text and len(text.strip()) > 50:
                        page_texts[i] = text
                except Exception as e:
                    logger.warning("OCR página %d falló: %s", i + 1, e)
        ordered = [page_texts[i] for i in sorted(page_texts)]
        full = "\n\n".join(ordered)
    finally:
        doc.close()
    if not full.strip():
        raise ValueError("No se pudo extraer texto del PDF")
    return Document(
        source=str(p), source_type="pdf", title=title[:200], text=full,
        metadata={"pages": n_pages,
                  "digital_pages": len(page_texts), "ocr_requested": ocr},
    )
