from inventario import modulo_19 as m


def test_primero_19():
    assert m.consultar("C19-0001") == {"grupo": "B", "valor": 959}
