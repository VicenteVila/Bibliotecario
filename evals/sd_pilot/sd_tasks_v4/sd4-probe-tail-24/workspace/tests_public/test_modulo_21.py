from inventario import modulo_21 as m


def test_primero_21():
    assert m.consultar("C21-0001") == {"grupo": "B", "valor": 164}
