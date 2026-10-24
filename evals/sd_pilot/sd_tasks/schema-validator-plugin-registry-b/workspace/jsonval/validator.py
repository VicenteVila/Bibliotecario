"""Validador de esquemas (versión inicial: solo el tipo de la raíz)."""
from __future__ import annotations

from jsonval.paths import ROOT
from jsonval.types import matches, type_name


def validate(data: object, schema: dict) -> list[str]:
    """Valida data contra schema. Versión inicial: solo chequea la raíz."""
    if not isinstance(schema, dict):
        raise TypeError("schema must be dict")
    errores: list[str] = []
    esperado = schema.get("type")
    if esperado is not None and not matches(data, esperado):
        errores.append(f"{ROOT}: expected {esperado}, got {type_name(data)}")
    return errores
