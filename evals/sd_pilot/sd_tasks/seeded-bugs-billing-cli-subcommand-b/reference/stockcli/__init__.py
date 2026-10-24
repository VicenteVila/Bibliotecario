"""CLI de inventario: parser, dispatcher y formatter."""
from stockcli.cli import main
from stockcli.dispatcher import dispatch
from stockcli.errors import DataError, UsageError
from stockcli.formatter import format_result
from stockcli.models import ITEMS, Item, ReportResult
from stockcli.parser import Command, parse

__all__ = [
    "ITEMS",
    "Command",
    "DataError",
    "Item",
    "ReportResult",
    "UsageError",
    "dispatch",
    "format_result",
    "main",
    "parse",
]
