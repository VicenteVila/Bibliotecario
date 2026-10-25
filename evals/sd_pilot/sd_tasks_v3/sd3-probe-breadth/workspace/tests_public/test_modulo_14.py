from almacen import modulo_14 as m


def test_modulo_14():
    assert m.validar(90) is True
    assert m.validar(91) is False
