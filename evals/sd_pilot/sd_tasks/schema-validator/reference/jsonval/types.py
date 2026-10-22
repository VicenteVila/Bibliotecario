"""Clasificación de tipos para el validador de esquemas."""
from __future__ import annotations

KNOWN_TYPES = ("object", "array", "string", "number", "integer", "boolean", "null")


def type_name(value: object) -> str:
    """Nombre del tipo de un dato, para los mensajes de error."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def matches(value: object, name: str) -> bool:
    """¿Cumple el dato el tipo declarado? bool no es number/integer."""
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise ValueError(f"unknown type: {name}")
