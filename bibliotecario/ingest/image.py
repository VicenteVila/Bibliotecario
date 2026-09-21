"""Ingesta de imágenes: OCR vía visión Gemini + metadata Pillow."""
from __future__ import annotations

import io
from pathlib import Path

from bibliotecario.ingest.base import Document


def ocr_image_bytes(png_bytes: bytes) -> str:
    from bibliotecario.core.llm import generate_vision
    return generate_vision("Extrae TODO el texto visible. Solo el texto, sin comentarios.", png_bytes)


def extract_image(path: str | Path) -> Document:
    from PIL import Image

    p = Path(path)
    img = Image.open(str(p))
    w, h, fmt = img.size[0], img.size[1], img.format or p.suffix.lstrip(".")
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    text = ocr_image_bytes(buf.getvalue())
    if not text:
        raise ValueError("OCR no extrajo texto (¿falta GEMINI_API_KEY o imagen sin texto?)")
    return Document(source=str(p), source_type="image", title=p.stem, text=text,
                    metadata={"width": w, "height": h, "format": fmt})
