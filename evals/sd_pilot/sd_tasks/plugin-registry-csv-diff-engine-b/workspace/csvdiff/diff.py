"""Diff entre dos tablas (versión inicial, sin renombrados)."""
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


def diff_tables(old: Table, new: Table) -> DiffResult:
    result = DiffResult()
    common_cols = [c for c in old.columns if c in new.columns]
    for key, row in new.rows.items():
        if key not in old.rows:
            result.added[key] = dict(row)
    for key, row in old.rows.items():
        if key not in new.rows:
            result.removed[key] = dict(row)
    for key, new_row in new.rows.items():
        old_row = old.rows.get(key)
        if old_row is None:
            continue
        cells: dict[str, dict[str, str]] = {}
        for col in common_cols:
            if old_row[col] != new_row[col]:
                cells[col] = {"old": old_row[col], "new": new_row[col]}
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
