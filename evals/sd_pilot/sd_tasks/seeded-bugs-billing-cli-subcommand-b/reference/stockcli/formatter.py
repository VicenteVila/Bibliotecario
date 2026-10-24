"""Formateo de la salida de la CLI."""
from __future__ import annotations

from stockcli.errors import UsageError
from stockcli.models import Item, ReportResult


def format_list(items: list[Item]) -> str:
    """Una línea por item o EMPTY si no hay."""
    if not items:
        return "EMPTY"
    return "\n".join(f"{it.sku} {it.qty} {it.status}" for it in items)


def format_count(n: int) -> str:
    """Resumen de conteo en una línea."""
    return f"COUNT {n}"


def format_report(result: ReportResult) -> str:
    """TOTAL + una línea por fila; sin filas si total es 0."""
    lineas = [f"TOTAL {result.total}"]
    lineas.extend(f"{it.sku} {it.qty} {it.status}" for it in result.rows)
    return "\n".join(lineas)


_FORMATTERS = {
    "list": format_list,
    "count": format_count,
    "report": format_report,
}


def format_result(result: tuple[str, object]) -> str:
    """Enruta el resultado (kind, payload) al formatter del kind."""
    kind, payload = result
    fn = _FORMATTERS.get(kind)
    if fn is None:
        raise UsageError(f"unknown result kind: {kind!r}")
    return fn(payload)
