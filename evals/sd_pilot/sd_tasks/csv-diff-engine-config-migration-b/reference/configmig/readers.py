"""Lectores de formatos de configuración."""
from __future__ import annotations

import json
import re
import tomllib

from .errors import ConfigParseError
from .model import Config, flatten

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+)$")


def _coerce_ini_value(raw: str) -> object:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    if _INT_RE.match(value):
        return int(value)
    if _FLOAT_RE.match(value):
        return float(value)
    return value


def read_ini(text: str) -> Config:
    """Lee un INI con secciones ``[seccion]`` y ``clave = valor``.

    - Comentarios con ``#`` o ``;``.
    - Los valores se recortan; si van entrecomillados con ``'`` o ``"`` de
      ambos lados, se quitan las comillas.
    - Coerción del valor: ``true``/``false`` (minúsculas) -> bool; entero
      con signo opcional -> int; decimal -> float; el resto -> str.
    - Clave repetida en la misma sección -> ConfigParseError.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    values: dict[str, object] = {}
    section: str | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            if not section:
                raise ConfigParseError(f"seccion vacia en la linea {lineno}")
            continue
        if section is None:
            raise ConfigParseError(
                f"clave fuera de seccion {stripped!r} en la linea {lineno}"
            )
        if "=" not in stripped:
            raise ConfigParseError(f"linea {lineno} sin '=': {stripped!r}")
        key, _, raw_value = stripped.partition("=")
        key = key.strip()
        dotted = f"{section}.{key}"
        if dotted in values:
            raise ConfigParseError(f"clave duplicada {dotted!r} en la linea {lineno}")
        values[dotted] = _coerce_ini_value(raw_value)
    return Config(values=values)


def read_json(text: str) -> Config:
    """Lee JSON (objeto raíz) y lo aplana a claves con punto."""
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigParseError(f"json invalido: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigParseError("la raiz debe ser un objeto json")
    return Config(values=flatten(data))


def read_toml(text: str) -> Config:
    """Lee TOML (subconjunto tomllib) y lo aplana a claves con punto.

    - Error de sintaxis TOML -> ConfigParseError.
    - La raíz debe ser un objeto (siempre lo es en TOML válido).
    """
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigParseError(f"toml invalido: {exc}") from exc
    return Config(values=flatten(data))
