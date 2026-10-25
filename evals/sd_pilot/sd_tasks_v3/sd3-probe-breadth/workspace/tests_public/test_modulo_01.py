from almacen import modulo_01 as m


def test_modulo_01():
    assert m.normalizar("  AbC ") == "abc"
