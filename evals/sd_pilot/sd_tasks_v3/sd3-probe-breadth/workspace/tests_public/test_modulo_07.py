from almacen import modulo_07 as m


def test_modulo_07():
    assert m.sumar_iva(100) == round(100 * (1 + 20 / 100), 2)
