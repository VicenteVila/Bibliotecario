"""DAOs (data access objects) sobre la conexión SQLite del catálogo."""

from __future__ import annotations

import sqlite3

from catalogo.modelos import Libro, Prestamo


def _fila_a_libro(fila: sqlite3.Row) -> Libro:
    return Libro(
        isbn=fila["isbn"],
        titulo=fila["titulo"],
        autor=fila["autor"],
        anio=fila["anio"],
        copias=fila["copias"],
    )


class LibroDAO:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def agregar(self, libro: Libro) -> None:
        self._conn.execute(
            "INSERT INTO libros (isbn, titulo, autor, anio, copias) "
            "VALUES (?, ?, ?, ?, ?)",
            (libro.isbn, libro.titulo, libro.autor, libro.anio, libro.copias),
        )
        self._conn.commit()

    def buscar_por_isbn(self, isbn: str) -> Libro | None:
        fila = self._conn.execute(
            "SELECT isbn, titulo, autor, anio, copias FROM libros WHERE isbn = ?",
            (isbn,),
        ).fetchone()
        return None if fila is None else _fila_a_libro(fila)

    def listar_por_autor(self, autor: str) -> list[Libro]:
        filas = self._conn.execute(
            "SELECT isbn, titulo, autor, anio, copias FROM libros "
            "WHERE autor = ? ORDER BY isbn",
            (autor,),
        ).fetchall()
        return [_fila_a_libro(f) for f in filas]

    def actualizar_copias(self, isbn: str, delta: int) -> None:
        self._conn.execute(
            "UPDATE libros SET copias = copias + ? WHERE isbn = ?",
            (delta, isbn),
        )
        self._conn.commit()


class PrestamoDAO:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def registrar(self, prestamo: Prestamo) -> None:
        self._conn.execute(
            "INSERT INTO prestamos (identificador, isbn, lector, activo) "
            "VALUES (?, ?, ?, ?)",
            (prestamo.identificador, prestamo.isbn, prestamo.lector,
             1 if prestamo.activo else 0),
        )
        self._conn.commit()

    def buscar(self, identificador: str) -> Prestamo | None:
        fila = self._conn.execute(
            "SELECT identificador, isbn, lector, activo FROM prestamos "
            "WHERE identificador = ?",
            (identificador,),
        ).fetchone()
        if fila is None:
            return None
        return Prestamo(
            identificador=fila["identificador"],
            isbn=fila["isbn"],
            lector=fila["lector"],
            activo=bool(fila["activo"]),
        )

    def prestamos_activos(self, isbn: str) -> int:
        fila = self._conn.execute(
            "SELECT COUNT(*) AS n FROM prestamos "
            "WHERE isbn = ? AND activo = 1",
            (isbn,),
        ).fetchone()
        return int(fila["n"])

    def desactivar(self, identificador: str) -> Prestamo:
        prestamo = self.buscar(identificador)
        if prestamo is None:
            raise KeyError(f"prestamo inexistente: {identificador}")
        self._conn.execute(
            "UPDATE prestamos SET activo = 0 WHERE identificador = ?",
            (identificador,),
        )
        self._conn.commit()
        return Prestamo(
            identificador=prestamo.identificador,
            isbn=prestamo.isbn,
            lector=prestamo.lector,
            activo=False,
        )
