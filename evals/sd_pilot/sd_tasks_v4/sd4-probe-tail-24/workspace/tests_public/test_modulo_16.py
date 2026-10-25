from inventario import modulo_16 as m


def test_primero_16():
    assert m.consultar("C16-0001") == {"grupo": "B", "valor": 656}
