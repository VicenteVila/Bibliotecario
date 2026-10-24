"""Lector de CSV a Table (versión inicial)."""
from __future__ import annotations

import csv
from pathlib import Path

from .errors import DuplicateKeyError, MissingKeyColumnError
from .table import Table


def read_table(path: str | Path, key_columns: list[str] | tuple[str, ...]) -> Table:
    """Lee un CSV y lo convierte en Table indexada por clave compuesta."""
    table = Table(key_columns=list(key_columns))
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            raise MissingKeyColumnError(list(key_columns)[0])
        table.columns = header
        for col in key_columns:
            if col not in header:
                raise MissingKeyColumnError(col)
        index = {name: i for i, name in enumerate(header)}
        for row in reader:
            values = {
                name: row[index[name]] if index[name] < len(row) else ""
                for name in header
            }
            key = table.make_key(values)
            if key in table.rows:
                raise DuplicateKeyError(key, reader.line_num)
            table.rows[key] = values
    return table
