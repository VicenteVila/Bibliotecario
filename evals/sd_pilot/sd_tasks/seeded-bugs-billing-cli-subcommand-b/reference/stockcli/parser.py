"""Parser de argv de la CLI."""
from __future__ import annotations

from dataclasses import dataclass

from stockcli.errors import UsageError

VALID_STATUS = ("OK", "LOW", "OUT")


@dataclass(frozen=True)
class Command:
    """Comando parseado: nombre + opciones normalizadas."""

    name: str
    options: dict[str, str | int]


_SPECS: dict[str, dict[str, str]] = {
    "list": {"status": "str"},
    "count": {"status": "str"},
    "report": {"status": "str", "min-qty": "int", "top": "int"},
}


def _coerce(flag: str, kind: str, raw: str) -> str | int:
    if kind == "str":
        return raw
    try:
        return int(raw, 10)
    except ValueError:
        raise UsageError(f"invalid integer for --{flag}: {raw!r}") from None


def _validate(flag: str, value: str | int) -> None:
    if flag == "status" and value not in VALID_STATUS:
        raise UsageError(f"invalid status: {value!r} (expected OK|LOW|OUT)")
    if flag == "min-qty" and value < 0:
        raise UsageError("min-qty must be >= 0")
    if flag == "top" and value < 1:
        raise UsageError("top must be >= 1")


def parse(argv: list[str]) -> Command:
    """Parsea argv a un Command; errores de uso -> UsageError."""
    if not argv:
        raise UsageError("missing command")
    name, *rest = argv
    spec = _SPECS.get(name)
    if spec is None:
        raise UsageError(f"unknown command: {name!r}")
    options: dict[str, str | int] = {}
    i = 0
    while i < len(rest):
        token = rest[i]
        if not token.startswith("--"):
            raise UsageError(f"unexpected argument: {token!r}")
        body = token[2:]
        if "=" in body:
            flag, _, raw = body.partition("=")
        else:
            flag = body
            if i + 1 >= len(rest):
                raise UsageError(f"flag requires a value: --{flag}")
            raw = rest[i + 1]
            i += 1
        if flag not in spec:
            raise UsageError(f"unknown flag: --{flag}")
        value = _coerce(flag, spec[flag], raw)
        _validate(flag, value)
        options[flag.replace("-", "_")] = value
        i += 1
    return Command(name=name, options=options)
