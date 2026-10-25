from almacen import modulo_05 as m


def test_modulo_05():
    assert m.resumen([2, 4]) == {"n": 2, "total": 6, "media": 3.0}
