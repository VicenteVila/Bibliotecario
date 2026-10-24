"""Tests ocultos: bordes del TTL, validaciones y purga perezosa."""

import pytest
from catalogo.cache import CacheTTL


class RelojFalso:
    def __init__(self, inicio: float = 0.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def test_ttl_expira_en_el_borde_exacto():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=4, reloj=reloj)
    cache.poner("k", "v", ttl=10.0)
    reloj.avanzar(10.0)
    assert cache.obtener("k") == (False, None)
    stats = cache.estadisticas()
    assert stats["expiraciones"] == 1
    assert stats["fallos"] == 1
    assert stats["tamano"] == 0


def test_justo_antes_del_borde_sigue_vivo():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=4, reloj=reloj)
    cache.poner("k", "v", ttl=10.0)
    reloj.avanzar(9.999)
    assert cache.obtener("k") == (True, "v")
    assert cache.estadisticas()["aciertos"] == 1


def test_valor_none_almacenado_es_acierto():
    cache = CacheTTL(capacidad=4, reloj=RelojFalso())
    cache.poner("k", None, ttl=60.0)
    acierto, valor = cache.obtener("k")
    assert acierto is True
    assert valor is None
    stats = cache.estadisticas()
    assert stats["aciertos"] == 1
    assert stats["fallos"] == 0


def test_ttl_no_positivo_es_valueerror():
    cache = CacheTTL(capacidad=4, reloj=RelojFalso())
    with pytest.raises(ValueError, match="ttl debe ser > 0"):
        cache.poner("k", "v", ttl=0)
    with pytest.raises(ValueError, match="ttl debe ser > 0"):
        cache.poner("k", "v", ttl=-1.5)


def test_capacidad_invalida_es_valueerror():
    with pytest.raises(ValueError, match="capacidad debe ser >= 1"):
        CacheTTL(capacidad=0, reloj=RelojFalso())
    with pytest.raises(ValueError, match="capacidad debe ser >= 1"):
        CacheTTL(capacidad=-3, reloj=RelojFalso())


def test_reemplazo_reinicia_el_ttl():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=4, reloj=reloj)
    cache.poner("k", "v1", ttl=10.0)
    reloj.avanzar(8.0)
    cache.poner("k", "v2", ttl=10.0)
    reloj.avanzar(9.0)
    assert cache.obtener("k") == (True, "v2")


def test_estadisticas_no_purga_entradas_expiradas():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=4, reloj=reloj)
    cache.poner("k", "v", ttl=1.0)
    reloj.avanzar(50.0)
    stats = cache.estadisticas()
    assert stats["tamano"] == 1
    assert stats["expiraciones"] == 0
    acierto, _ = cache.obtener("k")
    assert acierto is False
    assert cache.estadisticas()["tamano"] == 0


def test_limpiar_resetea_contadores_per_no_capacidad():
    reloj = RelojFalso()
    cache = CacheTTL(capacidad=7, reloj=reloj)
    cache.poner("a", 1, ttl=60.0)
    cache.obtener("a")
    cache.obtener("falta")
    cache.limpiar()
    stats = cache.estadisticas()
    assert stats["aciertos"] == 0
    assert stats["fallos"] == 0
    assert stats["expiraciones"] == 0
    assert stats["evicciones"] == 0
    assert stats["tamano"] == 0
    assert stats["capacidad"] == 7
