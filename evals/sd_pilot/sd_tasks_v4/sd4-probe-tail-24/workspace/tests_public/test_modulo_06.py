from inventario import modulo_06 as m


def test_primero_06():
    assert m.consultar("C06-0001") == {"grupo": "B", "valor": 643}
