from inventario import modulo_15 as m


def test_primero_15():
    assert m.consultar("C15-0001") == {"grupo": "B", "valor": 555}
