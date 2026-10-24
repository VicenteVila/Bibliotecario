"""Tests ocultos: semántica del diff (renómbrados, orden, contrato)."""
from csvdiff import diff_csv, diff_tables, read_table


def _write(path, text):
    path.write_bytes(text.encode("utf-8"))


def test_renombrado_con_valores_iguales(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,name\n1,ana\n2,luis\n")
    _write(new, "id,title\n1,ana\n2,luis\n")
    result = diff_csv(old, new, ["id"])
    assert result.renamed_columns == {"name": "title"}
    assert result.changed == {}
    assert result.added == {}
    assert result.removed == {}
    assert result.unchanged == 2


def test_renombrado_no_detectado_si_valores_difieren(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,name\n1,ana\n")
    _write(new, "id,title\n1,otra\n")
    result = diff_csv(old, new, ["id"])
    assert result.renamed_columns == {}
    assert result.changed == {}


def test_renombrado_detectado_ignora_filas_anadidas(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,name\n1,ana\n")
    _write(new, "id,title\n1,ana\n2,eva\n")
    result = diff_csv(old, new, ["id"])
    assert result.renamed_columns == {"name": "title"}
    assert result.changed == {}
    assert result.added == {"2": {"id": "2", "title": "eva"}}
    assert result.unchanged == 1


def test_dos_columnas_sobrantes_sin_renombrado(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,a,b\n1,1,2\n")
    _write(new, "id,a,c\n1,1,99\n")
    result = diff_csv(old, new, ["id"])
    assert result.renamed_columns == {}
    assert result.changed == {}
    assert result.unchanged == 1


def test_columna_que_sobra_se_ignora_en_changed(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,a\n1,x\n")
    _write(new, "id,a,extra\n1,x,zzz\n")
    result = diff_csv(old, new, ["id"])
    assert result.changed == {}
    assert result.unchanged == 1


def test_added_incluye_columnas_nuevas(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,a\n1,x\n")
    _write(new, "id,a,extra\n2,x,zzz\n")
    result = diff_csv(old, new, ["id"])
    assert result.added == {"2": {"id": "2", "a": "x", "extra": "zzz"}}


def test_removed_usa_nombres_de_columnas_del_archivo_antiguo(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,vieja\n9,valor\n")
    _write(new, "id,nueva\n1,x\n")
    result = diff_csv(old, new, ["id"])
    assert result.removed == {"9": {"id": "9", "vieja": "valor"}}
    assert result.added == {"1": {"id": "1", "nueva": "x"}}


def test_salida_ordenada_por_clave(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,v\n10,a\n9,b\n")
    _write(new, "id,v\n10,A\n9,B\n")
    result = diff_csv(old, new, ["id"])
    assert list(result.changed) == ["10", "9"]
    assert list(result.added) == []


def test_to_dict_shape_y_tipos(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,v\n1,a\n2,b\n")
    _write(new, "id,v\n1,a\n3,c\n")
    d = diff_csv(old, new, ["id"]).to_dict()
    assert list(d) == ["added", "removed", "changed", "renamed_columns", "unchanged"]
    assert d["added"] == {"3": {"id": "3", "v": "c"}}
    assert d["removed"] == {"2": {"id": "2", "v": "b"}}
    assert d["changed"] == {}
    assert d["renamed_columns"] == {}
    assert d["unchanged"] == 1


def test_unchanged_con_conjunto_mixto(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,v\n1,a\n2,b\n3,c\n")
    _write(new, "id,v\n1,a\n2,B\n4,d\n")
    result = diff_csv(old, new, ["id"])
    assert result.unchanged == 1
    assert set(result.changed) == {"2"}
    assert set(result.removed) == {"3"}
    assert set(result.added) == {"4"}


def test_clave_compuesta_en_diff(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "store,sku,qty\nA,x,1\nB,x,2\n")
    _write(new, "store,sku,qty\nA,x,9\nB,x,2\n")
    result = diff_csv(old, new, ["store", "sku"])
    assert result.changed == {"A\x1fx": {"qty": {"old": "1", "new": "9"}}}
    assert result.unchanged == 1


def test_valores_vacios_y_espacios_se_comparan_literal(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,v\n1,x\n2,\n")
    _write(new, "id,v\n1,x\n2, \n")
    result = diff_csv(old, new, ["id"])
    assert result.changed == {"2": {"v": {"old": "", "new": " "}}}


def test_diff_tables_directo_con_tablas_en_memoria():
    old = read_table_bytes("id,v\n1,a\n")
    new = read_table_bytes("id,v\n1,b\n")
    result = diff_tables(old, new)
    assert result.changed == {"1": {"v": {"old": "a", "new": "b"}}}


def read_table_bytes(text):
    import tempfile
    import os

    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "wb") as fh:
        fh.write(text.encode("utf-8"))
    try:
        return read_table(path, ["id"])
    finally:
        os.unlink(path)
