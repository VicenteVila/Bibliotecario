"""Tests públicos del motor de diff CSV."""
import pytest

from csvdiff import (
    DiffResult,
    MissingKeyColumnError,
    diff_csv,
    read_table,
)


def _write(path, text):
    path.write_text(text, encoding="utf-8", newline="")


def test_diff_basico_added_removed_changed(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,name\n1,ana\n2,luis\n")
    _write(new, "id,name\n1,ana\n3,eva\n")
    result = diff_csv(old, new, ["id"])
    assert result.added == {"3": {"id": "3", "name": "eva"}}
    assert result.removed == {"2": {"id": "2", "name": "luis"}}
    assert result.changed == {}
    assert result.unchanged == 1


def test_changed_solo_celdas_distintas(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,a,b\n1,x,y\n")
    _write(new, "id,a,b\n1,x,z\n")
    result = diff_csv(old, new, ["id"])
    assert result.changed == {"1": {"b": {"old": "y", "new": "z"}}}
    assert result.unchanged == 0


def test_to_dict_claves_exactas(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,v\n1,a\n")
    _write(new, "id,v\n1,a\n")
    d = diff_csv(old, new, ["id"]).to_dict()
    assert set(d) == {"added", "removed", "changed", "renamed_columns", "unchanged"}
    assert isinstance(d["unchanged"], int)


def test_falta_columna_clave(tmp_path):
    f = tmp_path / "a.csv"
    _write(f, "id,name\n1,x\n")
    with pytest.raises(MissingKeyColumnError) as exc:
        read_table(f, ["nid"])
    assert exc.value.column == "nid"


def test_renombrado_detectado(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    _write(old, "id,name\n1,ana\n")
    _write(new, "id,title\n1,ana\n")
    result = diff_csv(old, new, ["id"])
    assert result.renamed_columns == {"name": "title"}
    assert result.changed == {}
    assert result.unchanged == 1
