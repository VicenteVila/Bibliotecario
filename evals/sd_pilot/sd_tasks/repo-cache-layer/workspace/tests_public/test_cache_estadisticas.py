"""Tests públicos de las estadísticas de la caché."""

from catalogo.cache import CacheTTL


class RelojFalso:
    def __init__(self, inicio: float = 0.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def test_aciertos_y_fallos_se_cuentan():
    cache = CacheTTL(capacidad=4, reloj=RelojFalso())
    cache.poner("k", "v", ttl=60.0)
    cache.obtener("k")
    cache.obtener("otra")
    stats = cache.estadisticas()
    assert stats["aciertos"] == 1
    assert stats["fallos"] == 1
    assert stats["capacidad"] == 4


def test_estadisticas_refleja_expiraciones():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=4, reloj=reloj)
    cache.poner("k", "v", ttl=10.0)
    reloj.avanzar(10.0)
    cache.obtener("k")
    stats = cache.estadisticas()
    assert stats["expiraciones"] == 1
    assert stats["fallos"] == 1
    assert stats["tamano"] == 0


def test_estadisticas_refleja_evicciones():
    cache = CacheTTL(capacidad=1, reloj=RelojFalso())
    cache.poner("a", 1, ttl=60.0)
    cache.poner("b", 2, ttl=60.0)
    stats = cache.estadisticas()
    assert stats["evicciones"] == 1
    assert stats["tamano"] == 1
