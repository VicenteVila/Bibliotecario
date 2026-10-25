from inventario import modulo_07 as m


def test_primero_07():
    assert m.consultar("C07-0001") == {"grupo": "B", "valor": 744}
