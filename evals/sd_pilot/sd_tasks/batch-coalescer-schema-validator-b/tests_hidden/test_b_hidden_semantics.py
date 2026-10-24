"""Tests ocultos: semántica (required, tipos, enum, acumulación, orden)."""
from jsonval import validate


def test_objeto_valido_anidado():
    schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "object",
                "properties": {"b": {"type": "integer"}},
                "required": ["b"],
            }
        },
        "required": ["a"],
    }
    assert validate({"a": {"b": 1}}, schema) == []


def test_required_anidado_mensaje_en_path_del_padre():
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {"email": {"type": "string"}},
                "required": ["email"],
            }
        },
    }
    assert validate({"user": {}}, schema) == [
        "$.user: missing required property 'email'"
    ]


def test_required_varios_en_orden_del_array():
    schema = {"type": "object", "required": ["z", "a", "m"]}
    assert validate({}, schema) == [
        "$: missing required property 'z'",
        "$: missing required property 'a'",
        "$: missing required property 'm'",
    ]


def test_orden_required_primero_luego_propiedades_en_insercion():
    schema = {
        "type": "object",
        "properties": {
            "b": {"type": "integer"},
            "a": {"type": "string"},
        },
        "required": ["b", "a"],
    }
    assert validate({"a": 1}, schema) == [
        "$: missing required property 'b'",
        "$.a: expected string, got integer",
    ]


def test_errores_acumulados_en_orden_de_insercion():
    schema = {
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "string"},
        },
    }
    data = {"y": 2, "x": "mal", "z": True}
    assert validate(data, schema) == [
        "$.y: expected string, got integer",
        "$.x: expected integer, got string",
    ]


def test_additional_properties_true_por_defecto():
    schema = {"type": "object", "properties": {"a": {"type": "integer"}}}
    assert validate({"a": 1, "extra": "x"}, schema) == []


def test_additional_properties_false_en_raiz():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "additionalProperties": False,
    }
    assert validate({"a": 1, "extra": "x"}, schema) == [
        "$: unexpected property 'extra'"
    ]


def test_additional_properties_false_anidado_y_en_insercion():
    schema = {
        "type": "object",
        "properties": {
            "obj": {
                "type": "object",
                "properties": {"k": {"type": "integer"}},
                "additionalProperties": False,
            }
        },
    }
    data = {"obj": {"zz": 0, "k": 1, "aa": 2}}
    assert validate(data, schema) == [
        "$.obj: unexpected property 'zz'",
        "$.obj: unexpected property 'aa'",
    ]


def test_additional_properties_false_no_valida_el_valor_extra():
    schema = {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    assert validate({"rara": {"anidado": [1]}}, schema) == [
        "$: unexpected property 'rara'"
    ]


def test_bool_no_es_number():
    assert validate(True, {"type": "number"}) == [
        "$: expected number, got boolean"
    ]


def test_bool_no_es_integer():
    assert validate(False, {"type": "integer"}) == [
        "$: expected integer, got boolean"
    ]


def test_float_no_es_integer():
    assert validate(2.0, {"type": "integer"}) == [
        "$: expected integer, got number"
    ]


def test_int_si_es_number():
    assert validate(2, {"type": "number"}) == []


def test_float_es_number():
    assert validate(2.5, {"type": "number"}) == []


def test_null_vs_otros_tipos():
    assert validate(None, {"type": "null"}) == []
    assert validate(1, {"type": "null"}) == ["$: expected null, got integer"]
    assert validate(None, {"type": "string"}) == [
        "$: expected string, got null"
    ]


def test_string_vs_number_mensajes():
    assert validate("x", {"type": "number"}) == [
        "$: expected number, got string"
    ]


def test_array_vs_object():
    assert validate([], {"type": "object"}) == [
        "$: expected object, got array"
    ]
    assert validate({}, {"type": "array"}) == ["$: expected array, got object"]


def test_enum_ok():
    schema = {"enum": ["a", "b", 3]}
    assert validate("a", schema) == []
    assert validate(3, schema) == []


def test_enum_fallo():
    schema = {"enum": ["a", "b"]}
    assert validate("c", schema) == ["$: value not in enum"]


def test_enum_es_estricto_de_tipo_true_vs_1():
    assert validate(True, {"enum": [1]}) == ["$: value not in enum"]
    assert validate(1, {"enum": [True]}) == ["$: value not in enum"]


def test_enum_float_vs_int():
    assert validate(3.0, {"enum": [3]}) == ["$: value not in enum"]
    assert validate(3, {"enum": [3.0]}) == ["$: value not in enum"]


def test_enum_none_y_listas():
    assert validate(None, {"enum": [None]}) == []
    assert validate([], {"enum": [[]]}) == []
    assert validate([], {"enum": [1]}) == ["$: value not in enum"]


def test_enum_pare_al_nodo_sin_descender():
    schema = {"type": "object", "enum": [1], "required": ["x"]}
    assert validate({}, schema) == ["$: value not in enum"]


def test_min_length():
    schema = {"type": "string", "minLength": 2}
    assert validate("", schema) == ["$: string length 0 < minLength 2"]
    assert validate("a", schema) == ["$: string length 1 < minLength 2"]
    assert validate("ab", schema) == []


def test_max_length():
    schema = {"type": "string", "maxLength": 3}
    assert validate("abcd", schema) == ["$: string length 4 > maxLength 3"]
    assert validate("abc", schema) == []


def test_min_y_max_length_anidados():
    schema = {
        "type": "object",
        "properties": {"s": {"type": "string", "minLength": 3}},
    }
    assert validate({"s": "ab"}, schema) == ["$.s: string length 2 < minLength 3"]


def test_type_incorrecto_no_desciende():
    schema = {"type": "string", "minLength": 2}
    assert validate(5, schema) == ["$: expected string, got integer"]


def test_array_vacio_con_items_es_valido():
    schema = {"type": "array", "items": {"type": "integer"}}
    assert validate([], schema) == []


def test_array_sin_items_ignora_elementos():
    assert validate([1, "x", None], {"type": "array"}) == []


def test_array_items_complejos():
    schema = {
        "type": "array",
        "items": {"type": "object", "required": ["id"]},
    }
    assert validate([{"id": 1}, {}], schema) == ["$[1]: missing required property 'id'"]


def test_items_en_array_no_esperado():
    # items declarado fuera de un array se ignora
    assert validate("hola", {"type": "string", "items": {"type": "integer"}}) == []


def test_schema_sin_type_valida_solo_enum():
    assert validate("x", {"enum": ["x"]}) == []
    assert validate("y", {"enum": ["x"]}) == ["$: value not in enum"]


def test_schema_vacio_acepta_todo():
    assert validate({"cualquiera": [1, 2]}, {}) == []
    assert validate(None, {}) == []


def test_properties_sin_type_object_se_ignoran():
    schema = {"properties": {"a": {"type": "integer"}}}
    assert validate("no-objeto", schema) == []
