"""Tests públicos de expiración temporal con reloj falso."""

from catalogo.cache import CacheTTL


class RelojFalso:
    def __init__(self, inicio: float = 0.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def test_entrada_expirada_es_fallo():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=4, reloj=reloj)
    cache.poner("k", "v", ttl=10.0)
    reloj.avanzar(25.0)
    acierto, valor = cache.obtener("k")
    assert acierto is False
    assert valor is None


def test_entrada_viva_dentro_del_ttl():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=4, reloj=reloj)
    cache.poner("k", "v", ttl=10.0)
    reloj.avanzar(3.0)
    assert cache.obtener("k") == (True, "v")
