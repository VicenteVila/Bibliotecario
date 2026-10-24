"""Formateo de la salida de la CLI."""
from __future__ import annotations

from stockcli.errors import UsageError
from stockcli.models import Item


def format_list(items: list[Item]) -> str:
    """Una línea por item o EMPTY si no hay."""
    if not items:
        return "EMPTY"
    return "\n".join(f"{it.sku} {it.qty} {it.status}" for it in items)


def format_count(n: int) -> str:
    """Resumen de conteo en una línea."""
    return f"COUNT {n}"


_FORMATTERS = {
    "list": format_list,
    "count": format_count,
}


def format_result(result: tuple[str, object]) -> str:
    """Enruta el resultado (kind, payload) al formatter del kind."""
    kind, payload = result
    fn = _FORMATTERS.get(kind)
    if fn is None:
        raise UsageError(f"unknown result kind: {kind!r}")
    return fn(payload)
