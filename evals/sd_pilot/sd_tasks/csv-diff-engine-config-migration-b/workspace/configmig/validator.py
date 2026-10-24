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


def validate(config: Config) -> None:
    """Valida el config contra el esquema.

    Lanza ConfigValidationError con la lista ordenada de errores:
    - ``missing:<key>`` para claves requeridas ausentes.
    - ``type:<key>`` cuando el tipo no coincide.
    """
    errors: list[str] = []
    for key, expected in REQUIRED.items():
        if key not in config.values:
            errors.append(f"missing:{key}")
        elif not isinstance(config.values[key], expected):
            errors.append(f"type:{key}")
    for key, expected in OPTIONAL.items():
        if key in config.values and not isinstance(config.values[key], expected):
            errors.append(f"type:{key}")
    if errors:
        raise ConfigValidationError(sorted(errors))
