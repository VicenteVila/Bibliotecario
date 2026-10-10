"""Aislamiento: ningún test debe escribir en data/bibliotecario.db.

Medido antes de existir este fichero: `test_isolated_no_escribe_leccion_ni_las_lectura`
llama a `loop.run()`, que hace `harness.start_run()`, y dejaba una fila nueva en
harness_runs. Una sola pasada de pytest subía 1121 -> 1122, así que la suite
estaba contaminando la BD real y 'los tests no tocan la BD' era falso.

Los tests que parchean `storage.db_path` ellos mismos siguen ganando: piden la
misma instancia de `monkeypatch` y su setattr se aplica después de este.
"""
from __future__ import annotations

import pytest

from bibliotecario.core import storage


@pytest.fixture(autouse=True)
def _db_aislada(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    return db
