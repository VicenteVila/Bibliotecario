from inventario import modulo_22 as m


def test_primero_22():
    assert m.consultar("C22-0001") == {"grupo": "B", "valor": 265}
