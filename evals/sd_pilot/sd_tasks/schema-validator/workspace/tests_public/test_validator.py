"""Tests públicos: validador de esquemas."""
import pytest
from jsonval import validate

SCHEMA_USUARIO = {
    "type": "object",
    "properties": {
        "user": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["user"],
}


def test_objeto_valido_devuelve_errores_vacios():
    data = {"user": {"name": "ana"}, "tags": ["x"]}
    assert validate(data, SCHEMA_USUARIO) == []


def test_tipo_de_raiz_incorrecto():
    assert validate(3, {"type": "object"}) == [
        "$: expected object, got integer"
    ]


def test_required_faltante_en_la_raiz():
    schema = {"type": "object", "required": ["name"]}
    assert validate({}, schema) == ["$: missing required property 'name'"]


def test_indice_de_array_en_el_path():
    schema = {"type": "array", "items": {"type": "string"}}
    assert validate([1], schema) == ["$[0]: expected string, got integer"]


def test_schema_no_dict_es_typeerror():
    with pytest.raises(TypeError):
        validate({}, [])
