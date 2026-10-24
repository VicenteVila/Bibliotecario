"""Diff entre dos tablas."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .reader import read_table
from .table import Table


@dataclass
class DiffResult:
    added: dict[str, dict[str, str]] = field(default_factory=dict)
    removed: dict[str, dict[str, str]] = field(default_factory=dict)
    changed: dict[str, dict[str, dict[str, str]]] = field(default_factory=dict)
    renamed_columns: dict[str, str] = field(default_factory=dict)
    unchanged: int = 0

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
            "renamed_columns": self.renamed_columns,
            "unchanged": self.unchanged,
        }


def _detect_rename(old: Table, new: Table) -> dict[str, str]:
    """Detección conservadora de renombrados de columna.

    Solo se declara un renombrado cuando exactamente falta una columna en
    el archivo nuevo (respecto al antiguo), exactamente sobra una en el
    nuevo (respecto al antiguo) y los valores de ambas coinciden en todas
    las filas presentes en las dos tablas. En cualquier otro caso no hay
    renombrado.
    """
    missing_in_new = sorted(set(old.columns) - set(new.columns))
    extra_in_new = sorted(set(new.columns) - set(old.columns))
    if len(missing_in_new) != 1 or len(extra_in_new) != 1:
        return {}
    old_col, new_col = missing_in_new[0], extra_in_new[0]
    common_keys = set(old.rows) & set(new.rows)
    old_map = {k: old.rows[k][old_col] for k in common_keys}
    new_map = {k: new.rows[k][new_col] for k in common_keys}
    if old_map != new_map:
        return {}
    return {old_col: new_col}


def diff_tables(old: Table, new: Table) -> DiffResult:
    """Calcula el diff entre dos tablas.

    - ``added`` / ``removed``: filas solo en un lado, con todas las columnas
      de su propio archivo (los del antiguo con sus nombres originales).
    - ``changed``: solo las celdas que difieren de las columnas comparables
      (intersección de columnas tras aplicar el renombrado detectado).
    - Las columnas que sobran en un lado y no se detectan como renombrado
      se ignoran en la comparación de celdas.
    - Salida ordenada por clave (``sorted``) y, dentro de cada fila, por
      nombre de columna.
    - ``unchanged``: número de claves presentes en ambos archivos sin
      ningún cambio de celda.
    """
    rename = _detect_rename(old, new)
    result = DiffResult(renamed_columns=rename)

    for key in sorted(set(new.rows) - set(old.rows)):
        result.added[key] = {c: new.rows[key][c] for c in new.columns}
    for key in sorted(set(old.rows) - set(new.rows)):
        result.removed[key] = {c: old.rows[key][c] for c in old.columns}

    old_columns_renamed = [rename.get(c, c) for c in old.columns]
    comparable = sorted(set(old_columns_renamed) & set(new.columns))
    inv_rename = {v: k for k, v in rename.items()}

    for key in sorted(set(old.rows) & set(new.rows)):
        old_row = old.rows[key]
        new_row = new.rows[key]
        cells: dict[str, dict[str, str]] = {}
        for col in comparable:
            old_name = inv_rename.get(col, col)
            ov = old_row[old_name]
            nv = new_row[col]
            if ov != nv:
                cells[col] = {"old": ov, "new": nv}
        if cells:
            result.changed[key] = cells
        else:
            result.unchanged += 1
    return result


def diff_csv(
    old_path: str | Path,
    new_path: str | Path,
    key_columns: list[str] | tuple[str, ...],
) -> DiffResult:
    return diff_tables(
        read_table(old_path, key_columns),
        read_table(new_path, key_columns),
    )
