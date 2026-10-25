from almacen import modulo_10 as m


def test_modulo_10():
    assert m.parsear_codigo("ALM-00042") == 42
