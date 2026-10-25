from inventario import modulo_20 as m


def test_primero_20():
    assert m.consultar("C20-0001") == {"grupo": "B", "valor": 63}
