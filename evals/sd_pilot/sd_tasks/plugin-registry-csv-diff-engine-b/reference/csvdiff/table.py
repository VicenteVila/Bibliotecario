"""Modelo de tabla en memoria."""
from __future__ import annotations

from dataclasses import dataclass, field

KEY_SEPARATOR = "\x1f"


@dataclass
class Table:
    """Tabla leída de un CSV.

    ``rows`` mapea clave compuesta -> dict columna -> valor (cadena).
    """

    columns: list[str] = field(default_factory=list)
    key_columns: list[str] = field(default_factory=list)
    rows: dict[str, dict[str, str]] = field(default_factory=dict)

    def make_key(self, values: dict[str, str]) -> str:
        return KEY_SEPARATOR.join(values[c] for c in self.key_columns)
