"""Normalización de citas [doc:chunk] — formato canónico único.

Los proveedores de LLM emiten variantes: `[5:7]`, `[doc:1:chunk:42]`, `[doc:1, chunk:42]`,
`[doc: 2, chunk: 86]`, `[5, chunk 7]`. Este módulo:

- `parse_citations(text)` → lista de (doc_id, chunk) normalizada, en orden de aparición.
- `normalize_citations(text)` → reescribe todas las variantes al formato `[d:c]`.
- `HAS_CITATION` para comprobar quickly si una respuesta trae alguna cita.

Se usa en dos sitios: el cierre del loop (para emitir citas homogéneas y verificables)
y en evals/eval_end2end.py (para medir la provenance real, no una heurística frágil).
"""
from __future__ import annotations

import re

# [5:7] | [doc:5:chunk:7] | [doc:5, chunk:7] | [doc: 5, chunk: 7] | [5, chunk 7]
CITE = re.compile(
    r"\[\s*(?:doc\s*[:=]?\s*)?(\d{1,4})\s*(?:[:,]\s*)?(?:chunk\s*[:=]?\s*)?(\d{1,6})\s*\]",
    re.IGNORECASE,
)

# Varias citas dentro de un mismo corchete: [1:1, 1:6], [1:1,1:6;2:3].
# El agente las emite así, y CITE no las ve porque exige un único par por
# corchete. Medido en la eval: una respuesta correcta con [1:1, 1:6] puntuaba
# 0 citas, es decir la métrica de provenance daba 0 en respuestas bien citadas.
CITE_LIST = re.compile(
    r"\[\s*((?:\d{1,4}\s*:\s*\d{1,6}\s*(?:[,;]\s*)?)+)\]", re.IGNORECASE)
_PAIR = re.compile(r"(\d{1,4})\s*:\s*(\d{1,6})")


def parse_citations(text: str) -> list[tuple[int, int]]:
    """Extrae (doc_id, chunk) de cualquier variante, sin duplicados y en orden."""
    text = text or ""
    out: list[tuple[int, int]] = []
    for m in CITE.finditer(text):
        pair = (int(m.group(1)), int(m.group(2)))
        if pair not in out:
            out.append(pair)
    for m in CITE_LIST.finditer(text):
        for d, c in _PAIR.findall(m.group(1)):
            pair = (int(d), int(c))
            if pair not in out:
                out.append(pair)
    return out


def has_citation(text: str) -> bool:
    return bool(CITE.search(text or "") or CITE_LIST.search(text or ""))


def normalize_citations(text: str) -> str:
    """Reescribe cada cita a [d:c] conservando el resto del texto intacto."""
    return CITE.sub(lambda m: f"[{int(m.group(1))}:{int(m.group(2))}]", text or "")
