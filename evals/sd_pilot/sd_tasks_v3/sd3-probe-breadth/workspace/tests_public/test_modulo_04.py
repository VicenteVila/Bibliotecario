from almacen import modulo_04 as m


def test_modulo_04():
    assert m.validar(94) is True
    assert m.validar(95) is False
