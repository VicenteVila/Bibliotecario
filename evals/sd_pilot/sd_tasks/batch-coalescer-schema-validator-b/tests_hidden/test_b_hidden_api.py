"""Tests ocultos: contrato de la API (TypeError y tipos de dato)."""
import pytest
from jsonval import validate


def test_schema_list_es_typeerror():
    with pytest.raises(TypeError) as exc:
        validate({}, [])
    assert str(exc.value) == "schema must be dict"


def test_schema_none_es_typeerror():
    with pytest.raises(TypeError) as exc:
        validate(1, None)
    assert str(exc.value) == "schema must be dict"


def test_schema_tupla_es_typeerror():
    with pytest.raises(TypeError) as exc:
        validate(1, (("type", "integer"),))
    assert str(exc.value) == "schema must be dict"


def test_validate_devuelve_list_no_tupla():
    resultado = validate(1, {"type": "string"})
    assert isinstance(resultado, list)


def test_validate_es_puro_no_muta_el_schema():
    schema = {"type": "object", "required": ["a"]}
    copia = dict(schema)
    validate({}, schema)
    assert schema == copia


def test_objetos_tipicos_del_dominio_json():
    schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "n": {"type": "number"},
            "s": {"type": "string"},
            "nil": {"type": "null"},
            "arr": {"type": "array"},
            "obj": {"type": "object"},
        },
    }
    data = {"ok": True, "n": 1.5, "s": "x", "nil": None, "arr": [], "obj": {}}
    assert validate(data, schema) == []
    malo = {"ok": 1, "n": True, "s": 2, "nil": 0, "arr": {}, "obj": []}
    assert validate(malo, schema) == [
        "$.ok: expected boolean, got integer",
        "$.n: expected number, got boolean",
        "$.s: expected string, got integer",
        "$.nil: expected null, got integer",
        "$.arr: expected array, got object",
        "$.obj: expected object, got array",
    ]


def test_required_ausente_vs_tipo_mal_en_la_misma_clave():
    # required se evalua primero; la clave ausente genera solo el required
    schema = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
    }
    assert validate({}, schema) == ["$: missing required property 'a'"]
