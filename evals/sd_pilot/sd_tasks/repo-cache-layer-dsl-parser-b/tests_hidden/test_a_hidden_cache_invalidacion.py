"""Tests ocultos: invalidación por prefijo (startswith, no igualdad)."""

from catalogo.cache import CacheTTL


class RelojFalso:
    def __init__(self, inicio: float = 0.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def test_invalidar_prefijo_borra_toda_la_familia():
    cache = CacheTTL(capacidad=8, reloj=RelojFalso())
    cache.poner("libro:1", "a", ttl=60.0)
    cache.poner("libro:2", "b", ttl=60.0)
    cache.poner("libro:10", "c", ttl=60.0)
    cache.poner("autor:x", ["libro:1"], ttl=30.0)
    assert cache.invalidar_prefijo("libro:") == 3
    assert cache.obtener("libro:1") == (False, None)
    assert cache.obtener("libro:2") == (False, None)
    assert cache.obtener("libro:10") == (False, None)
    assert cache.obtener("autor:x")[0] is True


def test_invalidar_prefijo_con_nombre_largo_no_borra_al_mas_corto():
    cache = CacheTTL(capacidad=8, reloj=RelojFalso())
    cache.poner("libro:ABC", "corto", ttl=60.0)
    cache.poner("libro:ABCD", "largo", ttl=60.0)
    assert cache.invalidar_prefijo("libro:ABCD") == 1
    assert cache.obtener("libro:ABC") == (True, "corto")
    assert cache.obtener("libro:ABCD") == (False, None)


def test_invalidar_prefijo_vacio_borra_todo():
    cache = CacheTTL(capacidad=8, reloj=RelojFalso())
    cache.poner("a", 1, ttl=60.0)
    cache.poner("b", 2, ttl=60.0)
    assert cache.invalidar_prefijo("") == 2
    assert cache.estadisticas()["tamano"] == 0


def test_invalidar_prefijo_borra_tambien_expiradas_sin_contarlas():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=8, reloj=reloj)
    cache.poner("libro:1", "a", ttl=1.0)
    cache.poner("libro:2", "b", ttl=100.0)
    reloj.avanzar(50.0)
    assert cache.invalidar_prefijo("libro:") == 2
    stats = cache.estadisticas()
    assert stats["expiraciones"] == 0
    assert stats["fallos"] == 0
    assert stats["aciertos"] == 0


def test_invalidar_prefijo_no_toca_contadores_de_acierto_fallo():
    cache = CacheTTL(capacidad=8, reloj=RelojFalso())
    cache.poner("libro:1", "a", ttl=60.0)
    cache.obtener("libro:1")
    cache.obtener("no")
    cache.invalidar_prefijo("libro:")
    stats = cache.estadisticas()
    assert stats["aciertos"] == 1
    assert stats["fallos"] == 1
