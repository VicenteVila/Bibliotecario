"""Construcción de paths de error con escaping de claves."""
from __future__ import annotations

import re

ROOT = "$"

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_ESCAPES = (
    ("\\", "\\\\"),
    ('"', '\\"'),
    ("\n", "\\n"),
    ("\t", "\\t"),
    ("\r", "\\r"),
)


def key(path: str, name: str) -> str:
    """Path de una propiedad: notación punto o corchete con escaping."""
    if _IDENT.match(name):
        return f"{path}.{name}"
    escapada = name
    for original, reemplazo in _ESCAPES:
        escapada = escapada.replace(original, reemplazo)
    return f'{path}["{escapada}"]'


def index(path: str, i: int) -> str:
    """Path de un elemento de array."""
    return f"{path}[{i}]"
