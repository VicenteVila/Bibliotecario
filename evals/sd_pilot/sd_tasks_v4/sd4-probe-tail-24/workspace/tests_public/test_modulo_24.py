from inventario import modulo_24 as m


def test_primero_24():
    assert m.consultar("C24-0001") == {"grupo": "B", "valor": 467}
