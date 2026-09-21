"""Ingesta de imágenes: OCR vía visión Gemini + metadata Pillow."""
from __future__ import annotations

import io
import logging
from pathlib import Path

from bibliotecario.config import _LLM_MODEL, gemini_api_key
from bibliotecario.ingest.base import Document

logger = logging.getLogger(__name__)


def ocr_image_bytes(png_bytes: bytes) -> str:
    key = gemini_api_key()
    if not key:
        return ""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=_LLM_MODEL,
            contents=["Extrae TODO el texto visible. Solo el texto, sin comentarios.",
                      types.Part.from_bytes(data=png_bytes, mime_type="image/png")],
            config={"max_output_tokens": 2048, "temperature": 0.0},
        )
        return (resp.text or "").strip()
    except Exception as e:
        logger.warning("OCR visión falló: %s", e)
        return ""


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
