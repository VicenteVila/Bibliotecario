"""Validador del esquema canónico."""
from __future__ import annotations

from .errors import ConfigValidationError
from .model import Config

REQUIRED: dict[str, type] = {
    "app.name": str,
    "app.version": str,
    "db.host": str,
    "db.port": int,
}

OPTIONAL: dict[str, type] = {
    "db.tls": bool,
}

KNOWN_KEYS = set(REQUIRED) | set(OPTIONAL)

_STRING_REQUIRED = {k for k, t in REQUIRED.items() if t is str}


def validate(config: Config) -> None:
    """Valida el config contra el esquema.

    Lanza ConfigValidationError con la lista ordenada de errores:
    - ``missing:<key>`` para claves requeridas ausentes.
    - ``type:<key>`` cuando el tipo no coincide exactamente (``bool`` no
      cuenta como ``int``).
    - ``empty:<key>`` cuando una cadena requerida es ``""``.
    - ``unknown:<key>`` para claves fuera del esquema.
    """
    errors: list[str] = []
    for key, expected in REQUIRED.items():
        if key not in config.values:
            errors.append(f"missing:{key}")
            continue
        value = config.values[key]
        if type(value) is not expected:
            errors.append(f"type:{key}")
        elif key in _STRING_REQUIRED and value == "":
            errors.append(f"empty:{key}")
    for key, expected in OPTIONAL.items():
        if key in config.values and type(config.values[key]) is not expected:
            errors.append(f"type:{key}")
    for key in config.values:
        if key not in KNOWN_KEYS:
            errors.append(f"unknown:{key}")
    if errors:
        raise ConfigValidationError(sorted(errors))
