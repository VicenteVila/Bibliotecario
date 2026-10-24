"""Orden de resolución de plugins (versión inicial simplificada)."""
from __future__ import annotations

from .plugin import PluginSpec


def resolve_order(specs: dict[str, PluginSpec]) -> list[str]:
    """Devuelve los nombres de plugin en orden de carga.

    Versión inicial: ignora dependencias y ordena por prioridad y nombre.
    """
    return sorted(
        specs,
        key=lambda n: (-specs[n].priority, n),
    )
