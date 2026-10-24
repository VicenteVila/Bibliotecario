"""Tests ocultos: validador, convertidores y orquestador."""
import pytest

from configmig import converters, migrator, validator
from configmig.errors import ConfigValidationError, UnknownFormatError
from configmig.model import Config

VALID = {
    "app.name": "Biblio",
    "app.version": "1.0",
    "db.host": "localhost",
    "db.port": 5432,
}


def test_validate_ok_no_lanza():
    validator.validate(Config(values=dict(VALID)))


def test_validate_todos_los_errores_ordenados():
    cfg = Config(values={"otra.clave": 1, "db.tls": "si", "app.name": ""})
    with pytest.raises(ConfigValidationError) as exc:
        validator.validate(cfg)
    assert exc.value.errors == [
        "empty:app.name",
        "missing:app.version",
        "missing:db.host",
        "missing:db.port",
        "type:db.tls",
        "unknown:otra.clave",
    ]


def test_validate_bool_no_cuenta_como_int():
    cfg = Config(values={**VALID, "db.port": True})
    with pytest.raises(ConfigValidationError) as exc:
        validator.validate(cfg)
    assert exc.value.errors == ["type:db.port"]


def test_validate_toml_port_cadena_es_error_de_tipo():
    texto = '[app]\nname = "x"\nversion = "1"\n[db]\nhost = "h"\nport = "5432"\n'
    cfg = migrator.READERS["toml"](texto)
    with pytest.raises(ConfigValidationError) as exc:
        validator.validate(cfg)
    assert exc.value.errors == ["type:db.port"]


def test_validate_toml_desde_archivo(tmp_path):
    p = tmp_path / "app.toml"
    p.write_text(
        '[app]\nname = "x"\nversion = "1"\n[db]\nhost = "h"\nport = "no"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigValidationError) as exc:
        migrator.migrate(p)
    assert exc.value.errors == ["type:db.port"]


def test_migrate_toml_a_json_exacto(tmp_path):
    p = tmp_path / "app.toml"
    p.write_text(
        '[db]\nport = 5432\nhost = "localhost"\n[app]\nversion = "1.0"\nname = "Biblio"\n',
        encoding="utf-8",
    )
    salida = migrator.migrate(p, "json")
    esperado = (
        '{\n'
        '  "app.name": "Biblio",\n'
        '  "app.version": "1.0",\n'
        '  "db.host": "localhost",\n'
        '  "db.port": 5432\n'
        '}\n'
    )
    assert salida == esperado


def test_migrate_toml_a_toml_roundtrip(tmp_path):
    p = tmp_path / "app.toml"
    p.write_text(
        '[app]\nname = "Biblio"\nversion = "1.0"\n[db]\nhost = "localhost"\nport = 5432\ntls = true\n',
        encoding="utf-8",
    )
    salida = migrator.migrate(p, "toml")
    esperado = (
        "[app]\n"
        'name = "Biblio"\n'
        'version = "1.0"\n'
        "\n"
        "[db]\n"
        'host = "localhost"\n'
        "port = 5432\n"
        "tls = true\n"
    )
    assert salida == esperado


def test_write_toml_comillas_y_escapes():
    cfg = Config(values={"app.name": 'con "comillas"', "db.port": 1})
    salida = converters.write_toml(cfg)
    assert salida == '[app]\nname = "con \\"comillas\\""\n\n[db]\nport = 1\n'


def test_write_ini_orden_de_secciones_y_claves():
    cfg = Config(
        values={
            "zeta.k": "1",
            "alfa.b": "2",
            "alfa.a": "3",
            "suelta": "4",
        }
    )
    salida = converters.write_ini(cfg)
    assert salida == "suelta = 4\n\n[alfa]\na = 3\nb = 2\n\n[zeta]\nk = 1\n"


def test_write_json_bool_y_float(tmp_path):
    cfg = Config(values={**VALID, "db.tls": False, "app.version": 1.5})
    salida = converters.write_json(cfg)
    assert '"db.tls": false' in salida
    assert '"app.version": 1.5' in salida


def test_migrate_dst_desconocido(tmp_path):
    p = tmp_path / "app.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(UnknownFormatError) as exc:
        migrator.migrate(p, "yaml")
    assert exc.value.path == "yaml"


def test_migrate_ini_a_toml(tmp_path):
    p = tmp_path / "app.ini"
    p.write_text(
        "[app]\nname = Biblio\nversion = 1.0.3\n[db]\nhost = localhost\nport = 5432\n",
        encoding="utf-8",
    )
    salida = migrator.migrate(p, "toml")
    assert 'name = "Biblio"' in salida
    assert 'version = "1.0.3"' in salida
    assert "port = 5432" in salida


def test_migrate_cfg_como_ini(tmp_path):
    p = tmp_path / "app.cfg"
    p.write_text(
        "[app]\nname = Biblio\nversion = 1.0.3\n[db]\nhost = localhost\nport = 1\n",
        encoding="utf-8",
    )
    assert migrator.detect_format(p) == "ini"
    assert '"app.name": "Biblio"' in migrator.migrate(p)


def test_readers_toml_registrada_en_migrator():
    assert "toml" in migrator.READERS
    assert "toml" in migrator.WRITERS
