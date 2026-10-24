'''Parser del canal b con recuperación acotada de `write_file` mal formado.

Fase A de HITO21. Regla dura: si `parse_actions()` ya devuelve acciones, se
devuelven **exactamente** esas (idempotencia); solo si no hay ninguna se
intenta reparar el patrón observado en la evidencia de HITO20 §1:

    "content": """texto..."""}}

Es decir, el modelo usó triples comillas de Python en vez de una cadena JSON.
La reparación no inventa contenido: si faltan `tool`, `path` o el delimitador
de cierre, devuelve lista vacía.
'''
from __future__ import annotations

import re

from evals.sd_pilot.harness import parse_actions

_PAT_WRITE = re.compile(r'"tool"\s*:\s*"write_file"')
_PAT_PATH = re.compile(r'"path"\s*:\s*"([^"\\]+)"')
_PAT_TRIPLE = re.compile(r'"content"\s*:\s*"""(.*)"""\s*\}?\s*\}?\s*$', re.DOTALL)


def parse_actions_tolerante(raw: str) -> list[dict]:
    base = parse_actions(raw)
    if base:
        return base
    return _reparar_write(raw)


def _reparar_write(raw: str) -> list[dict]:
    if not raw or not _PAT_WRITE.search(raw):
        return []
    path = _PAT_PATH.search(raw)
    content = _PAT_TRIPLE.search(raw)
    if not path or not content:
        return []
    return [{"tool": "write_file",
             "args": {"path": path.group(1), "content": content.group(1)}}]
