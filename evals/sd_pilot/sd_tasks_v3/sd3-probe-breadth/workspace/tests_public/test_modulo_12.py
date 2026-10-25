from almacen import modulo_12 as m


def test_modulo_12():
    assert m.clasificar(9) == "bajo"
    assert m.clasificar(10) == "medio"
    assert m.clasificar(22) == "alto"
