from inventario import modulo_23 as m


def test_primero_23():
    assert m.consultar("C23-0001") == {"grupo": "B", "valor": 366}
