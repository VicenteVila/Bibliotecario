"""Validador de esquemas JSON-like con paths exactos."""
from __future__ import annotations

from jsonval.paths import ROOT, index, key
from jsonval.types import matches, type_name


def validate(data: object, schema: dict) -> list[str]:
    """Valida data contra schema; devuelve mensajes "{path}: {detalle}"."""
    if not isinstance(schema, dict):
        raise TypeError("schema must be dict")
    errores: list[str] = []
    _check(data, schema, ROOT, errores)
    return errores


def _check(data: object, schema: dict, path: str, errores: list[str]) -> None:
    esperado = schema.get("type")
    if esperado is not None and not matches(data, esperado):
        errores.append(f"{path}: expected {esperado}, got {type_name(data)}")
        return
    if "enum" in schema and not _enum_contains(schema["enum"], data):
        errores.append(f"{path}: value not in enum")
        return
    if esperado == "object":
        _check_object(data, schema, path, errores)
    elif esperado == "array":
        items = schema.get("items")
        if items is not None:
            for i, valor in enumerate(data):
                _check(valor, items, index(path, i), errores)
    elif esperado == "string":
        _check_string(data, schema, path, errores)


def _check_object(
    data: dict, schema: dict, path: str, errores: list[str]
) -> None:
    for nombre in schema.get("required", ()):
        if nombre not in data:
            errores.append(f"{path}: missing required property {nombre!r}")
    props = schema.get("properties", {})
    adicionales = schema.get("additionalProperties", True)
    for clave, valor in data.items():
        sub = props.get(clave)
        if sub is not None:
            _check(valor, sub, key(path, clave), errores)
        elif adicionales is False:
            errores.append(f"{path}: unexpected property {clave!r}")


def _check_string(
    data: str, schema: dict, path: str, errores: list[str]
) -> None:
    n = len(data)
    min_len = schema.get("minLength")
    max_len = schema.get("maxLength")
    if min_len is not None and n < min_len:
        errores.append(f"{path}: string length {n} < minLength {min_len}")
    if max_len is not None and n > max_len:
        errores.append(f"{path}: string length {n} > maxLength {max_len}")


def _enum_contains(opciones: object, valor: object) -> bool:
    for opcion in opciones:
        if type(opcion) is type(valor) and opcion == valor:
            return True
    return False
