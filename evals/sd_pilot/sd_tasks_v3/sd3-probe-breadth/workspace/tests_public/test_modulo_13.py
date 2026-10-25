from almacen import modulo_13 as m


def test_modulo_13():
    esperado = (4 + 4 * 3) * 3 + 2
    assert m.calcular(4, 3) == esperado
