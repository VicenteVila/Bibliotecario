"""Tests públicos de la migración de configuraciones."""
import json

import pytest

from configmig import (
    Config,
    ConfigValidationError,
    UnknownFormatError,
    migrate,
    read_ini,
    read_json,
    validate,
)


VALID_INI = """\
[app]
name = Bibliotecario
version = 1.0.3
[db]
host = localhost
port = 5432
"""


def test_ini_a_json_produce_plan_plano(tmp_path):
    src = tmp_path / "app.ini"
    src.write_text(VALID_INI, encoding="utf-8")
    salida = migrate(src, "json")
    datos = json.loads(salida)
    assert datos == {
        "app.name": "Bibliotecario",
        "app.version": "1.0.3",
        "db.host": "localhost",
        "db.port": 5432,
    }


def test_read_json_aplaña_anidamiento():
    cfg = read_json('{"app": {"name": "x", "version": "1"}, "db": {"host": "h", "port": 1}}')
    assert cfg.values["app.name"] == "x"
    assert cfg.values["db.port"] == 1


def test_validate_faltantes_ordenados():
    cfg = Config(values={})
    with pytest.raises(ConfigValidationError) as exc:
        validate(cfg)
    assert exc.value.errors == [
        "missing:app.name",
        "missing:app.version",
        "missing:db.host",
        "missing:db.port",
    ]


def test_read_ini_coercion_de_valores():
    cfg = read_ini("[app]\nname = \"Biblio\"\nversion = 2\n[db]\nhost = h\nport = 6\n[extra]\ntls = true\n")
    assert cfg.values["app.name"] == "Biblio"
    assert cfg.values["app.version"] == 2
    assert cfg.values["extra.tls"] is True


def test_migracion_toml_a_json(tmp_path):
    src = tmp_path / "app.toml"
    src.write_text(
        '[app]\nname = "Biblio"\nversion = "1"\n[db]\nhost = "h"\nport = 5432\n',
        encoding="utf-8",
    )
    salida = migrate(src, "json")
    datos = json.loads(salida)
    assert datos["db.port"] == 5432
    assert datos["app.name"] == "Biblio"


def test_extension_desconocida(tmp_path):
    src = tmp_path / "app.yaml"
    src.write_text("a: 1\n", encoding="utf-8")
    with pytest.raises(UnknownFormatError):
        migrate(src)
