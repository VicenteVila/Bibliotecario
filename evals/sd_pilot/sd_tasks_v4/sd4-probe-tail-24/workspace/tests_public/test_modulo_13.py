from inventario import modulo_13 as m


def test_primero_13():
    assert m.consultar("C13-0001") == {"grupo": "B", "valor": 353}
