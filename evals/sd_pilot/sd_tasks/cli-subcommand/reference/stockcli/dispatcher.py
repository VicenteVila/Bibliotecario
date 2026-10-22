"""Dispatcher de comandos de la CLI."""
from __future__ import annotations

from stockcli.errors import UsageError
from stockcli.models import Item, ReportResult
from stockcli.parser import Command


def cmd_list(items: list[Item], options: dict) -> tuple[str, object]:
    """Selecciona items por status (si se pidió)."""
    if "status" in options:
        seleccion = [it for it in items if it.status == options["status"]]
    else:
        seleccion = list(items)
    return ("list", seleccion)


def cmd_count(items: list[Item], options: dict) -> tuple[str, object]:
    """Cuenta items por status (si se pidió)."""
    if "status" in options:
        seleccion = [it for it in items if it.status == options["status"]]
    else:
        seleccion = list(items)
    return ("count", len(seleccion))


def cmd_report(items: list[Item], options: dict) -> tuple[str, object]:
    """Filtra, ordena y recorta items para el reporte."""
    seleccion = list(items)
    if "status" in options:
        seleccion = [it for it in seleccion if it.status == options["status"]]
    if "min_qty" in options:
        seleccion = [it for it in seleccion if it.qty >= options["min_qty"]]
    ordenados = sorted(seleccion, key=lambda it: (-it.qty, it.sku))
    if "top" in options:
        ordenados = ordenados[: options["top"]]
    return ("report", ReportResult(total=len(seleccion), rows=tuple(ordenados)))


_HANDLERS = {
    "list": cmd_list,
    "count": cmd_count,
    "report": cmd_report,
}


def dispatch(command: Command, items: list[Item]) -> tuple[str, object]:
    """Ejecuta el handler del comando contra los items."""
    if not isinstance(command, Command):
        raise TypeError("command must be Command")
    handler = _HANDLERS.get(command.name)
    if handler is None:
        raise UsageError(f"unknown command: {command.name!r}")
    return handler(list(items), command.options)
