"""Tests ocultos: lector TOML y errores de formato."""
import pytest

from configmig import readers
from configmig.errors import ConfigParseError, UnknownFormatError
from configmig import migrator


def test_read_toml_basica():
    texto = '[app]\nname = "Biblio"\nversion = "1.2"\n[db]\nhost = "localhost"\nport = 5432\ntls = true\n'
    cfg = readers.read_toml(texto)
    assert cfg.values == {
        "app.name": "Biblio",
        "app.version": "1.2",
        "db.host": "localhost",
        "db.port": 5432,
        "db.tls": True,
    }


def test_read_toml_anidamiento_y_flotantes():
    texto = 'a = 1.5\n[outer.inner]\nx = "y"\nz = -3\n'
    cfg = readers.read_toml(texto)
    assert cfg.values == {"a": 1.5, "outer.inner.x": "y", "outer.inner.z": -3}


def test_read_toml_comentarios_y_espacios():
    texto = '# comentario\n[app]  \n  name = "x"   # otro\n\n[db]\nport = 1\n'
    cfg = readers.read_toml(texto)
    assert cfg.values["app.name"] == "x"
    assert cfg.values["db.port"] == 1


def test_read_toml_sintaxis_invalida():
    with pytest.raises(ConfigParseError):
        readers.read_toml("[app\nname = 1\n")


def test_detect_format_toml():
    assert migrator.detect_format("conf/app.toml") == "toml"
    assert migrator.detect_format("conf/app.ini") == "ini"
    assert migrator.detect_format("conf/app.CFG") == "ini"
    assert migrator.detect_format("conf/app.JSON") == "json"


def test_extension_desconocida_lleva_path():
    with pytest.raises(UnknownFormatError) as exc:
        migrator.detect_format("conf/app.yaml")
    assert exc.value.path == "conf/app.yaml"


def test_load_toml_desde_disco(tmp_path):
    p = tmp_path / "app.toml"
    p.write_text(
        '[app]\nname = "Biblio"\nversion = "1"\n[db]\nhost = "h"\nport = 1\n',
        encoding="utf-8",
    )
    cfg = migrator.load(p)
    assert cfg.values["app.name"] == "Biblio"


def test_load_json_con_bom(tmp_path):
    p = tmp_path / "app.json"
    p.write_bytes(
        '\ufeff{"app": {"name": "x", "version": "1"}, "db": {"host": "h", "port": 1}}'.encode(
            "utf-8"
        )
    )
    cfg = migrator.load(p)
    assert cfg.values["app.name"] == "x"


def test_read_ini_bom_inicial():
    cfg = readers.read_ini('\ufeff[app]\nname = "x"\n')
    assert cfg.values["app.name"] == "x"


def test_read_ini_clave_fuera_de_seccion():
    with pytest.raises(ConfigParseError):
        readers.read_ini("suelta = 1\n[app]\nname = x\n")


def test_read_ini_clave_duplicada():
    with pytest.raises(ConfigParseError):
        readers.read_ini("[app]\nname = a\nname = b\n")


def test_read_ini_crlf(tmp_path):
    cfg = readers.read_ini("[app]\r\nname = x\r\nversion = 1\r\n")
    assert cfg.values["app.name"] == "x"


def test_read_ini_comillas_y_coercion():
    cfg = readers.read_ini(
        "[app]\nname = 'Ana'\nversion = \"1.0.3\"\n[db]\nport = 5432\nratio = 0.5\nflag = false\n"
    )
    assert cfg.values["app.name"] == "Ana"
    assert cfg.values["app.version"] == "1.0.3"
    assert cfg.values["db.port"] == 5432
    assert cfg.values["db.ratio"] == 0.5
    assert cfg.values["db.flag"] is False


def test_read_json_lista_como_valor():
    with pytest.raises(ConfigParseError):
        readers.read_json('{"app": {"names": ["a", "b"]}}')


def test_read_json_raiz_no_objeto():
    with pytest.raises(ConfigParseError):
        readers.read_json("[1, 2]")
