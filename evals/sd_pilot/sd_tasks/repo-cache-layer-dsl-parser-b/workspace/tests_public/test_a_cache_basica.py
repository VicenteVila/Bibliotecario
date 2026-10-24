"""Tests públicos básicos de la caché: hit/miss, reemplazo y limpieza."""

from catalogo.cache import CacheTTL


class RelojFalso:
    def __init__(self, inicio: float = 1000.0) -> None:
        self.ahora = inicio

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def test_obtener_sin_clave_es_fallo():
    cache = CacheTTL(capacidad=4, reloj=RelojFalso())
    acierto, valor = cache.obtener("no-existe")
    assert acierto is False
    assert valor is None


def test_poner_y_obtener_devuelve_el_valor():
    cache = CacheTTL(capacidad=4, reloj=RelojFalso())
    cache.poner("libro:1", {"titulo": "Rayuela"}, ttl=60.0)
    acierto, valor = cache.obtener("libro:1")
    assert acierto is True
    assert valor == {"titulo": "Rayuela"}


def test_reemplazo_de_clave():
    cache = CacheTTL(capacidad=4, reloj=RelojFalso())
    cache.poner("k", 1, ttl=60.0)
    cache.poner("k", 2, ttl=60.0)
    acierto, valor = cache.obtener("k")
    assert acierto is True
    assert valor == 2


def test_invalidar_prefijo_purga_la_familia():
    cache = CacheTTL(capacidad=8, reloj=RelojFalso())
    cache.poner("libro:1", "a", ttl=60.0)
    cache.poner("libro:2", "b", ttl=60.0)
    cache.poner("autor:garcia", ["libro:1"], ttl=30.0)
    assert cache.invalidar_prefijo("libro:") == 2
    assert cache.obtener("libro:1") == (False, None)
    assert cache.obtener("libro:2") == (False, None)
    assert cache.obtener("autor:garcia")[0] is True


def test_limpiar_vacia_todo():
    cache = CacheTTL(capacidad=8, reloj=RelojFalso())
    cache.poner("a", 1, ttl=60.0)
    cache.poner("b", 2, ttl=60.0)
    cache.limpiar()
    assert cache.obtener("a") == (False, None)
    assert cache.obtener("b") == (False, None)
