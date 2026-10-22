"""HITO17 §1.B — prefiltro no-LLM de frames sin contenido (Opción B).

Regla declarada sin umbral calibrado: un frame es «sin contenido» si es
**color plano** (todos los píxeles idénticos — min==max por canal). El
control negro de U2 (`ffmpeg lavfi color=black`) lo cumple exactamente.

Un caso se anula SOLO si TODOS sus frames son planos: entonces el juez no
se llama (0 llamadas) y todos los ítems salen 0 con la misma forma que un
JSON del juez — U2 pasa **por construcción**, como declaró el dueño al
ratificar la Opción B (2026-10-22).

La trampa U7 NO pasa por este prefiltro: su marco vacío debe puntuar 0 en
el juez CRUDO, que es exactamente lo que U7 mide.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def frame_plano(path: Path) -> bool:
    """True si todos los píxeles del frame son idénticos (color plano)."""
    with Image.open(path) as im:
        extrema = im.convert("RGB").getextrema()
    return all(mn == mx for mn, mx in extrema)


def analizar(frames: list[Path]) -> dict:
    """Informe del prefiltro para un caso (se persiste en la evidencia)."""
    planos = [f.name for f in frames if frame_plano(f)]
    sin = bool(frames) and len(planos) == len(frames)
    motivo = ""
    if sin:
        motivo = (f"prefiltro: {len(planos)}/{len(frames)} frames de color "
                  "plano (sin contenido) — anulación por construcción")
    return {"aplicado": True, "total": len(frames), "planos": len(planos),
            "sin_contenido": sin, "motivo": motivo}


def anular(rubrica: dict, motivo: str) -> dict:
    """Resultado con la forma de `juez_b2.parsear`, con todos los ítems en 0."""
    items = {it["id"]: {"score": 0.0, "justificacion": motivo[:400]}
             for it in rubrica["items"]}
    return {"items": items, "intentos": 0, "usage": {}}
