"""Capa de persistencia SQLite del catálogo.

Una instancia de ``BaseDatos`` owns la conexión. Los DAOs comparten la misma
conexión. El esquema es mínimo y determinista (sin fechas reales).
"""

from __future__ import annotations

import sqlite3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS libros (
    isbn   TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    autor  TEXT NOT NULL,
    anio   INTEGER NOT NULL,
    copias INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS prestamos (
    identificador TEXT PRIMARY KEY,
    isbn         TEXT NOT NULL REFERENCES libros(isbn),
    lector       TEXT NOT NULL,
    activo       INTEGER NOT NULL
);
"""


class BaseDatos:
    def __init__(self, ruta: str = ":memory:") -> None:
        self._conn = sqlite3.connect(ruta)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(ESQUEMA)
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def cerrar(self) -> None:
        self._conn.close()
