from inventario import modulo_04 as m


def test_primero_04():
    assert m.consultar("C04-0001") == {"grupo": "B", "valor": 441}
