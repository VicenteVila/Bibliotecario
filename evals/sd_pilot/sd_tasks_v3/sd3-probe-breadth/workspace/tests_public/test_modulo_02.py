from almacen import modulo_02 as m


def test_modulo_02():
    assert m.clasificar(11) == "bajo"
    assert m.clasificar(12) == "medio"
    assert m.clasificar(22) == "alto"
