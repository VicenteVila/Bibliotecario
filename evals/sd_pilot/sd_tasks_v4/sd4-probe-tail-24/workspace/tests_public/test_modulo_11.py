from inventario import modulo_11 as m


def test_primero_11():
    assert m.consultar("C11-0001") == {"grupo": "B", "valor": 151}
