from inventario import modulo_10 as m


def test_primero_10():
    assert m.consultar("C10-0001") == {"grupo": "B", "valor": 50}
