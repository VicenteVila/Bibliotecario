"""Modelo canónico de configuración."""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import ConfigParseError


@dataclass
class Config:
    """Config canónico: valores planos con claves con punto.

    Los escalares admitidos son ``str``, ``int``, ``float`` y ``bool``.
    """

    values: dict[str, object] = field(default_factory=dict)


def flatten(data: dict, prefix: str = "") -> dict[str, object]:
    """Aplana un dict anidado a claves con punto.

    - Dicts vacíos se omiten.
    - Una lista como valor -> ConfigParseError.
    """
    out: dict[str, object] = {}
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, dotted + "."))
        elif isinstance(value, list):
            raise ConfigParseError(f"valor de lista no soportado en {dotted!r}")
        else:
            out[dotted] = value
    return out
