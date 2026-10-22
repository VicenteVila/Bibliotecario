"""Servicio de alto nivel del catálogo: orquesta DAOs + caché TTL.

Este módulo es la arquitectura existente: no se toca. Define las claves y los
TTLs de la caché y las invalidaciones tras cada mutación.
"""

from __future__ import annotations

from catalogo.cache import CacheTTL
from catalogo.daos import LibroDAO, PrestamoDAO
from catalogo.modelos import Libro, Prestamo

TTL_LIBRO_S = 60.0
TTL_LISTADO_S = 30.0


class CatalogoService:
    def __init__(
        self,
        dao_libros: LibroDAO,
        dao_prestamos: PrestamoDAO,
        cache: CacheTTL,
    ) -> None:
        self._dao_libros = dao_libros
        self._dao_prestamos = dao_prestamos
        self._cache = cache

    def libro(self, isbn: str) -> Libro | None:
        clave = f"libro:{isbn}"
        acierto, valor = self._cache.obtener(clave)
        if acierto:
            return valor
        encontrado = self._dao_libros.buscar_por_isbn(isbn)
        if encontrado is not None:
            self._cache.poner(clave, encontrado, TTL_LIBRO_S)
        return encontrado

    def listar_por_autor(self, autor: str) -> list[str]:
        clave = f"autor:{autor}"
        acierto, valor = self._cache.obtener(clave)
        if acierto:
            return list(valor)
        isbns = [libro.isbn for libro in self._dao_libros.listar_por_autor(autor)]
        self._cache.poner(clave, isbns, TTL_LISTADO_S)
        return list(isbns)

    def copias_disponibles(self, isbn: str) -> int:
        clave = f"copias:{isbn}"
        acierto, valor = self._cache.obtener(clave)
        if acierto:
            return valor
        libro = self._dao_libros.buscar_por_isbn(isbn)
        if libro is None:
            return 0
        disponibles = libro.copias - self._dao_prestamos.prestamos_activos(isbn)
        self._cache.poner(clave, disponibles, TTL_LIBRO_S)
        return disponibles

    def agregar_libro(self, libro: Libro) -> None:
        self._dao_libros.agregar(libro)
        self._cache.invalidar_prefijo("autor:")

    def registrar_prestamo(self, identificador: str, isbn: str,
                           lector: str) -> None:
        if self._dao_libros.buscar_por_isbn(isbn) is None:
            raise KeyError(f"libro inexistente: {isbn}")
        self._dao_prestamos.registrar(
            Prestamo(
                identificador=identificador, isbn=isbn, lector=lector, activo=True
            )
        )
        self._cache.invalidar_prefijo(f"libro:{isbn}")
        self._cache.invalidar_prefijo(f"copias:{isbn}")

    def devolver_prestamo(self, identificador: str) -> None:
        prestamo = self._dao_prestamos.desactivar(identificador)
        self._cache.invalidar_prefijo(f"copias:{prestamo.isbn}")

    def actualizar_copias(self, isbn: str, delta: int) -> None:
        self._dao_libros.actualizar_copias(isbn, delta)
        self._cache.invalidar_prefijo(f"libro:{isbn}")
        self._cache.invalidar_prefijo(f"copias:{isbn}")
