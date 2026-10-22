"""Tests ocultos: claves y invalidaciones observables del CatalogoService."""

from catalogo.cache import CacheTTL
from catalogo.daos import LibroDAO, PrestamoDAO
from catalogo.db import BaseDatos
from catalogo.modelos import Libro
from catalogo.servicio import CatalogoService


class RelojFalso:
    def __init__(self, inicio: float = 0.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


class LibroDAOCuenta(LibroDAO):
    def __init__(self, conn) -> None:
        super().__init__(conn)
        self.consultas_isbn = 0
        self.consultas_autor = 0

    def buscar_por_isbn(self, isbn: str):
        self.consultas_isbn += 1
        return super().buscar_por_isbn(isbn)

    def listar_por_autor(self, autor: str):
        self.consultas_autor += 1
        return super().listar_por_autor(autor)


class PrestamoDAOCuenta(PrestamoDAO):
    def __init__(self, conn) -> None:
        super().__init__(conn)
        self.consultas_activos = 0

    def prestamos_activos(self, isbn: str) -> int:
        self.consultas_activos += 1
        return super().prestamos_activos(isbn)


def _armar() -> tuple[CatalogoService, LibroDAOCuenta, PrestamoDAOCuenta, RelojFalso]:
    db = BaseDatos()
    reloj = RelojFalso()
    dao_libros = LibroDAOCuenta(db.conn)
    dao_prestamos = PrestamoDAOCuenta(db.conn)
    cache = CacheTTL(capacidad=32, reloj=reloj)
    servicio = CatalogoService(dao_libros, dao_prestamos, cache)
    return servicio, dao_libros, dao_prestamos, reloj


def _ejemplo(isbn: str = "978-84-1", autor: str = "Cortazar") -> Libro:
    return Libro(isbn=isbn, titulo="T", autor=autor, anio=1963, copias=3)


def test_libro_cacheado_no_vuelve_a_consultar_el_dao():
    servicio, dao_libros, _, _ = _armar()
    servicio.agregar_libro(_ejemplo())
    servicio.libro("978-84-1")
    servicio.libro("978-84-1")
    servicio.libro("978-84-1")
    assert dao_libros.consultas_isbn == 1  # solo la del alta (agregar consulta)


def test_libro_inexistente_no_se_cachea():
    servicio, dao_libros, _, _ = _armar()
    assert servicio.libro("no") is None
    assert servicio.libro("no") is None
    assert dao_libros.consultas_isbn == 2


def test_prestamo_invalida_su_isbn_y_no_otros():
    servicio, _, _, _ = _armar()
    servicio.agregar_libro(_ejemplo("978-84-1"))
    servicio.agregar_libro(_ejemplo("978-84-2"))
    servicio.libro("978-84-1")
    servicio.libro("978-84-2")
    servicio.registrar_prestamo("p-1", "978-84-1", "lucia")
    assert servicio.libro("978-84-1").copias == 3  # dato del modelo, no mutado
    assert servicio.copias_disponibles("978-84-1") == 2
    assert servicio.copias_disponibles("978-84-2") == 3


def test_agregar_libro_invalida_todos_los_listados_de_autores():
    servicio, _, _, _ = _armar()
    servicio.agregar_libro(_ejemplo("978-84-1", "Garcia"))
    servicio.agregar_libro(_ejemplo("978-84-2", "Garcia Marquez"))
    assert servicio.listar_por_autor("Garcia") == ["978-84-1"]
    assert servicio.listar_por_autor("Garcia Marquez") == ["978-84-2"]
    servicio.agregar_libro(_ejemplo("978-84-3", "Garcia"))
    assert servicio.listar_por_autor("Garcia") == ["978-84-1", "978-84-3"]
    assert servicio.listar_por_autor("Garcia Marquez") == ["978-84-2"]


def test_copias_disponibles_se_cachea_y_devolucion_invalida():
    servicio, _, dao_prestamos, _ = _armar()
    servicio.agregar_libro(_ejemplo())
    assert servicio.copias_disponibles("978-84-1") == 3
    assert servicio.copias_disponibles("978-84-1") == 3
    assert dao_prestamos.consultas_activos == 1
    servicio.registrar_prestamo("p-1", "978-84-1", "lucia")
    assert servicio.copias_disponibles("978-84-1") == 2
    servicio.devolver_prestamo("p-1")
    assert servicio.copias_disponibles("978-84-1") == 3


def test_listar_por_autor_devuelve_copia_inmutable():
    servicio, _, _, _ = _armar()
    servicio.agregar_libro(_ejemplo("978-84-1"))
    resultado = servicio.listar_por_autor("Cortazar")
    resultado.append("CORRUPTO")
    assert servicio.listar_por_autor("Cortazar") == ["978-84-1"]


def test_listado_vacio_se_cachea_y_alta_lo_refleja():
    servicio, dao_libros, _, _ = _armar()
    assert servicio.listar_por_autor("Nadie") == []
    assert dao_libros.consultas_autor == 1
    assert servicio.listar_por_autor("Nadie") == []
    assert dao_libros.consultas_autor == 1  # cacheado
    servicio.agregar_libro(_ejemplo("978-84-9", "Nadie"))
    assert servicio.listar_por_autor("Nadie") == ["978-84-9"]
    assert dao_libros.consultas_autor == 2
