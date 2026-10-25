from inventario import modulo_18 as m


def test_primero_18():
    assert m.consultar("C18-0001") == {"grupo": "B", "valor": 858}
