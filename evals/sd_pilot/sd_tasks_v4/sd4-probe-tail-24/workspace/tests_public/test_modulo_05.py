from inventario import modulo_05 as m


def test_primero_05():
    assert m.consultar("C05-0001") == {"grupo": "B", "valor": 542}
