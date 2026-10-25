from inventario import modulo_09 as m


def test_primero_09():
    assert m.consultar("C09-0001") == {"grupo": "B", "valor": 946}
