"""Lector de CSV a Table."""
from __future__ import annotations

import csv
from pathlib import Path

from .errors import (
    DuplicateColumnError,
    DuplicateKeyError,
    MissingKeyColumnError,
)
from .table import Table


def _is_blank_row(row: list[str]) -> bool:
    return not row or all(cell == "" for cell in row)


def read_table(path: str | Path, key_columns: list[str] | tuple[str, ...]) -> Table:
    """Lee un CSV y lo convierte en Table indexada por clave compuesta.

    - Codificación utf-8-sig: el BOM inicial se elimina.
    - Dialecto por defecto de ``csv``: acepta LF y CRLF y comillas.
    - Las filas en blanco (sin celdas o todas vacías) se ignoran y no
      desplazan la numeración de líneas física.
    - La primera fila no en blanco es la cabecera.
    - Archivo sin ninguna fila no en blanco -> MissingKeyColumnError con la
      primera columna clave.
    - Columna repetida en la cabecera -> DuplicateColumnError con la línea
      física de la repetición.
    - Falta columna clave -> MissingKeyColumnError.
    - Celdas que falten en una fila se rellenan con ""; las sobrantes se
      ignoran.
    - Clave compuesta repetida -> DuplicateKeyError con la línea física de
      la segunda aparición.
    """
    keys = list(key_columns)
    table = Table(key_columns=keys)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header: list[str] | None = None
        for row in reader:
            if _is_blank_row(row):
                continue
            header = row
            header_line = reader.line_num
            break
        if header is None:
            raise MissingKeyColumnError(keys[0])
        seen: dict[str, int] = {}
        for col in header:
            if col in seen:
                raise DuplicateColumnError(col, header_line)
            seen[col] = reader.line_num
        table.columns = list(header)
        for col in keys:
            if col not in seen:
                raise MissingKeyColumnError(col)
        index = {name: i for i, name in enumerate(header)}
        for row in reader:
            if _is_blank_row(row):
                continue
            values = {
                name: row[index[name]] if index[name] < len(row) else ""
                for name in header
            }
            key = table.make_key(values)
            if key in table.rows:
                raise DuplicateKeyError(key, reader.line_num)
            table.rows[key] = values
    return table
