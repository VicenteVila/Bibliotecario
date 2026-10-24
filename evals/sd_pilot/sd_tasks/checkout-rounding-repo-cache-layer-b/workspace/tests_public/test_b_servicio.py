"""Tests públicos del servicio del catálogo sobre la caché."""

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


def _servicio() -> CatalogoService:
    db = BaseDatos()
    cache = CacheTTL(capacidad=32, reloj=RelojFalso())
    return CatalogoService(
        LibroDAO(db.conn), PrestamoDAO(db.conn), cache
    )


def _ejemplo() -> Libro:
    return Libro(
        isbn="978-84-1", titulo="Rayuela", autor="Cortazar", anio=1963, copias=3
    )


def test_libro_se_cachea_en_la_segunda_llamada():
    servicio = _servicio()
    servicio.agregar_libro(_ejemplo())
    primero = servicio.libro("978-84-1")
    segundo = servicio.libro("978-84-1")
    assert primero == segundo
    assert segundo is not None
    assert segundo.titulo == "Rayuela"


def test_prestamo_invalida_las_claves_del_isbn():
    servicio = _servicio()
    servicio.agregar_libro(_ejemplo())
    assert servicio.copias_disponibles("978-84-1") == 3
    servicio.registrar_prestamo("p-1", "978-84-1", "lucia")
    assert servicio.copias_disponibles("978-84-1") == 2


def test_devolucion_libera_ejemplar():
    servicio = _servicio()
    servicio.agregar_libro(_ejemplo())
    servicio.registrar_prestamo("p-1", "978-84-1", "lucia")
    assert servicio.copias_disponibles("978-84-1") == 2
    servicio.devolver_prestamo("p-1")
    assert servicio.copias_disponibles("978-84-1") == 3


def test_listar_por_autor_refleja_alta_nueva():
    servicio = _servicio()
    servicio.agregar_libro(_ejemplo())
    assert servicio.listar_por_autor("Cortazar") == ["978-84-1"]
    servicio.agregar_libro(
        Libro(isbn="978-84-2", titulo="Ficciones", autor="Cortazar",
              anio=1944, copias=1)
    )
    assert servicio.listar_por_autor("Cortazar") == ["978-84-1", "978-84-2"]
