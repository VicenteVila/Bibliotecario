from almacen import modulo_03 as m


def test_modulo_03():
    esperado = (6 + 4 * 2) * 3 + 2
    assert m.calcular(4, 3) == esperado
