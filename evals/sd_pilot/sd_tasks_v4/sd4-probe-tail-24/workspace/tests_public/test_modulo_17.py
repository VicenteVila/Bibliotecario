from inventario import modulo_17 as m


def test_primero_17():
    assert m.consultar("C17-0001") == {"grupo": "B", "valor": 757}
