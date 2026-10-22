"""Punto de entrada de la CLI de inventario."""
from __future__ import annotations

import sys
from typing import TextIO

from stockcli.dispatcher import dispatch
from stockcli.errors import DataError, UsageError
from stockcli.formatter import format_result
from stockcli.models import ITEMS, Item
from stockcli.parser import parse


def main(
    argv: list[str] | None = None,
    *,
    items: tuple[Item, ...] | list[Item] = ITEMS,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Ejecuta un comando; devuelve el exit code (0 ok, 2 uso, 1 datos)."""
    if argv is None:
        argv = sys.argv[1:]
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr
    try:
        command = parse(argv)
        result = dispatch(command, list(items))
        stdout.write(format_result(result) + "\n")
        return 0
    except UsageError as exc:
        stderr.write(f"error: {exc}\n")
        return 2
    except DataError as exc:
        stderr.write(f"error: {exc}\n")
        return 1
