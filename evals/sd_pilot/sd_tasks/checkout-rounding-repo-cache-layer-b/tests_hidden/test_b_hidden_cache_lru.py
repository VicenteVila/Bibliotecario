"""Tests ocultos: orden LRU y expulsión de la menos reciente."""

from catalogo.cache import CacheTTL


class RelojFalso:
    def __init__(self, inicio: float = 0.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def test_lru_expulsa_la_menos_usada():
    cache = CacheTTL(capacidad=2, reloj=RelojFalso())
    cache.poner("a", 1, ttl=60.0)
    cache.poner("b", 2, ttl=60.0)
    cache.obtener("a")  # a pasa a ser la más reciente
    cache.poner("c", 3, ttl=60.0)
    assert cache.obtener("b") == (False, None)
    assert cache.obtener("a") == (True, 1)
    assert cache.obtener("c") == (True, 3)


def test_poner_reemplazado_tambien_cuenta_como_uso():
    cache = CacheTTL(capacidad=2, reloj=RelojFalso())
    cache.poner("a", 1, ttl=60.0)
    cache.poner("b", 2, ttl=60.0)
    cache.poner("a", 10, ttl=60.0)  # reemplazo: a es la más reciente
    cache.poner("c", 3, ttl=60.0)
    assert cache.obtener("b") == (False, None)
    assert cache.obtener("a") == (True, 10)
    assert cache.obtener("c") == (True, 3)


def test_evicciones_cuentan_uno_por_entrada_expulsada():
    cache = CacheTTL(capacidad=3, reloj=RelojFalso())
    cache.poner("a", 1, ttl=60.0)
    cache.poner("b", 2, ttl=60.0)
    cache.poner("c", 3, ttl=60.0)
    cache.poner("d", 4, ttl=60.0)
    cache.poner("e", 5, ttl=60.0)
    stats = cache.estadisticas()
    assert stats["evicciones"] == 2
    assert stats["tamano"] == 3
    assert stats["capacidad"] == 3


def test_lru_no_expulsa_entradas_expiradas_por_orden_sino_por_uso():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=2, reloj=reloj)
    cache.poner("a", 1, ttl=5.0)
    cache.poner("b", 2, ttl=100.0)
    cache.obtener("a")  # sigue viva; a es la más reciente
    cache.poner("c", 3, ttl=100.0)
    # se expulsa b (menos reciente), no a
    assert cache.obtener("b") == (False, None)
    assert cache.obtener("a") == (True, 1)
