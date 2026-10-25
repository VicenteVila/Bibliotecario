from inventario import modulo_12 as m


def test_primero_12():
    assert m.consultar("C12-0001") == {"grupo": "B", "valor": 252}
