from almacen import modulo_16 as m


def test_modulo_16():
    assert m.aplicar_descuento(100, 15) == 85.0
