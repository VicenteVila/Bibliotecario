from almacen import modulo_11 as m


def test_modulo_11():
    assert m.normalizar("  AbC ") == "abc"
