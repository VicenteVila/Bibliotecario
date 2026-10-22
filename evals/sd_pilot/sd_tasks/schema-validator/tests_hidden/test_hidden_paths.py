"""Tests ocultos: construcción de paths (notación y escaping)."""
from jsonval import key, validate


def test_key_identificador_usa_punto():
    assert key("$", "user") == "$.user"
    assert key("$.user", "name") == "$.user.name"
    assert key("$", "_x1") == "$._x1"


def test_key_con_punto_usa_corchetes():
    schema = {"type": "object", "properties": {"a.b": {"type": "integer"}}}
    assert validate({"a.b": None}, schema) == [
        '$["a.b"]: expected integer, got null'
    ]


def test_key_que_empieza_por_digito_usa_corchetes():
    schema = {"type": "object", "properties": {"1abc": {"type": "integer"}}}
    assert validate({"1abc": "x"}, schema) == [
        '$["1abc"]: expected integer, got string'
    ]


def test_key_con_espacios_usa_corchetes():
    schema = {"type": "object", "properties": {"mi clave": {"type": "null"}}}
    assert validate({"mi clave": 1}, schema) == [
        '$["mi clave"]: expected null, got integer'
    ]


def test_key_con_comillas_escapa_comilla():
    schema = {"type": "object", "properties": {'say "hi"': {"type": "integer"}}}
    assert validate({'say "hi"': None}, schema) == [
        '$["say \\"hi\\""]: expected integer, got null'
    ]


def test_key_con_backslash_escapa_backslash():
    schema = {"type": "object", "properties": {"a\\b": {"type": "integer"}}}
    assert validate({"a\\b": None}, schema) == [
        '$["a\\\\b"]: expected integer, got null'
    ]


def test_key_con_newline_escapa():
    schema = {"type": "object", "properties": {"line\nbreak": {"type": "integer"}}}
    assert validate({"line\nbreak": None}, schema) == [
        '$["line\\nbreak"]: expected integer, got null'
    ]


def test_key_con_tab_escapa():
    schema = {"type": "object", "properties": {"tab\there": {"type": "integer"}}}
    assert validate({"tab\there": None}, schema) == [
        '$["tab\\there"]: expected integer, got null'
    ]


def test_key_con_carriage_return_escapa():
    schema = {"type": "object", "properties": {"a\rb": {"type": "integer"}}}
    assert validate({"a\rb": None}, schema) == [
        '$["a\\rb"]: expected integer, got null'
    ]


def test_key_unicode_no_es_identificador():
    schema = {"type": "object", "properties": {"café": {"type": "integer"}}}
    assert validate({"café": None}, schema) == [
        '$["café"]: expected integer, got null'
    ]


def test_key_comilla_simple_no_se_escapa():
    schema = {"type": "object", "properties": {"it's": {"type": "integer"}}}
    assert validate({"it's": None}, schema) == [
        '$["it\'s"]: expected integer, got null'
    ]


def test_path_indice_de_array():
    schema = {"type": "array", "items": {"type": "string"}}
    assert validate([1, "ok", 3.0], schema) == [
        "$[0]: expected string, got integer",
        "$[2]: expected string, got number",
    ]


def test_path_array_de_arrays():
    schema = {
        "type": "array",
        "items": {"type": "array", "items": {"type": "integer"}},
    }
    assert validate([[1], [2, "x"]], schema) == [
        "$[1][1]: expected integer, got string"
    ]


def test_path_profundo_objeto_array_objeto():
    schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "object",
                "properties": {
                    "b": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"c": {"type": "boolean"}},
                        },
                    }
                },
            }
        },
    }
    data = {"a": {"b": [{"c": True}, {"c": "x"}, {"c": 1}]}}
    assert validate(data, schema) == [
        "$.a.b[1].c: expected boolean, got string",
        "$.a.b[2].c: expected boolean, got integer",
    ]


def test_path_anidado_con_clave_rara_intermedia():
    schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": "object",
                "properties": {"b c": {"type": "string"}},
            }
        },
    }
    assert validate({"a": {"b c": 1}}, schema) == [
        '$.a["b c"]: expected string, got integer'
    ]
