from inventario import modulo_03 as m


def test_primero_03():
    assert m.consultar("C03-0001") == {"grupo": "B", "valor": 340}
