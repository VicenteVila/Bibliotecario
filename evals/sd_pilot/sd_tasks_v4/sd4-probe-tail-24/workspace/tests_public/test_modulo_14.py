from inventario import modulo_14 as m


def test_primero_14():
    assert m.consultar("C14-0001") == {"grupo": "B", "valor": 454}
