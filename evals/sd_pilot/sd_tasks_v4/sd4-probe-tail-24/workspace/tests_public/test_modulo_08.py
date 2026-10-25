from inventario import modulo_08 as m


def test_primero_08():
    assert m.consultar("C08-0001") == {"grupo": "B", "valor": 845}
