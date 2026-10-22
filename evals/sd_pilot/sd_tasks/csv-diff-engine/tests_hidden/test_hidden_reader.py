"""Tests ocultos: lector de CSV (BOM, líneas, duplicados, claves)."""
import pytest

from csvdiff import (
    DuplicateColumnError,
    DuplicateKeyError,
    MissingKeyColumnError,
    read_table,
)
from csvdiff.table import KEY_SEPARATOR, Table


def _write(path, text):
    path.write_bytes(text.encode("utf-8"))


def test_bom_no_contamina_primera_columna(tmp_path):
    f = tmp_path / "bom.csv"
    _write(f, "\ufeffid,name\n1,ana\n")
    t = read_table(f, ["id"])
    assert t.columns == ["id", "name"]
    assert "1" in t.rows
    assert t.rows["1"] == {"id": "1", "name": "ana"}


def test_archivo_crlf(tmp_path):
    f = tmp_path / "crlf.csv"
    _write(f, "id,name\r\n1,ana\r\n2,luis\r\n")
    t = read_table(f, ["id"])
    assert t.columns == ["id", "name"]
    assert sorted(t.rows) == ["1", "2"]
    assert t.rows["2"]["name"] == "luis"


def test_lf_sin_newline_final(tmp_path):
    f = tmp_path / "sin_final.csv"
    _write(f, "id,name\n1,ana")
    t = read_table(f, ["id"])
    assert t.rows == {"1": {"id": "1", "name": "ana"}}


def test_fila_en_blanco_intermedia_se_ignora(tmp_path):
    f = tmp_path / "blancos.csv"
    _write(f, "id,name\n1,ana\n\n\n2,luis\n")
    t = read_table(f, ["id"])
    assert sorted(t.rows) == ["1", "2"]


def test_fila_todas_celdas_vacias_se_ignora(tmp_path):
    f = tmp_path / "vacias.csv"
    _write(f, "id,name\n1,ana\n,\n2,luis\n")
    t = read_table(f, ["id"])
    assert sorted(t.rows) == ["1", "2"]


def test_archivo_vacio_lanza_missing_key(tmp_path):
    f = tmp_path / "vacio.csv"
    _write(f, "")
    with pytest.raises(MissingKeyColumnError) as exc:
        read_table(f, ["id", "otra"])
    assert exc.value.column == "id"


def test_solo_cabecera_da_filas_vacias(tmp_path):
    f = tmp_path / "cabecera.csv"
    _write(f, "id,name\n")
    t = read_table(f, ["id"])
    assert t.columns == ["id", "name"]
    assert t.rows == {}


def test_columna_duplicada_en_cabecera(tmp_path):
    f = tmp_path / "dup_col.csv"
    _write(f, "id,name,id\n1,ana,9\n")
    with pytest.raises(DuplicateColumnError) as exc:
        read_table(f, ["id"])
    assert exc.value.column == "id"
    assert exc.value.line == 1


def test_columna_duplicada_tras_filas_en_blanco_linea_fisica(tmp_path):
    f = tmp_path / "dup_col2.csv"
    _write(f, "\n\nid,name,name\n1,ana,x\n")
    with pytest.raises(DuplicateColumnError) as exc:
        read_table(f, ["id"])
    assert exc.value.column == "name"
    assert exc.value.line == 3


def test_clave_duplicada_reporta_linea_fisica(tmp_path):
    f = tmp_path / "dup_key.csv"
    _write(f, "id,name\n1,ana\n\n2,luis\n1,otra\n")
    with pytest.raises(DuplicateKeyError) as exc:
        read_table(f, ["id"])
    assert exc.value.key == "1"
    assert exc.value.line == 5


def test_clave_compuesta_multi_columna(tmp_path):
    f = tmp_path / "multi.csv"
    _write(f, "store,sku,qty\nA,x1,3\nB,x1,4\n")
    t = read_table(f, ["store", "sku"])
    assert f"A{KEY_SEPARATOR}x1" in t.rows
    assert t.rows[f"B{KEY_SEPARATOR}x1"]["qty"] == "4"


def test_fila_corta_se_rellena_y_larga_se_recorta(tmp_path):
    f = tmp_path / "corta.csv"
    _write(f, "id,a,b\n1,solo\n2,x,y,z\n")
    t = read_table(f, ["id"])
    assert t.rows["1"] == {"id": "1", "a": "solo", "b": ""}
    assert t.rows["2"] == {"id": "2", "a": "x", "b": "y"}


def test_valores_con_comas_y_comillas(tmp_path):
    f = tmp_path / "comillas.csv"
    _write(f, 'id,nota\n1,"hola, ""mundo"""\n')
    t = read_table(f, ["id"])
    assert t.rows["1"]["nota"] == 'hola, "mundo"'


def test_make_key_respeta_orden_de_key_columns():
    t = Table(columns=["a", "b"], key_columns=["b", "a"])
    assert t.make_key({"a": "1", "b": "2"}) == f"2{KEY_SEPARATOR}1"
